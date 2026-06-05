"""Extract first-pass OCTA en face and segmentation biomarkers.

The initial target is a device/protocol-consistent subset:
Topcon Maestro2 macula 6 x 6 OCTA. This avoids mixing scanner/protocol effects
while we test whether OCTA-derived vascular/structural proxies map to MoCA.

Usage:
    python -m neuro_moca_mapping.extract_octa_biomarkers
    python -m neuro_moca_mapping.extract_octa_biomarkers --max-persons 50
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import pydicom

from scripts.config import DATA_ROOT, OCTA_MANIFEST, RESULTS_DIR


DEFAULT_OUTPUT_DIR = RESULTS_DIR / "neuro_moca_mapping"
DEFAULT_DEVICE = "Maestro2"
DEFAULT_REGION = "Macula, 6 x 6"
MISSING_PATH_VALUES = {"", "Not reported", "Not Reported", "nan", "NaN"}


def resolve_manifest_path(filepath: str | Path) -> Path:
    path = Path(str(filepath))
    if path.exists():
        return path
    return DATA_ROOT / str(path).lstrip("/")


def safe_slug(value: str) -> str:
    out = []
    for ch in str(value).lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "_":
            out.append("_")
    return "".join(out).strip("_")


def load_pixels(filepath: str | Path) -> np.ndarray:
    path = resolve_manifest_path(filepath)
    ds = pydicom.dcmread(str(path))
    return ds.pixel_array


def otsu_threshold_uint8(image: np.ndarray) -> int:
    arr = np.asarray(image)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    hist = np.bincount(arr.ravel(), minlength=256).astype(np.float64)
    total = hist.sum()
    if total <= 0:
        return 0

    prob = hist / total
    omega = np.cumsum(prob)
    centers = np.arange(256, dtype=np.float64)
    mu = np.cumsum(prob * centers)
    mu_t = mu[-1]
    denom = omega * (1.0 - omega)
    denom[denom <= 0] = np.nan
    sigma_b = (mu_t * omega - mu) ** 2 / denom
    if np.all(np.isnan(sigma_b)):
        return int(np.nanmedian(arr))
    return int(np.nanargmax(sigma_b))


def entropy_uint8(image: np.ndarray) -> float:
    arr = np.clip(np.asarray(image), 0, 255).astype(np.uint8)
    hist = np.bincount(arr.ravel(), minlength=256).astype(np.float64)
    prob = hist / hist.sum()
    prob = prob[prob > 0]
    return float(-(prob * np.log2(prob)).sum())


def enface_features(image: np.ndarray, prefix: str) -> dict[str, float]:
    arr = np.asarray(image, dtype=np.float32)
    finite = np.isfinite(arr)
    values = arr[finite]
    if values.size == 0:
        return {}

    threshold = otsu_threshold_uint8(values)
    row_mean = np.nanmean(arr, axis=1)
    col_mean = np.nanmean(arr, axis=0)
    mean_value = float(np.nanmean(values))
    eps = 1e-6
    features = {
        f"{prefix}_mean": mean_value,
        f"{prefix}_std": float(np.nanstd(values)),
        f"{prefix}_p01": float(np.nanpercentile(values, 1)),
        f"{prefix}_p10": float(np.nanpercentile(values, 10)),
        f"{prefix}_p50": float(np.nanpercentile(values, 50)),
        f"{prefix}_p90": float(np.nanpercentile(values, 90)),
        f"{prefix}_p99": float(np.nanpercentile(values, 99)),
        f"{prefix}_nonzero_frac": float(np.mean(values > 0)),
        f"{prefix}_low_signal_frac": float(np.mean(values <= 5)),
        f"{prefix}_saturated_frac": float(np.mean(values >= 250)),
        f"{prefix}_otsu_threshold": float(threshold),
        f"{prefix}_otsu_flow_frac": float(np.mean(values > threshold)),
        f"{prefix}_entropy": entropy_uint8(values),
        f"{prefix}_row_band_cv": float(np.nanstd(row_mean) / (abs(float(np.nanmean(row_mean))) + eps)),
        f"{prefix}_col_band_cv": float(np.nanstd(col_mean) / (abs(float(np.nanmean(col_mean))) + eps)),
    }
    foreground = values[values > threshold]
    features[f"{prefix}_foreground_mean"] = (
        float(np.nanmean(foreground)) if foreground.size else float("nan")
    )
    return features


def segmentation_features(segmentation: np.ndarray, prefix: str = "seg") -> dict[str, float]:
    arr = np.asarray(segmentation, dtype=np.float32)
    if arr.ndim != 3:
        return {}
    arr[~np.isfinite(arr)] = np.nan
    n_surfaces = arr.shape[0]
    features: dict[str, float] = {
        f"{prefix}_n_surfaces": float(n_surfaces),
        f"{prefix}_height": float(arr.shape[1]),
        f"{prefix}_width": float(arr.shape[2]),
    }

    for idx in range(n_surfaces):
        surface = arr[idx]
        features[f"{prefix}_surface_{idx}_mean_px"] = float(np.nanmean(surface))
        features[f"{prefix}_surface_{idx}_std_px"] = float(np.nanstd(surface))

    if n_surfaces >= 2:
        diffs = np.diff(arr, axis=0)
        for idx in range(diffs.shape[0]):
            diff = diffs[idx]
            features[f"{prefix}_thickness_{idx}_{idx + 1}_mean_px"] = float(np.nanmean(diff))
            features[f"{prefix}_thickness_{idx}_{idx + 1}_std_px"] = float(np.nanstd(diff))
            features[f"{prefix}_thickness_{idx}_{idx + 1}_abs_mean_px"] = float(np.nanmean(np.abs(diff)))
        total = arr[-1] - arr[0]
        features[f"{prefix}_total_thickness_mean_px"] = float(np.nanmean(total))
        features[f"{prefix}_total_thickness_std_px"] = float(np.nanstd(total))
        features[f"{prefix}_total_thickness_abs_mean_px"] = float(np.nanmean(np.abs(total)))
    return features


def has_reported_path(value: object) -> bool:
    if value is None:
        return False
    text = str(value)
    return text not in MISSING_PATH_VALUES


def process_octa_row(row: pd.Series, include_segmentation: bool = True) -> dict[str, object]:
    record: dict[str, object] = {
        "person_id": str(row["person_id"]),
        "manufacturer": str(row["manufacturers_model_name"]),
        "anatomic_region": str(row["anatomic_region"]),
        "laterality": str(row["laterality"]),
        "flow_cube_height": float(row.get("flow_cube_height", np.nan)),
        "flow_cube_width": float(row.get("flow_cube_width", np.nan)),
        "flow_cube_number_of_frames": float(row.get("flow_cube_number_of_frames", np.nan)),
    }

    for layer_idx in range(1, 5):
        path_col = f"associated_enface_{layer_idx}_file_path"
        type_col = f"associated_enface_{layer_idx}_ophthalmic_image_type"
        layer_type = str(row.get(type_col, f"enface_{layer_idx}"))
        record[f"enface_{layer_idx}_type"] = layer_type
        if not has_reported_path(row.get(path_col)):
            continue
        try:
            image = load_pixels(row[path_col])
            record.update(enface_features(image, f"enface_{layer_idx}"))
        except Exception as exc:  # noqa: BLE001 - keep batch extraction moving.
            record[f"enface_{layer_idx}_error"] = str(exc)

    seg_path = row.get("associated_segmentation_file_path")
    if include_segmentation and has_reported_path(seg_path):
        try:
            segmentation = load_pixels(seg_path)
            record.update(segmentation_features(segmentation))
        except Exception as exc:  # noqa: BLE001
            record["seg_error"] = str(exc)
    return record


def select_rows(manifest: pd.DataFrame, device: str, region: str, max_persons: int | None) -> pd.DataFrame:
    mask = manifest["manufacturers_model_name"].astype(str).str.casefold().eq(device.casefold())
    mask &= manifest["anatomic_region"].astype(str).str.casefold().eq(region.casefold())
    rows = manifest.loc[mask].copy()
    rows = rows.sort_values(["person_id", "laterality", "flow_cube_sop_instance_uid"])
    if max_persons is not None:
        keep_people = rows["person_id"].drop_duplicates().head(max_persons)
        rows = rows[rows["person_id"].isin(set(keep_people))]
    return rows


def aggregate_participant_features(acq: pd.DataFrame, prefix: str) -> pd.DataFrame:
    numeric_cols = [
        c for c in acq.columns
        if c not in {"person_id"}
        and pd.api.types.is_numeric_dtype(acq[c])
        and not c.endswith("_height")
        and not c.endswith("_width")
        and not c.endswith("_number_of_frames")
    ]

    mean_features = acq.groupby("person_id", sort=True)[numeric_cols].mean()
    mean_features.columns = [f"{prefix}_{c}_mean_eyes" for c in mean_features.columns]

    count_features = pd.DataFrame({
        f"{prefix}_n_acquisitions": acq.groupby("person_id").size(),
        f"{prefix}_n_lateralities": acq.groupby("person_id")["laterality"].nunique(),
    })

    side_means = acq.groupby(["person_id", "laterality"])[numeric_cols].mean().reset_index()
    asymmetry = pd.DataFrame(index=mean_features.index)
    if {"L", "R"}.issubset(set(side_means["laterality"].dropna())):
        left = side_means[side_means["laterality"].eq("L")].set_index("person_id")
        right = side_means[side_means["laterality"].eq("R")].set_index("person_id")
        common = left.index.intersection(right.index)
        diff = (right.loc[common, numeric_cols] - left.loc[common, numeric_cols]).abs()
        diff.columns = [f"{prefix}_{c}_abs_rl_diff" for c in diff.columns]
        asymmetry = diff

    out = count_features.join(mean_features, how="left").join(asymmetry, how="left")
    out.index = out.index.astype(str)
    out.index.name = "person_id"
    return out


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(OCTA_MANIFEST, sep="\t", dtype={"person_id": str}, low_memory=False)
    rows = select_rows(manifest, args.device, args.region, args.max_persons)
    if rows.empty:
        raise ValueError(f"No OCTA rows found for device={args.device!r}, region={args.region!r}")

    print(
        f"Processing {len(rows)} OCTA acquisitions from {rows['person_id'].nunique()} participants "
        f"({args.device}, {args.region})"
    )

    records: list[dict[str, object]] = []
    row_records = [row.to_dict() for _, row in rows.iterrows()]
    if args.workers <= 1:
        for i, row in enumerate(row_records, start=1):
            records.append(process_octa_row(pd.Series(row), include_segmentation=not args.skip_segmentation))
            if args.progress_every and (i % args.progress_every == 0 or i == len(row_records)):
                print(f"  processed {i}/{len(row_records)} acquisitions")
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(
                    process_octa_row,
                    pd.Series(row),
                    not args.skip_segmentation,
                )
                for row in row_records
            ]
            for i, future in enumerate(as_completed(futures), start=1):
                records.append(future.result())
                if args.progress_every and (i % args.progress_every == 0 or i == len(row_records)):
                    print(f"  processed {i}/{len(row_records)} acquisitions")

    acq = pd.DataFrame(records)
    feature_prefix = f"octa_{safe_slug(args.device)}_{safe_slug(args.region)}"
    participant = aggregate_participant_features(acq, feature_prefix)

    suffix = f"{safe_slug(args.device)}_{safe_slug(args.region)}"
    if args.skip_segmentation:
        suffix = f"{suffix}_enface_only"
    if args.max_persons is not None:
        suffix = f"{suffix}_pilot{args.max_persons}"

    acq_path = output_dir / f"octa_{suffix}_acquisition_features.parquet"
    participant_path = output_dir / f"octa_{suffix}_participant_features.parquet"
    acq.to_parquet(acq_path, index=False)
    participant.to_parquet(participant_path)

    summary = {
        "device": args.device,
        "region": args.region,
        "n_acquisitions": int(len(acq)),
        "n_participants": int(participant.shape[0]),
        "n_participant_features": int(participant.shape[1]),
        "acquisition_features_path": str(acq_path),
        "participant_features_path": str(participant_path),
    }
    pd.Series(summary).to_json(output_dir / f"octa_{suffix}_feature_summary.json", indent=2)
    print(f"Wrote acquisition features: {acq_path}")
    print(f"Wrote participant features: {participant_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--max-persons", type=int, default=None)
    parser.add_argument("--progress-every", type=int, default=250)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--skip-segmentation", action="store_true")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
