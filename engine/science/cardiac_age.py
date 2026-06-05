"""Cardiac aging clock using ECGFounder embeddings or ECG interval features.

Two modes:
  1. ECGFounder (GPU): Extract embeddings from pretrained 1D-CNN, train Ridge age head
  2. Interval fallback (CPU-only): Train Ridge on ECG interval features from manifest
     (ecg_rate, ecg_pr, ecg_qrsd, ecg_qt, ecg_qtc)

The interval fallback always works and requires only pandas + sklearn (no PyTorch).

Pipeline:
    1. Load ECG manifest / participant index
    2. Preprocess waveforms (if using ECGFounder): highpass, notch, trim, z-score
    3. Extract embeddings OR assemble interval feature matrix
    4. Train Ridge regression: features -> age (train split)
    5. Compute cardiac AgeAccel
    6. Save -> results/clocks/cardiac_age_accel.parquet

Usage:
    python -m scripts.cardiac_age                    # ECGFounder if available, else fallback
    python -m scripts.cardiac_age --fallback         # force interval-based fallback
    python -m scripts.cardiac_age --n 20             # first 20 participants (testing)
    python -m scripts.cardiac_age --from-embeddings  # train from saved embeddings
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .config import (
    DATA_ROOT, ECG_DATA_DIR, ECG_MANIFEST,
    ECG_SAMPLE_RATE, ECG_NUM_SAMPLES, ECG_NUM_LEADS, ECG_GAIN, ECG_LEAD_NAMES,
    result_path, result_variant_path,
)
from .splits import require_split_column

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Dependency checks ─────────────────────────────────────────────────────────

_HAS_TORCH = False
_HAS_SCIPY = False

try:
    import torch
    import torch.nn as nn
    _HAS_TORCH = True
except ImportError:
    pass

try:
    from scipy.signal import butter, filtfilt, iirnotch
    _HAS_SCIPY = True
except ImportError:
    pass

# ── Constants ─────────────────────────────────────────────────────────────────

ECGFOUNDER_HF_REPO = "PKUDigitalHealth/ECGFounder"
TARGET_SAMPLES = 5000       # 10s at 500Hz for ECGFounder
BATCH_SIZE = 64             # ECG tensors are small; large batches OK
INTERVAL_FEATURES = ["ecg_rate", "ecg_pr", "ecg_qrsd", "ecg_qt", "ecg_qtc"]

EMBEDDINGS_PATH = result_path("cardiac_embeddings.parquet")
OUTPUT_PATH = result_path("cardiac_age_accel.parquet")


# ── ECG waveform preprocessing ────────────────────────────────────────────────

def preprocess_ecg(signal_mv: np.ndarray, fs: int = ECG_SAMPLE_RATE) -> np.ndarray:
    """Preprocess 12-lead ECG for ECGFounder.

    Input:  (5500, 12) in millivolts
    Output: (12, 5000) float32, filtered and z-scored per lead

    Steps:
        1. Trim to first 5000 samples (10s)
        2. 0.5 Hz highpass Butterworth (order 3)
        3. 50 Hz notch filter (powerline)
        4. 60 Hz notch filter (powerline, US standard)
        5. z-score per lead
    """
    if not _HAS_SCIPY:
        # Minimal preprocessing without scipy: just trim and z-score
        sig = signal_mv[:TARGET_SAMPLES, :].copy()  # (5000, 12)
        sig = sig.T  # (12, 5000)
        for i in range(sig.shape[0]):
            lead = sig[i]
            mu, std = lead.mean(), lead.std()
            if std > 1e-6:
                sig[i] = (lead - mu) / std
            else:
                sig[i] = lead - mu
        return sig.astype(np.float32)

    sig = signal_mv[:TARGET_SAMPLES, :].copy()  # (5000, 12)

    # Highpass 0.5 Hz
    b_hp, a_hp = butter(3, 0.5, btype="high", fs=fs)
    for i in range(sig.shape[1]):
        sig[:, i] = filtfilt(b_hp, a_hp, sig[:, i])

    # Notch filters at 50 Hz and 60 Hz
    for freq in [50.0, 60.0]:
        if freq < fs / 2:
            b_n, a_n = iirnotch(freq, Q=30, fs=fs)
            for i in range(sig.shape[1]):
                sig[:, i] = filtfilt(b_n, a_n, sig[:, i])

    # Transpose to (12, 5000) and z-score per lead
    sig = sig.T  # (12, 5000)
    for i in range(sig.shape[0]):
        lead = sig[i]
        mu, std = lead.mean(), lead.std()
        if std > 1e-6:
            sig[i] = (lead - mu) / std
        else:
            sig[i] = lead - mu

    return sig.astype(np.float32)


def load_ecg_signal_raw(person_id: str, manifest: pd.DataFrame) -> np.ndarray | None:
    """Load first ECG recording for a participant as (5500, 12) array in mV.

    Returns None if files are missing or unreadable.
    """
    rows = manifest[manifest["person_id"] == person_id]
    if rows.empty:
        return None

    row = rows.iloc[0]
    dat_rel = row["wfdb_dat_filepath"]
    dat_path = DATA_ROOT / dat_rel.lstrip("/")

    if not dat_path.exists():
        return None

    try:
        raw = np.fromfile(str(dat_path), dtype="<i2")
        signal = raw.reshape(ECG_NUM_SAMPLES, ECG_NUM_LEADS)
        return signal.astype(np.float32) / ECG_GAIN
    except Exception:
        return None


# ── ECGFounder model architecture ────────────────────────────────────────────

ECGFOUNDER_WEIGHTS = Path(__file__).resolve().parent.parent / "models" / "ecgfounder" / "12_lead_ECGFounder.pth"

# Stage config derived from the checkpoint:
#   (out_channels, num_blocks, group_width)
# Channel transitions: 64->64, 64->160, 160->160, 160->400, 400->400, 400->1024, 1024->1024
_STAGE_CONFIGS = [
    (64,   2, 16),   # stage 0: 64  channels, 2 blocks
    (160,  2, 16),   # stage 1: 160 channels, 2 blocks
    (160,  2, 16),   # stage 2: 160 channels, 2 blocks
    (400,  3, 16),   # stage 3: 400 channels, 3 blocks
    (400,  3, 16),   # stage 4: 400 channels, 3 blocks
    (1024, 4, 16),   # stage 5: 1024 channels, 4 blocks
    (1024, 4, 16),   # stage 6: 1024 channels, 4 blocks
]


class _ConvWrap(nn.Module):
    """Wrapper so that weights live under `conv.weight` / `conv.bias`.

    Uses padding = kernel_size // 2 and trims output to input length when
    the kernel size is even (e.g. 16), ensuring length-preserving behaviour.
    """
    def __init__(self, in_ch: int, out_ch: int, kernel_size: int,
                 stride: int = 1, groups: int = 1, bias: bool = True):
        super().__init__()
        self._ks = kernel_size
        padding = kernel_size // 2
        self.conv = nn.Conv1d(in_ch, out_ch, kernel_size, stride=stride,
                              padding=padding, groups=groups, bias=bias)

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        L_in = x.shape[2]
        out = self.conv(x)
        # Even kernels with pad=k//2 produce output 1 sample longer than input.
        # Trim from the right to keep length consistent.
        if self._ks % 2 == 0 and out.shape[2] > L_in:
            out = out[:, :, :L_in]
        return out


class _RegNetBlock(nn.Module):
    """Single RegNet-Y 1D block with SE.

    Order: BN1 -> Conv1(1x1) -> BN2 -> Conv2(grouped, k=16) -> BN3 -> Conv3(1x1) -> SE + residual.

    SE weights (se_fc1, se_fc2) live directly on the block (not nested in a
    sub-module) to match the checkpoint key structure.
    """

    def __init__(self, in_ch: int, out_ch: int, group_width: int = 16,
                 stride: int = 1):
        super().__init__()
        self.has_skip = (in_ch == out_ch and stride == 1)
        groups = out_ch // group_width
        se_mid = out_ch // 2

        self.bn1 = nn.BatchNorm1d(in_ch)
        self.conv1 = _ConvWrap(in_ch, out_ch, kernel_size=1)
        self.bn2 = nn.BatchNorm1d(out_ch)
        self.conv2 = _ConvWrap(out_ch, out_ch, kernel_size=16,
                               stride=stride, groups=groups)
        self.bn3 = nn.BatchNorm1d(out_ch)
        self.conv3 = _ConvWrap(out_ch, out_ch, kernel_size=1)

        # SE layers directly on block (keys: se_fc1.weight, se_fc2.weight)
        self.se_fc1 = nn.Linear(out_ch, se_mid)
        self.se_fc2 = nn.Linear(se_mid, out_ch)

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        identity = x

        out = torch.relu(self.bn1(x))
        out = self.conv1(out)
        out = torch.relu(self.bn2(out))
        out = self.conv2(out)
        out = torch.relu(self.bn3(out))
        out = self.conv3(out)

        # Squeeze-and-Excitation
        s = out.mean(dim=2)                         # (B, C)
        s = torch.relu(self.se_fc1(s))              # (B, C//2)
        s = torch.sigmoid(self.se_fc2(s))           # (B, C)
        out = out * s.unsqueeze(2)                   # (B, C, L)

        if self.has_skip:
            out = out + identity
        return out


class _RegNetStage(nn.Module):
    """One stage of RegNet-Y containing multiple blocks."""

    def __init__(self, in_ch: int, out_ch: int, num_blocks: int,
                 group_width: int = 16, stride: int = 1):
        super().__init__()
        blocks = []
        for i in range(num_blocks):
            blk_in = in_ch if i == 0 else out_ch
            blk_stride = stride if i == 0 else 1
            blocks.append(_RegNetBlock(blk_in, out_ch, group_width, blk_stride))
        self.block_list = nn.ModuleList(blocks)

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        for blk in self.block_list:
            x = blk(x)
        return x


class ECGFounderBackbone(nn.Module):
    """ECGFounder RegNet-Y 1D backbone (no classification head).

    Input:  (batch, 12, 5000)
    Output: (batch, 1024) after global average pooling
    """

    def __init__(self):
        super().__init__()
        self.first_conv = _ConvWrap(12, 64, kernel_size=16)
        self.first_bn = nn.BatchNorm1d(64)

        self.stage_list = nn.ModuleList()
        in_ch = 64
        for out_ch, num_blocks, gw in _STAGE_CONFIGS:
            self.stage_list.append(
                _RegNetStage(in_ch, out_ch, num_blocks, group_width=gw)
            )
            in_ch = out_ch

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        # x: (B, 12, 5000)
        x = torch.relu(self.first_bn(self.first_conv(x)))
        for stage in self.stage_list:
            x = stage(x)
        # Global average pooling -> (B, 1024)
        x = x.mean(dim=2)
        return x


# ── ECGFounder model loading ──────────────────────────────────────────────────

def load_ecgfounder_model(device: "torch.device") -> "nn.Module":
    """Load ECGFounder backbone from local checkpoint.

    Builds a RegNet-Y 1D CNN matching the checkpoint structure, loads all
    backbone weights (507 keys; drops the 150-class dense head), and returns
    the model in eval mode producing 1024-dim embeddings.
    """
    if not ECGFOUNDER_WEIGHTS.exists():
        raise FileNotFoundError(
            f"ECGFounder weights not found at {ECGFOUNDER_WEIGHTS}"
        )

    log.info(f"Loading ECGFounder from {ECGFOUNDER_WEIGHTS} ...")

    ckpt = torch.load(str(ECGFOUNDER_WEIGHTS), map_location="cpu",
                       weights_only=False)
    state_dict = ckpt["state_dict"]

    # Remove the dense classification head (we want embeddings only)
    backbone_sd = {k: v for k, v in state_dict.items()
                   if not k.startswith("dense")}

    model = ECGFounderBackbone()

    # Load weights -- must match exactly
    missing, unexpected = model.load_state_dict(backbone_sd, strict=False)
    if unexpected:
        log.warning(f"  Unexpected keys in checkpoint: {unexpected}")
    if missing:
        log.warning(f"  Missing keys (not in checkpoint): {missing}")

    n_loaded = len(backbone_sd)
    n_model = sum(1 for _ in model.state_dict())
    log.info(f"  Loaded {n_loaded} keys into backbone ({n_model} model keys)")

    model = model.to(device).eval()
    log.info(f"  Model on {device}, eval mode, output dim = 1024")
    return model


def extract_ecg_embeddings(
    person_ids: list[str],
    manifest: pd.DataFrame,
    model: "nn.Module",
    device: "torch.device",
    batch_size: int = BATCH_SIZE,
) -> pd.DataFrame:
    """Extract ECGFounder 1024-dim embeddings for all participants.

    Returns DataFrame indexed by person_id with 1024 embedding columns.
    """
    log.info(f"Extracting ECG embeddings for {len(person_ids)} participants ...")

    all_pids = []
    all_embs = []
    n_errors = 0
    t0 = time.time()

    for batch_start in range(0, len(person_ids), batch_size):
        batch_pids = person_ids[batch_start:batch_start + batch_size]
        batch_signals = []
        batch_valid_pids = []

        for pid in batch_pids:
            sig = load_ecg_signal_raw(pid, manifest)
            if sig is None:
                n_errors += 1
                continue
            preprocessed = preprocess_ecg(sig)  # (12, 5000)
            batch_signals.append(preprocessed)
            batch_valid_pids.append(pid)

        if not batch_signals:
            continue

        batch_tensor = torch.tensor(
            np.stack(batch_signals), dtype=torch.float32
        ).to(device)

        with torch.no_grad():
            emb = model(batch_tensor)  # (batch, 1024)

        all_embs.append(emb.cpu().numpy())
        all_pids.extend(batch_valid_pids)

        n_done = min(batch_start + batch_size, len(person_ids))
        elapsed = time.time() - t0
        log.info(f"  {n_done}/{len(person_ids)} ({n_done / elapsed:.1f} ecg/s)")

    if not all_embs:
        return pd.DataFrame()

    emb_array = np.vstack(all_embs)
    cols = [f"cardiac_emb_{i}" for i in range(emb_array.shape[1])]
    df = pd.DataFrame(emb_array, columns=cols)
    df["person_id"] = all_pids
    df = df.set_index("person_id")

    elapsed = time.time() - t0
    log.info(f"  Done: {len(df)} embeddings in {elapsed:.1f}s, {n_errors} errors")
    return df


# ── Interval-based fallback ───────────────────────────────────────────────────

def build_interval_features() -> pd.DataFrame:
    """Build ECG interval feature matrix from participant_index.parquet.

    Uses: ecg_rate, ecg_pr, ecg_qrsd, ecg_qt, ecg_qtc
    Returns DataFrame indexed by person_id with the 5 interval features.
    """
    log.info("Building ECG interval feature matrix (fallback mode) ...")
    pi = pd.read_parquet(result_path("participant_index.parquet"))

    # Filter to participants with ECG data
    has_ecg = pi["cardiac_ecg"].fillna(False).astype(bool)
    ecg_pi = pi[has_ecg][INTERVAL_FEATURES].copy()

    n_before = len(ecg_pi)
    ecg_pi = ecg_pi.dropna(subset=INTERVAL_FEATURES, how="all")
    log.info(f"  {len(ecg_pi)} participants with ECG interval features "
             f"({n_before - len(ecg_pi)} dropped for all-NaN)")

    return ecg_pi


# ── Train age clock (shared for both modes) ──────────────────────────────────

def train_cardiac_age_clock(
    features_df: pd.DataFrame,
    feature_prefix: str = "cardiac",
    split_column: str = "recommended_split",
) -> pd.DataFrame:
    """Train Ridge regression from features to age, compute AgeAccel.

    Works for both embedding features (cardiac_emb_*) and interval features
    (ecg_rate, ecg_pr, ...).

    Returns DataFrame with person_id, age, cardiac_predicted_age,
    cardiac_age_accel, split.
    """
    from sklearn.linear_model import RidgeCV, LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import mean_absolute_error, r2_score

    log.info("Training cardiac age clock ...")

    # Load feature matrix for age and splits
    fm = pd.read_parquet(result_path("feature_matrix.parquet"))
    fm = require_split_column(fm, split_column)
    meta = fm[["age", split_column]].copy()

    # Merge features with metadata
    merged = features_df.join(meta, how="inner")
    log.info(f"  Merged: {len(merged)} participants with features + age")

    feat_cols = [c for c in features_df.columns]

    # Split
    train = merged[merged[split_column] == "train"]
    val = merged[merged[split_column] == "val"]
    test = merged[merged[split_column] == "test"]
    log.info(f"  Train: {len(train)}, Val: {len(val)}, Test: {len(test)}")

    if len(train) < 10:
        log.error("Too few training samples. Aborting.")
        return pd.DataFrame()

    X_train = train[feat_cols].values
    y_train = train["age"].values
    X_val = val[feat_cols].values
    y_val = val["age"].values
    X_test = test[feat_cols].values
    y_test = test["age"].values
    X_all = merged[feat_cols].values

    # Impute missing values (median strategy, relevant for interval features)
    imputer = SimpleImputer(strategy="median")
    X_train = imputer.fit_transform(X_train)
    X_val = imputer.transform(X_val)
    X_test = imputer.transform(X_test)
    X_all = imputer.transform(X_all)

    # Standardize
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)
    X_all_s = scaler.transform(X_all)

    # RidgeCV
    alphas = np.logspace(-2, 6, 50)
    ridge = RidgeCV(alphas=alphas, cv=5)
    ridge.fit(X_train_s, y_train)
    log.info(f"  Best alpha: {ridge.alpha_:.4f}")

    # Feature importances (for interval mode, show which features matter)
    if len(feat_cols) <= 10:
        coef_mag = np.abs(ridge.coef_)
        for fname, coef in sorted(zip(feat_cols, coef_mag), key=lambda x: -x[1]):
            log.info(f"    |coef| {fname}: {coef:.4f}")

    # Predict on all data
    pred_all = ridge.predict(X_all_s)
    merged = merged.copy()
    merged["cardiac_predicted_age"] = pred_all

    # Evaluate per split
    for name, split_name in [("train", "train"), ("val", "val"), ("test", "test")]:
        subset = merged[merged[split_column] == split_name]
        if len(subset) == 0:
            continue
        mae = mean_absolute_error(subset["age"], subset["cardiac_predicted_age"])
        r2 = r2_score(subset["age"], subset["cardiac_predicted_age"])
        log.info(f"  {name}: MAE={mae:.2f} years, R2={r2:.3f}")

    # AgeAccel: residual from regressing predicted_age on chronological age
    train_mask = merged[split_column] == "train"
    lr = LinearRegression()
    lr.fit(
        merged.loc[train_mask, "age"].values.reshape(-1, 1),
        merged.loc[train_mask, "cardiac_predicted_age"].values,
    )
    expected = lr.predict(merged["age"].values.reshape(-1, 1))
    merged["cardiac_age_accel"] = merged["cardiac_predicted_age"] - expected

    # Output
    result = merged[["age", split_column, "cardiac_predicted_age",
                      "cardiac_age_accel"]].copy()
    result = result.rename(columns={split_column: "split"})
    result.index.name = "person_id"

    log.info(f"  AgeAccel stats: mean={result['cardiac_age_accel'].mean():.3f}, "
             f"std={result['cardiac_age_accel'].std():.2f}")
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cardiac aging clock")
    parser.add_argument("--n", type=int, default=None,
                        help="Limit to first N participants (for testing)")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                        help=f"Batch size for GPU inference (default: {BATCH_SIZE})")
    parser.add_argument("--fallback", action="store_true",
                        help="Force interval-based fallback (no GPU/PyTorch needed)")
    parser.add_argument("--embeddings-only", action="store_true",
                        help="Extract and save embeddings only")
    parser.add_argument("--from-embeddings", action="store_true",
                        help="Train from saved embeddings (skip extraction)")
    parser.add_argument("--split-column", default="recommended_split",
                        help="Split column to use, e.g. recommended_split or balanced_split_v1")
    parser.add_argument("--output-suffix", default=None,
                        help="Optional artifact suffix. Defaults to split column for non-recommended splits.")
    args = parser.parse_args()
    variant = args.output_suffix
    if variant is None and args.split_column != "recommended_split":
        variant = args.split_column
    output_path = result_variant_path("cardiac_age_accel.parquet", variant)

    # ── From saved embeddings ────────────────────────────────────────────
    if args.from_embeddings:
        if not EMBEDDINGS_PATH.exists():
            log.error(f"No saved embeddings at {EMBEDDINGS_PATH}")
            sys.exit(1)
        log.info(f"Loading saved embeddings from {EMBEDDINGS_PATH}")
        emb_df = pd.read_parquet(EMBEDDINGS_PATH)
        if emb_df.index.name != "person_id":
            emb_df = emb_df.set_index("person_id")
        result = train_cardiac_age_clock(emb_df, split_column=args.split_column)
        result.to_parquet(output_path)
        log.info(f"Saved cardiac age accel to {output_path}")
        return

    # ── Interval-based fallback ──────────────────────────────────────────
    use_fallback = args.fallback or not _HAS_TORCH

    if use_fallback:
        if not args.fallback:
            log.info("PyTorch not available. Using interval-based fallback.")
        else:
            log.info("Using interval-based fallback (--fallback flag).")

        feat_df = build_interval_features()
        if args.n is not None:
            feat_df = feat_df.head(args.n)

        result = train_cardiac_age_clock(feat_df, split_column=args.split_column)
        if result.empty:
            log.error("Training failed. Exiting.")
            sys.exit(1)
        result.to_parquet(output_path)
        log.info(f"Saved cardiac age accel to {output_path}")
        return

    # ── ECGFounder mode (GPU) ────────────────────────────────────────────
    log.info("Attempting ECGFounder embedding extraction ...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"Using device: {device}")
    if device.type == "cuda":
        log.info(f"  GPU: {torch.cuda.get_device_name(0)}")

    # Load ECG manifest
    ecg_manifest = pd.read_csv(ECG_MANIFEST, sep="\t", dtype={"person_id": str})
    person_ids = sorted(ecg_manifest["person_id"].unique().tolist())
    if args.n is not None:
        person_ids = person_ids[:args.n]
    log.info(f"  {len(person_ids)} participants with ECG data")

    # Try loading ECGFounder
    try:
        model = load_ecgfounder_model(device)

        # Extract embeddings
        emb_df = extract_ecg_embeddings(
            person_ids, ecg_manifest, model, device, batch_size=args.batch_size,
        )

        if emb_df.empty:
            raise RuntimeError("No embeddings extracted")

        # Save embeddings
        EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        emb_df.to_parquet(EMBEDDINGS_PATH)
        log.info(f"Saved embeddings to {EMBEDDINGS_PATH}")

        if args.embeddings_only:
            return

        # Train age clock from embeddings
        result = train_cardiac_age_clock(emb_df, split_column=args.split_column)

    except Exception as e:
        log.warning(f"ECGFounder failed: {e}")
        log.info("Falling back to interval-based features ...")
        feat_df = build_interval_features()
        if args.n is not None:
            feat_df = feat_df.head(args.n)
        result = train_cardiac_age_clock(feat_df, split_column=args.split_column)

    if result.empty:
        log.error("Training failed. Exiting.")
        sys.exit(1)

    result.to_parquet(output_path)
    log.info(f"Saved cardiac age accel to {output_path}")


if __name__ == "__main__":
    main()
