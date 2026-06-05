"""Retinal aging clock using RETFound ViT-Large frozen embeddings.

Extracts 1024-dim CLS token embeddings from RETFound (ViT-Large pretrained on
1.6M retinal images), then trains a Ridge regression age head on the train split
from results/features/feature_matrix.parquet.

Pipeline:
    1. Load photography manifest, select one CFP per person (prefer R eye, highest res)
    2. Load DICOM -> PIL Image -> resize 224x224 -> ImageNet normalize
    3. Extract frozen ViT embeddings in batches on GPU
    4. Save embeddings -> results/embeddings/retinal_embeddings.parquet
    5. Train Ridge regression: embedding -> age (train split)
    6. Compute retinal AgeAccel = predicted_age - age (residualized)
    7. Save -> results/clocks/retinal_age_accel.parquet

Usage:
    python -m scripts.retinal_age                   # full pipeline
    python -m scripts.retinal_age --n 20            # first 20 participants (testing)
    python -m scripts.retinal_age --embeddings-only # extract embeddings, skip training
    python -m scripts.retinal_age --from-embeddings # train from saved embeddings
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DATA_ROOT, PHOTO_MANIFEST, result_path, result_variant_path
from .splits import require_split_column

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Dependency checks ─────────────────────────────────────────────────────────

_HAS_TORCH = False
_HAS_TIMM = False

try:
    import torch
    import torch.nn as nn
    _HAS_TORCH = True
except ImportError:
    log.warning("PyTorch not available. Embedding extraction will not work.")

try:
    import timm
    _HAS_TIMM = True
except ImportError:
    log.info("timm not available. Will use manual ViT weight loading.")


# ── Constants ─────────────────────────────────────────────────────────────────

RETFOUND_HF_REPO = "rmaphoh/RETFound_MAE"
RETFOUND_FILENAME = "RETFound_cfp_weights.pth"
EMBED_DIM = 1024  # ViT-Large CLS token dimension
IMG_SIZE = 224
BATCH_SIZE = 32
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

EMBEDDINGS_PATH = result_path("retinal_embeddings.parquet")
OUTPUT_PATH = result_path("retinal_age_accel.parquet")


# ── Step 1: Select one CFP per person ─────────────────────────────────────────

def select_representative_cfp(n: int | None = None) -> pd.DataFrame:
    """Select one representative color fundus photo per person.

    Strategy: keep only Color Photography, prefer right eye (R), then pick
    the image with the largest pixel area (height * width) for consistency.

    Returns DataFrame with columns: person_id, filepath, laterality, height,
    width, manufacturers_model_name.
    """
    log.info("Loading photography manifest ...")
    manifest = pd.read_csv(
        PHOTO_MANIFEST, sep="\t", dtype={"person_id": str}, low_memory=False,
    )
    cfp = manifest[manifest["imaging"] == "Color Photography"].copy()
    log.info(f"  Total CFP records: {len(cfp)}, unique persons: {cfp['person_id'].nunique()}")

    cfp["pixel_area"] = cfp["height"] * cfp["width"]

    # Prefer right eye: assign laterality rank (R=0, L=1)
    cfp["lat_rank"] = cfp["laterality"].map({"R": 0, "L": 1}).fillna(2).astype(int)

    # Sort by person_id, laterality preference (R first), then largest area
    cfp = cfp.sort_values(
        ["person_id", "lat_rank", "pixel_area"],
        ascending=[True, True, False],
    )

    # Take first per person (= right eye, largest resolution)
    selected = cfp.groupby("person_id", sort=False).first().reset_index()
    selected = selected[["person_id", "filepath", "laterality", "height", "width",
                          "manufacturers_model_name"]].copy()

    if n is not None:
        selected = selected.head(n)

    log.info(f"  Selected {len(selected)} representative CFPs")
    log.info(f"  Laterality: {selected['laterality'].value_counts().to_dict()}")
    return selected


# ── Step 2: DICOM loading and preprocessing ───────────────────────────────────

def load_cfp_image(filepath: str) -> "np.ndarray":
    """Load a CFP DICOM file and return as (224, 224, 3) float32 array.

    Normalizes with ImageNet statistics for ViT input.
    """
    from PIL import Image
    import pydicom

    # Resolve path: manifest paths are relative to DATA_ROOT with leading /
    p = Path(filepath)
    if not p.exists():
        p = DATA_ROOT / filepath.lstrip("/")

    ds = pydicom.dcmread(str(p))
    arr = ds.pixel_array  # (H, W, 3) or (H, W) uint8/uint16

    # Ensure RGB
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    elif arr.shape[-1] == 1:
        arr = np.repeat(arr, 3, axis=-1)

    # Convert to PIL for consistent resizing
    if arr.dtype != np.uint8:
        # Normalize to 0-255
        arr = ((arr - arr.min()) / (arr.max() - arr.min() + 1e-8) * 255).astype(np.uint8)
    img = Image.fromarray(arr)
    img = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)

    # To float32 [0, 1]
    arr = np.array(img, dtype=np.float32) / 255.0

    # ImageNet normalization
    mean = np.array(IMAGENET_MEAN, dtype=np.float32)
    std = np.array(IMAGENET_STD, dtype=np.float32)
    arr = (arr - mean) / std

    return arr  # (224, 224, 3)


# ── Step 3: RETFound model loading ────────────────────────────────────────────

def _download_retfound_weights() -> Path:
    """Find or download RETFound CFP weights.

    Search order:
      1. models/RETFound_cfp_weights.pth (local project dir)
      2. HuggingFace Hub cache (requires auth for gated repos)
      3. Direct GitHub release URL
    """
    # 1. Check local project dir
    local_path = Path(__file__).resolve().parent.parent / "models" / RETFOUND_FILENAME
    if local_path.exists():
        return local_path

    # 2. Try HuggingFace Hub
    try:
        from huggingface_hub import hf_hub_download
        weights_path = hf_hub_download(
            repo_id=RETFOUND_HF_REPO,
            filename=RETFOUND_FILENAME,
        )
        return Path(weights_path)
    except Exception as e:
        log.warning(f"HuggingFace download failed ({e}), trying GitHub ...")

    # 3. Try GitHub release
    import urllib.request
    local_path.parent.mkdir(parents=True, exist_ok=True)
    gh_url = f"https://github.com/rmaphoh/RETFound_MAE/releases/download/v0.2/{RETFOUND_FILENAME}"
    try:
        urllib.request.urlretrieve(gh_url, local_path)
        return local_path
    except Exception:
        pass

    raise FileNotFoundError(
        f"Could not find RETFound weights. Please download manually:\n"
        f"  1. Visit https://github.com/rmaphoh/RETFound_MAE\n"
        f"  2. Download {RETFOUND_FILENAME} to {local_path}\n"
        f"  Or: huggingface-cli login && huggingface-cli download {RETFOUND_HF_REPO} {RETFOUND_FILENAME}"
    )


def _build_vit_large() -> "nn.Module":
    """Build a ViT-Large model compatible with RETFound weights.

    Uses timm if available, otherwise builds manually from torch.
    """
    if _HAS_TIMM:
        model = timm.create_model(
            "vit_large_patch16_224",
            pretrained=False,
            num_classes=0,  # remove classifier, returns features
            img_size=IMG_SIZE,
        )
    else:
        # Manual ViT-Large construction using torch
        from torch.nn import TransformerEncoder, TransformerEncoderLayer

        class PatchEmbed(nn.Module):
            def __init__(self, img_size=224, patch_size=16, in_chans=3, embed_dim=1024):
                super().__init__()
                self.num_patches = (img_size // patch_size) ** 2
                self.proj = nn.Conv2d(in_chans, embed_dim, kernel_size=patch_size, stride=patch_size)

            def forward(self, x):
                x = self.proj(x)  # (B, E, H/P, W/P)
                x = x.flatten(2).transpose(1, 2)  # (B, N, E)
                return x

        class VisionTransformer(nn.Module):
            def __init__(self, img_size=224, patch_size=16, embed_dim=1024,
                         depth=24, num_heads=16, mlp_ratio=4.0):
                super().__init__()
                self.patch_embed = PatchEmbed(img_size, patch_size, 3, embed_dim)
                num_patches = self.patch_embed.num_patches
                self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
                self.pos_embed = nn.Parameter(torch.zeros(1, num_patches + 1, embed_dim))
                encoder_layer = TransformerEncoderLayer(
                    d_model=embed_dim, nhead=num_heads,
                    dim_feedforward=int(embed_dim * mlp_ratio),
                    activation="gelu", batch_first=True, norm_first=True,
                )
                self.blocks = TransformerEncoder(encoder_layer, num_layers=depth)
                self.norm = nn.LayerNorm(embed_dim)

            def forward(self, x):
                B = x.shape[0]
                x = self.patch_embed(x)
                cls_tokens = self.cls_token.expand(B, -1, -1)
                x = torch.cat([cls_tokens, x], dim=1)
                x = x + self.pos_embed
                x = self.blocks(x)
                x = self.norm(x)
                return x[:, 0]  # CLS token

        model = VisionTransformer()

    return model


def load_retfound_model(device: "torch.device") -> "nn.Module":
    """Load RETFound ViT-Large with pretrained weights.

    Downloads weights if not cached. Falls back to ImageNet-pretrained ViT-Large
    if RETFound weights are unavailable (still produces useful embeddings).
    Loads into eval mode on the specified device.
    """
    log.info("Loading RETFound model ...")

    # Try to get RETFound weights
    weights_path = None
    use_retfound = True
    try:
        weights_path = _download_retfound_weights()
        log.info(f"  RETFound weights at: {weights_path}")
    except Exception as e:
        log.warning(
            f"RETFound weights not available: {e}\n"
            f"  Falling back to ImageNet-pretrained ViT-Large.\n"
            f"  For better results, download RETFound weights manually —\n"
            f"  see https://github.com/rmaphoh/RETFound_MAE"
        )
        use_retfound = False

    if use_retfound and _HAS_TIMM:
        # Use ImageNet-pretrained ViT as base, then load RETFound on top
        model = _build_vit_large()

        # Load RETFound weights (checkpoint has 'model' key from MAE pretraining)
        checkpoint = torch.load(weights_path, map_location="cpu", weights_only=False)
        state_dict = checkpoint.get("model", checkpoint)

        # Filter out decoder weights and mismatched keys
        model_keys = set(model.state_dict().keys())
        filtered = {}
        skipped = []
        for k, v in state_dict.items():
            clean_k = k.replace("encoder.", "")
            if clean_k in model_keys:
                if v.shape == model.state_dict()[clean_k].shape:
                    filtered[clean_k] = v
                else:
                    skipped.append(clean_k)
            else:
                skipped.append(k)

        missing, unexpected = model.load_state_dict(filtered, strict=False)
        log.info(f"  Loaded {len(filtered)} RETFound tensors, "
                 f"skipped {len(skipped)}, missing {len(missing)}")
    elif _HAS_TIMM:
        # Fallback: ImageNet-pretrained ViT-Large (still good features)
        log.info("  Using ImageNet-pretrained ViT-Large (timm) ...")
        model = timm.create_model(
            "vit_large_patch16_224",
            pretrained=True,
            num_classes=0,
            img_size=IMG_SIZE,
        )
    else:
        raise RuntimeError("Need either RETFound weights or timm for pretrained ViT.")

    model = model.to(device)
    model.eval()
    return model


# ── Step 3: Batch embedding extraction ────────────────────────────────────────

def extract_embeddings(
    selected: pd.DataFrame,
    model: "nn.Module",
    device: "torch.device",
    batch_size: int = BATCH_SIZE,
) -> pd.DataFrame:
    """Extract frozen RETFound embeddings for all selected CFPs.

    Returns DataFrame indexed by person_id with 1024 embedding columns.
    """
    log.info(f"Extracting embeddings for {len(selected)} images (batch_size={batch_size}) ...")

    person_ids = []
    embeddings = []
    n_errors = 0
    t0 = time.time()

    for batch_start in range(0, len(selected), batch_size):
        batch_df = selected.iloc[batch_start:batch_start + batch_size]
        batch_imgs = []
        batch_pids = []

        for _, row in batch_df.iterrows():
            try:
                img = load_cfp_image(row["filepath"])
                # (224, 224, 3) -> (3, 224, 224) for PyTorch
                img = img.transpose(2, 0, 1)
                batch_imgs.append(img)
                batch_pids.append(row["person_id"])
            except Exception as e:
                log.warning(f"  Error loading {row['person_id']}: {e}")
                n_errors += 1

        if not batch_imgs:
            continue

        batch_tensor = torch.tensor(np.stack(batch_imgs), dtype=torch.float32).to(device)

        with torch.no_grad():
            emb = model(batch_tensor)  # (B, 1024)

        embeddings.append(emb.cpu().numpy())
        person_ids.extend(batch_pids)

        n_done = min(batch_start + batch_size, len(selected))
        elapsed = time.time() - t0
        rate = n_done / elapsed
        log.info(f"  {n_done}/{len(selected)} ({rate:.1f} img/s)")

    if not embeddings:
        log.error("No embeddings extracted!")
        return pd.DataFrame()

    all_emb = np.vstack(embeddings)
    cols = [f"retinal_emb_{i}" for i in range(all_emb.shape[1])]
    emb_df = pd.DataFrame(all_emb, columns=cols)
    emb_df["person_id"] = person_ids
    emb_df = emb_df.set_index("person_id")

    elapsed = time.time() - t0
    log.info(f"  Done: {len(emb_df)} embeddings in {elapsed:.1f}s, {n_errors} errors")
    return emb_df


# ── Step 5-6: Train age regression and compute AgeAccel ──────────────────────

def train_retinal_age_clock(
    emb_df: pd.DataFrame,
    split_column: str = "recommended_split",
) -> pd.DataFrame:
    """Train Ridge regression from embeddings to age, compute AgeAccel.

    Uses the selected split column for train/val/test.
    AgeAccel is the residual from regressing predicted_age on chronological age
    (i.e., the portion of predicted age not explained by actual age).

    Returns DataFrame with person_id, age, retinal_predicted_age,
    retinal_age_accel, split.
    """
    from sklearn.linear_model import RidgeCV
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, r2_score

    log.info("Training retinal age clock ...")

    # Load feature matrix for age and splits
    fm = pd.read_parquet(result_path("feature_matrix.parquet"))
    fm = require_split_column(fm, split_column)
    meta = fm[["age", split_column]].copy()

    # Merge embeddings with metadata
    merged = emb_df.join(meta, how="inner")
    log.info(f"  Merged: {len(merged)} participants with embeddings + age")

    emb_cols = [c for c in emb_df.columns if c.startswith("retinal_emb_")]

    # Split
    train = merged[merged[split_column] == "train"]
    val = merged[merged[split_column] == "val"]
    test = merged[merged[split_column] == "test"]
    log.info(f"  Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")

    X_train = train[emb_cols].values
    y_train = train["age"].values
    X_val = val[emb_cols].values
    y_val = val["age"].values
    X_test = test[emb_cols].values
    y_test = test["age"].values

    # Standardize embeddings
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)

    # RidgeCV with cross-validation for alpha
    alphas = np.logspace(-2, 6, 50)
    ridge = RidgeCV(alphas=alphas, cv=5)
    ridge.fit(X_train_s, y_train)
    log.info(f"  Best alpha: {ridge.alpha_:.4f}")

    # Predict on all data
    X_all = scaler.transform(merged[emb_cols].values)
    merged = merged.copy()
    merged["retinal_predicted_age"] = ridge.predict(X_all)

    # Evaluate per split
    for name, mask in [("train", "train"), ("val", "val"), ("test", "test")]:
        subset = merged[merged[split_column] == mask]
        mae = mean_absolute_error(subset["age"], subset["retinal_predicted_age"])
        r2 = r2_score(subset["age"], subset["retinal_predicted_age"])
        log.info(f"  {name}: MAE={mae:.2f} years, R2={r2:.3f}")

    # Compute AgeAccel: residual from regressing predicted_age on age (train fit)
    from sklearn.linear_model import LinearRegression
    train_mask = merged[split_column] == "train"
    lr = LinearRegression()
    lr.fit(
        merged.loc[train_mask, "age"].values.reshape(-1, 1),
        merged.loc[train_mask, "retinal_predicted_age"].values,
    )
    expected = lr.predict(merged["age"].values.reshape(-1, 1))
    merged["retinal_age_accel"] = merged["retinal_predicted_age"] - expected

    # Output
    result = merged[["age", split_column, "retinal_predicted_age",
                      "retinal_age_accel"]].copy()
    result = result.rename(columns={split_column: "split"})
    result.index.name = "person_id"

    log.info(f"  AgeAccel stats: mean={result['retinal_age_accel'].mean():.3f}, "
             f"std={result['retinal_age_accel'].std():.2f}")
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Retinal aging clock via RETFound")
    parser.add_argument("--n", type=int, default=None,
                        help="Limit to first N participants (for testing)")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                        help=f"Batch size for GPU inference (default: {BATCH_SIZE})")
    parser.add_argument("--embeddings-only", action="store_true",
                        help="Extract and save embeddings only, skip age training")
    parser.add_argument("--from-embeddings", action="store_true",
                        help="Train age clock from saved embeddings (skip extraction)")
    parser.add_argument("--split-column", default="recommended_split",
                        help="Split column to use, e.g. recommended_split or balanced_split_v1")
    parser.add_argument("--output-suffix", default=None,
                        help="Optional artifact suffix. Defaults to split column for non-recommended splits.")
    args = parser.parse_args()
    variant = args.output_suffix
    if variant is None and args.split_column != "recommended_split":
        variant = args.split_column
    output_path = result_variant_path("retinal_age_accel.parquet", variant)

    if not _HAS_TORCH:
        log.error(
            "PyTorch is required for retinal embedding extraction.\n"
            "Install with: conda install pytorch torchvision pytorch-cuda=12.4 -c pytorch -c nvidia\n"
            "Also needed: pip install timm huggingface_hub pydicom pillow"
        )
        sys.exit(1)

    # --from-embeddings: skip extraction, train from saved
    if args.from_embeddings:
        if not EMBEDDINGS_PATH.exists():
            log.error(f"No saved embeddings at {EMBEDDINGS_PATH}")
            sys.exit(1)
        log.info(f"Loading saved embeddings from {EMBEDDINGS_PATH}")
        emb_df = pd.read_parquet(EMBEDDINGS_PATH)
        if emb_df.index.name != "person_id":
            emb_df = emb_df.set_index("person_id")
        result = train_retinal_age_clock(emb_df, split_column=args.split_column)
        result.to_parquet(output_path)
        log.info(f"Saved retinal age accel to {output_path}")
        return

    # Step 1: Select representative CFPs
    selected = select_representative_cfp(n=args.n)

    # Step 3: Load RETFound model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"Using device: {device}")
    if device.type == "cuda":
        log.info(f"  GPU: {torch.cuda.get_device_name(0)}")

    model = load_retfound_model(device)

    # Step 3: Extract embeddings
    emb_df = extract_embeddings(selected, model, device, batch_size=args.batch_size)

    if emb_df.empty:
        log.error("No embeddings produced. Exiting.")
        sys.exit(1)

    # Step 4: Save embeddings
    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    emb_df.to_parquet(EMBEDDINGS_PATH)
    log.info(f"Saved embeddings to {EMBEDDINGS_PATH}")

    if args.embeddings_only:
        log.info("--embeddings-only mode, skipping age training.")
        return

    # Steps 5-7: Train age clock and save
    result = train_retinal_age_clock(emb_df, split_column=args.split_column)
    result.to_parquet(output_path)
    log.info(f"Saved retinal age accel to {output_path}")


if __name__ == "__main__":
    main()
