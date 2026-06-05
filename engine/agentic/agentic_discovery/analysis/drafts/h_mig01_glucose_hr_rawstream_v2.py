"""Raw-stream H-MIG01 glucose-HR coupling analysis.

This draft analysis recomputes participant-level glucose and heart-rate coupling
directly from CGM and wearable JSON streams for PLAN-20260515-0006. It is meant
to be proposed through the quarantined execution-proposal gate before promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


GROUP_ORDER = [
    "healthy",
    "pre_diabetes_lifestyle_controlled",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled",
    "insulin_dependent",
]
GROUP_LABELS = {
    "healthy": "healthy",
    "pre_diabetes_lifestyle_controlled": "pre_diabetes",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": "oral_medication",
    "insulin_dependent": "insulin_dependent",
}
SEVERITY_MAP = {group: idx for idx, group in enumerate(GROUP_ORDER)}
PRIMARY_FEATURE = "glucose_hr_awake_pearson_r_resid_glucose_hr_mean"
FREQ = "5min"
STEP_MINUTES = 5
ALIGN_TOLERANCE = pd.Timedelta(minutes=10)
MIN_CORR_POINTS = 24
HASH_CHUNK_BYTES = 1024 * 1024


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--participant-index", type=Path, required=True)
    parser.add_argument("--feature-matrix", type=Path, required=True)
    parser.add_argument("--medication-search-root", type=Path, default=None)
    parser.add_argument("--candidate-id", default="CAND-LEGACY-H-MIG01")
    parser.add_argument("--plan-id", default="PLAN-20260515-0006")
    parser.add_argument("--min-aligned-hours", type=float, default=120.0)
    parser.add_argument("--surrogate-shifts", type=int, nargs="+", default=[30, 60, 120, 1440])
    parser.add_argument("--participant-limit", type=int, default=0)
    parser.add_argument("--hash-inputs", action="store_true")
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--group-csv", type=Path, required=True)
    parser.add_argument("--model-csv", type=Path, required=True)
    parser.add_argument("--pairwise-csv", type=Path, required=True)
    parser.add_argument("--surrogate-csv", type=Path, required=True)
    parser.add_argument("--participant-parquet", type=Path, required=True)
    args = parser.parse_args()

    participant = read_indexed_parquet(args.participant_index)
    feature_matrix = read_indexed_parquet(args.feature_matrix)
    person_ids = eligible_person_ids(participant, args.participant_limit)
    if not person_ids:
        raise ValueError("No eligible participants found in participant index")

    rows = []
    for person_id in person_ids:
        rows.append(
            compute_participant_features(
                person_id=person_id,
                data_root=args.data_root,
                min_aligned_hours=args.min_aligned_hours,
                surrogate_shifts=args.surrogate_shifts,
                hash_inputs=args.hash_inputs,
            )
        )

    participant_features = pd.DataFrame(rows).set_index("person_id")
    analysis = attach_metadata(participant_features, participant, feature_matrix)
    analysis = add_participant_level_residual_features(analysis, args.surrogate_shifts)
    real_features = [
        PRIMARY_FEATURE,
        "glucose_hr_awake_pearson_r",
        "glucose_hr_sleep_pearson_r",
        "glucose_hr_partial_r_activity_sleep",
        "sleep_minus_awake_pearson_r",
    ]
    surrogate_features = [
        f"glucose_hr_awake_shift_{shift}min_pearson_r_resid_glucose_hr_mean"
        for shift in args.surrogate_shifts
    ]

    group_rows = group_summary(analysis, real_features)
    model_rows = model_summary(analysis, real_features)
    pairwise_rows = pairwise_summary(analysis, real_features)
    surrogate_rows = surrogate_summary(analysis, args.surrogate_shifts, primary_feature=PRIMARY_FEATURE)
    medication = search_medication_fields(
        root=args.medication_search_root or args.data_root / "clinical_data",
        participant_index=args.participant_index,
        feature_matrix=args.feature_matrix,
    )
    primary_metrics = primary_metric_payload(
        analysis=analysis,
        feature=PRIMARY_FEATURE,
        model_rows=model_rows,
        pairwise_rows=pairwise_rows,
        surrogate_rows=surrogate_rows,
    )
    refutation = refutation_rule(analysis, PRIMARY_FEATURE, surrogate_rows)

    for output in [
        args.output_json,
        args.group_csv,
        args.model_csv,
        args.pairwise_csv,
        args.surrogate_csv,
        args.participant_parquet,
    ]:
        output.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(group_rows).to_csv(args.group_csv, index=False)
    pd.DataFrame(model_rows).to_csv(args.model_csv, index=False)
    pd.DataFrame(pairwise_rows).to_csv(args.pairwise_csv, index=False)
    pd.DataFrame(surrogate_rows).to_csv(args.surrogate_csv, index=False)
    analysis.reset_index().rename(columns={"index": "person_id"}).to_parquet(args.participant_parquet, index=False)

    payload = {
        "analysis_id": "h_mig01_glucose_hr_rawstream_v2",
        "created_at": now_utc(),
        "candidate_id": args.candidate_id,
        "plan_id": args.plan_id,
        "group_order": GROUP_ORDER,
        "min_aligned_hours": args.min_aligned_hours,
        "alignment": {
            "frequency": FREQ,
            "tolerance_minutes": int(ALIGN_TOLERANCE.total_seconds() / 60),
            "valid_pair_hours_definition": "rows with finite glucose and HR times 5 minutes",
        },
        "inputs": {
            "data_root": str(args.data_root),
            "participant_index": str(args.participant_index),
            "feature_matrix": str(args.feature_matrix),
            "medication_search_root": str(args.medication_search_root or args.data_root / "clinical_data"),
        },
        "input_provenance": [
            file_provenance(args.participant_index, hash_inputs=True),
            file_provenance(args.feature_matrix, hash_inputs=True),
        ],
        "outputs": {
            "summary_json": str(args.output_json),
            "group_csv": str(args.group_csv),
            "model_csv": str(args.model_csv),
            "pairwise_csv": str(args.pairwise_csv),
            "surrogate_csv": str(args.surrogate_csv),
            "participant_parquet": str(args.participant_parquet),
        },
        "participant_counts": participant_counts(analysis),
        "missingness_audit": missingness_audit(analysis),
        "medication_field_search": medication,
        "features": {
            "primary_feature": PRIMARY_FEATURE,
            "real_features": real_features,
            "surrogate_features": surrogate_features,
        },
        "claim_scope": {
            "status": "probe_valid_only_until_medication_exposure_data_are_available",
            "reason": "AI-READI clinical_data search does not expose drug_exposure or HR-active medication fields; this run may test whether a raw-stream signal survives negative controls, but cannot by itself support a causal or treatment-independent diabetes-severity claim.",
        },
        "pre_registered_refutation_rule": refutation,
        "primary_metrics": primary_metrics,
        "mechanical_checks": {
            "raw_streams_loaded": bool((analysis["status"] == "analyzed").any()),
            "train_test_split_used": False,
            "primary_metric_level_residualized_for_glucose_and_hr_mean": PRIMARY_FEATURE in analysis.columns,
            "min_aligned_hours_filter_applied": True,
            "pre_dropna_missingness_audit_recorded": True,
            "twenty_four_hour_surrogate_recorded": 1440 in args.surrogate_shifts,
            "time_shift_surrogates_recorded": len(surrogate_features) == len(args.surrogate_shifts),
            "pairwise_all_six_group_pairs_recorded": has_all_six_pairwise_rows(pairwise_rows),
            "pairwise_fdr_bh_recorded": all("p_fdr_bh" in row for row in pairwise_rows),
            "sleep_awake_contrast_recorded": "sleep_minus_awake_pearson_r" in analysis.columns,
            "medication_search_recorded": True,
            "participant_raw_file_provenance_recorded": True,
            "sha256_for_raw_streams": bool(args.hash_inputs),
        },
        "limitations": [
            "Cross-sectional association only; this does not infer causal disease progression.",
            "Medication confounding is audited through available field/file search; no drug-exposure table is assumed if it is absent.",
            "Sleep labels come from wearable sleep intervals when present; participants without sleep intervals are marked as missing sleep labels rather than imputed.",
            "Circular shifts are negative controls, not causal proof; the 1440-minute shift is included to weaken shared diurnal-envelope artifacts.",
            "Jonckheere-Terpstra U is reported with a normal approximation and a tie-aware Kendall tau-b trend p-value.",
        ],
    }
    args.output_json.write_text(json.dumps(clean_json(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(clean_json({"participant_counts": payload["participant_counts"], "primary_metrics": primary_metrics}), indent=2))


def read_indexed_parquet(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if "person_id" in frame.columns:
        frame = frame.set_index("person_id")
    frame.index = frame.index.astype(str)
    return frame


def eligible_person_ids(participant: pd.DataFrame, participant_limit: int) -> list[str]:
    if "study_group" not in participant.columns:
        raise KeyError("participant index must contain study_group")
    mask = participant["study_group"].isin(GROUP_ORDER)
    for availability_col in ["wearable_blood_glucose", "wearable_activity_monitor"]:
        if availability_col in participant.columns:
            mask = mask & participant[availability_col].fillna(False).astype(bool)
    ids = participant.loc[mask].index.astype(str).tolist()
    if participant_limit and participant_limit > 0:
        return ids[:participant_limit]
    return ids


def compute_participant_features(
    person_id: str,
    data_root: Path,
    min_aligned_hours: float,
    surrogate_shifts: list[int],
    hash_inputs: bool,
) -> dict[str, Any]:
    paths = raw_paths(data_root, person_id)
    row: dict[str, Any] = {
        "person_id": person_id,
        "status": "not_started",
        "error": "",
        "min_aligned_hours": min_aligned_hours,
    }
    for key, path in paths.items():
        row[f"{key}_path"] = str(path)
        provenance = file_provenance(path, hash_inputs=hash_inputs)
        for prov_key, prov_value in provenance.items():
            row[f"{key}_{prov_key}"] = prov_value

    try:
        cgm = load_cgm(paths["cgm"])
        hr = load_hr(paths["hr"])
        if cgm.empty or hr.empty:
            row["status"] = "missing_cgm_or_hr"
            row["cgm_records"] = int(len(cgm))
            row["hr_records"] = int(len(hr))
            return row

        aligned = align_cgm_hr(cgm, hr)
        if aligned.empty:
            row["status"] = "no_cgm_hr_overlap"
            row["cgm_records"] = int(len(cgm))
            row["hr_records"] = int(len(hr))
            return row

        aligned["activity_steps"] = activity_on_grid(paths["activity"], aligned.index)
        sleep_info = sleep_on_grid(paths["sleep"], aligned.index)
        aligned["asleep"] = sleep_info["asleep"]
        aligned["has_sleep_label"] = sleep_info["has_sleep_label"]

        valid_pair = aligned[["glucose_mg_dl", "hr_bpm"]].notna().all(axis=1)
        aligned_hours = float(valid_pair.sum() * STEP_MINUTES / 60.0)
        row.update(pre_dropna_counts(aligned, valid_pair))
        row.update(
            {
                "status": "excluded_min_aligned_hours" if aligned_hours < min_aligned_hours else "analyzed",
                "cgm_records": int(len(cgm)),
                "hr_records": int(len(hr)),
                "grid_points": int(len(aligned)),
                "aligned_hours": aligned_hours,
                "sleep_interval_count": int(sleep_info["sleep_interval_count"]),
                "sleep_label_source": sleep_info["source"],
                "activity_source": "raw_activity_json" if paths["activity"].exists() else "missing_activity_zero_fill",
            }
        )
        if aligned_hours < min_aligned_hours:
            return row

        row.update(signal_features(aligned, valid_pair, surrogate_shifts))
        return row
    except Exception as exc:
        row["status"] = "error"
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row


def raw_paths(data_root: Path, person_id: str) -> dict[str, Path]:
    return {
        "cgm": data_root
        / "wearable_blood_glucose"
        / "continuous_glucose_monitoring"
        / "dexcom_g6"
        / person_id
        / f"{person_id}_DEX.json",
        "hr": data_root
        / "wearable_activity_monitor"
        / "heart_rate"
        / "garmin_vivosmart5"
        / person_id
        / f"{person_id}_heartrate.json",
        "sleep": data_root
        / "wearable_activity_monitor"
        / "sleep"
        / "garmin_vivosmart5"
        / person_id
        / f"{person_id}_sleep.json",
        "activity": data_root
        / "wearable_activity_monitor"
        / "physical_activity"
        / "garmin_vivosmart5"
        / person_id
        / f"{person_id}_activity.json",
    }


def file_provenance(path: Path, hash_inputs: bool) -> dict[str, Any]:
    out: dict[str, Any] = {"exists": bool(path.exists())}
    if not path.exists():
        return out
    stat = path.stat()
    out.update(
        {
            "size_bytes": int(stat.st_size),
            "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        }
    )
    if hash_inputs:
        out["sha256"] = sha256_file(path)
    return out


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_cgm(path: Path) -> pd.DataFrame:
    payload = load_json(path)
    rows = []
    for item in payload.get("body", {}).get("cgm", []):
        time_value = (
            item.get("effective_time_frame", {})
            .get("time_interval", {})
            .get("start_date_time")
        )
        glucose_value = item.get("blood_glucose", {}).get("value")
        rows.append({"timestamp": parse_time(time_value), "glucose_mg_dl": numeric_or_nan(glucose_value)})
    return clean_timeseries(rows, "glucose_mg_dl")


def load_hr(path: Path) -> pd.DataFrame:
    payload = load_json(path)
    rows = []
    for item in payload.get("body", {}).get("heart_rate", []):
        time_value = item.get("effective_time_frame", {}).get("date_time")
        hr_value = item.get("heart_rate", {}).get("value")
        value = numeric_or_nan(hr_value)
        if np.isfinite(value) and value > 0:
            rows.append({"timestamp": parse_time(time_value), "hr_bpm": value})
    return clean_timeseries(rows, "hr_bpm")


def clean_timeseries(rows: list[dict[str, Any]], value_col: str) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=[value_col], index=pd.DatetimeIndex([], tz="UTC", name="timestamp"))
    frame = pd.DataFrame(rows)
    frame = frame.dropna(subset=["timestamp", value_col]).copy()
    if frame.empty:
        return pd.DataFrame(columns=[value_col], index=pd.DatetimeIndex([], tz="UTC", name="timestamp"))
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame[value_col] = pd.to_numeric(frame[value_col], errors="coerce")
    frame = frame.dropna(subset=[value_col]).sort_values("timestamp")
    frame = frame.groupby("timestamp", as_index=True)[value_col].mean().to_frame()
    frame.index.name = "timestamp"
    return frame


def parse_time(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None:
        return pd.NaT
    return pd.to_datetime(value, utc=True, errors="coerce")


def numeric_or_nan(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def align_cgm_hr(cgm: pd.DataFrame, hr: pd.DataFrame) -> pd.DataFrame:
    start = max(cgm.index.min(), hr.index.min()).ceil(FREQ)
    end = min(cgm.index.max(), hr.index.max()).floor(FREQ)
    if pd.isna(start) or pd.isna(end) or start > end:
        return pd.DataFrame(columns=["glucose_mg_dl", "hr_bpm"])
    grid = pd.date_range(start=start, end=end, freq=FREQ)
    out = pd.DataFrame(index=grid)
    out["glucose_mg_dl"] = cgm["glucose_mg_dl"].reindex(grid, method="nearest", tolerance=ALIGN_TOLERANCE)
    out["hr_bpm"] = hr["hr_bpm"].reindex(grid, method="nearest", tolerance=ALIGN_TOLERANCE)
    out.index.name = "timestamp"
    return out


def activity_on_grid(path: Path, grid: pd.DatetimeIndex) -> pd.Series:
    if not path.exists() or len(grid) == 0:
        return pd.Series(0.0, index=grid)
    payload = load_json(path)
    times = []
    values = []
    for item in payload.get("body", {}).get("activity", []):
        time_value = (
            item.get("effective_time_frame", {})
            .get("time_interval", {})
            .get("start_date_time")
        )
        value = (
            item.get("base_movement_quantity", {}).get("value")
            if isinstance(item.get("base_movement_quantity"), dict)
            else item.get("base_movement_quantity")
        )
        timestamp = parse_time(time_value)
        numeric_value = numeric_or_nan(value)
        if pd.notna(timestamp) and np.isfinite(numeric_value):
            times.append(timestamp)
            values.append(max(numeric_value, 0.0))
    if not times:
        return pd.Series(0.0, index=grid)
    series = pd.Series(values, index=pd.DatetimeIndex(times)).sort_index()
    series = series.groupby(series.index).sum()
    resampled = series.resample(FREQ).sum()
    return resampled.reindex(grid, fill_value=0.0).astype(float)


def sleep_on_grid(path: Path, grid: pd.DatetimeIndex) -> dict[str, Any]:
    asleep = pd.Series(False, index=grid)
    has_label = pd.Series(False, index=grid)
    if not path.exists() or len(grid) == 0:
        return {
            "asleep": asleep.astype(float),
            "has_sleep_label": has_label.astype(float),
            "sleep_interval_count": 0,
            "source": "missing_sleep_json",
        }

    payload = load_json(path)
    interval_count = 0
    for item in payload.get("body", {}).get("sleep", []):
        interval = item.get("effective_time_frame", {}).get("time_interval", {})
        start = parse_time(interval.get("start_date_time"))
        end = parse_time(interval.get("end_date_time"))
        if pd.isna(start) or pd.isna(end) or start >= end:
            continue
        state = sleep_state(item)
        is_asleep = state != "awake"
        mask = (grid >= start) & (grid < end)
        if mask.any():
            has_label.loc[mask] = True
            asleep.loc[mask] = bool(is_asleep)
            interval_count += 1
    source = "raw_sleep_json" if interval_count else "sleep_json_without_grid_overlap"
    return {
        "asleep": asleep.astype(float),
        "has_sleep_label": has_label.astype(float),
        "sleep_interval_count": interval_count,
        "source": source,
    }


def sleep_state(item: dict[str, Any]) -> str:
    for key in ["sleep_stage_state", "sleep_stage", "state"]:
        value = item.get(key)
        if value is not None:
            return str(value).strip().lower()
    value = item.get("value")
    if isinstance(value, dict):
        for key in ["text", "value", "name"]:
            if value.get(key) is not None:
                return str(value.get(key)).strip().lower()
    if value is not None:
        return str(value).strip().lower()
    return "unknown"


def pre_dropna_counts(aligned: pd.DataFrame, valid_pair: pd.Series) -> dict[str, Any]:
    awake_mask = aligned["has_sleep_label"].eq(1.0) & aligned["asleep"].eq(0.0)
    sleep_mask = aligned["has_sleep_label"].eq(1.0) & aligned["asleep"].eq(1.0)
    return {
        "n_grid_points_pre_dropna": int(len(aligned)),
        "n_missing_glucose_pre_dropna": int(aligned["glucose_mg_dl"].isna().sum()),
        "n_missing_hr_pre_dropna": int(aligned["hr_bpm"].isna().sum()),
        "n_valid_glucose_hr_pairs": int(valid_pair.sum()),
        "n_awake_labeled_points_pre_dropna": int(awake_mask.sum()),
        "n_sleep_labeled_points_pre_dropna": int(sleep_mask.sum()),
        "n_valid_awake_pairs": int((valid_pair & awake_mask).sum()),
        "n_valid_sleep_pairs": int((valid_pair & sleep_mask).sum()),
        "n_unlabeled_sleep_points": int(aligned["has_sleep_label"].eq(0.0).sum()),
    }


def signal_features(aligned: pd.DataFrame, valid_pair: pd.Series, surrogate_shifts: list[int]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    awake_mask = aligned["has_sleep_label"].eq(1.0) & aligned["asleep"].eq(0.0)
    sleep_mask = aligned["has_sleep_label"].eq(1.0) & aligned["asleep"].eq(1.0)
    row["glucose_mean"] = safe_float(aligned.loc[valid_pair, "glucose_mg_dl"].mean())
    row["hr_mean"] = safe_float(aligned.loc[valid_pair, "hr_bpm"].mean())
    row["activity_total_steps_proxy"] = safe_float(aligned["activity_steps"].sum())
    row["sleep_fraction"] = safe_float(aligned.loc[aligned["has_sleep_label"].eq(1.0), "asleep"].mean())
    row["glucose_hr_all_pearson_r"] = corr(aligned.loc[valid_pair, "glucose_mg_dl"], aligned.loc[valid_pair, "hr_bpm"], "pearson")
    row["glucose_hr_all_spearman_r"] = corr(aligned.loc[valid_pair, "glucose_mg_dl"], aligned.loc[valid_pair, "hr_bpm"], "spearman")
    row["glucose_hr_awake_pearson_r"] = corr(
        aligned.loc[valid_pair & awake_mask, "glucose_mg_dl"],
        aligned.loc[valid_pair & awake_mask, "hr_bpm"],
        "pearson",
    )
    row["glucose_hr_awake_spearman_r"] = corr(
        aligned.loc[valid_pair & awake_mask, "glucose_mg_dl"],
        aligned.loc[valid_pair & awake_mask, "hr_bpm"],
        "spearman",
    )
    row["glucose_hr_sleep_pearson_r"] = corr(
        aligned.loc[valid_pair & sleep_mask, "glucose_mg_dl"],
        aligned.loc[valid_pair & sleep_mask, "hr_bpm"],
        "pearson",
    )
    row["glucose_hr_sleep_spearman_r"] = corr(
        aligned.loc[valid_pair & sleep_mask, "glucose_mg_dl"],
        aligned.loc[valid_pair & sleep_mask, "hr_bpm"],
        "spearman",
    )
    row["glucose_hr_partial_r_activity_sleep"] = partial_corr(
        aligned.loc[valid_pair, ["glucose_mg_dl", "hr_bpm", "activity_steps", "asleep"]],
        x_col="glucose_mg_dl",
        y_col="hr_bpm",
        covariates=["activity_steps", "asleep"],
    )
    row["sleep_minus_awake_pearson_r"] = safe_diff(
        row["glucose_hr_sleep_pearson_r"],
        row["glucose_hr_awake_pearson_r"],
    )
    for shift_minutes in surrogate_shifts:
        row[f"glucose_hr_awake_shift_{shift_minutes}min_pearson_r"] = shifted_awake_corr(
            aligned=aligned,
            valid_pair=valid_pair,
            awake_mask=awake_mask,
            shift_minutes=shift_minutes,
        )
    return row


def corr(x: pd.Series, y: pd.Series, method: str) -> float | None:
    sub = pd.concat([pd.to_numeric(x, errors="coerce"), pd.to_numeric(y, errors="coerce")], axis=1).dropna()
    if len(sub) < MIN_CORR_POINTS:
        return None
    left = sub.iloc[:, 0].to_numpy(dtype=float)
    right = sub.iloc[:, 1].to_numpy(dtype=float)
    if np.nanstd(left) <= 0 or np.nanstd(right) <= 0:
        return None
    if method == "spearman":
        result = stats.spearmanr(left, right)
        return safe_float(result.statistic)
    result = stats.pearsonr(left, right)
    return safe_float(result.statistic)


def partial_corr(frame: pd.DataFrame, x_col: str, y_col: str, covariates: list[str]) -> float | None:
    sub = frame[[x_col, y_col] + covariates].replace([np.inf, -np.inf], np.nan).dropna()
    if len(sub) < max(30, len(covariates) + 5):
        return None
    x_resid = residualize(sub[x_col].to_numpy(dtype=float), sub[covariates])
    y_resid = residualize(sub[y_col].to_numpy(dtype=float), sub[covariates])
    if np.nanstd(x_resid) <= 0 or np.nanstd(y_resid) <= 0:
        return None
    return safe_float(stats.pearsonr(x_resid, y_resid).statistic)


def residualize(y: np.ndarray, covariates: pd.DataFrame) -> np.ndarray:
    cov = covariates.copy()
    if "activity_steps" in cov.columns:
        cov["activity_steps"] = np.log1p(pd.to_numeric(cov["activity_steps"], errors="coerce").fillna(0.0))
    x = cov.astype(float).to_numpy()
    x = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.pinv(x) @ y
    return y - x @ beta


def shifted_awake_corr(
    aligned: pd.DataFrame,
    valid_pair: pd.Series,
    awake_mask: pd.Series,
    shift_minutes: int,
) -> float | None:
    steps = int(round(shift_minutes / STEP_MINUTES))
    if steps == 0 or aligned.empty:
        return None
    shifted = pd.Series(np.roll(aligned["glucose_mg_dl"].to_numpy(dtype=float), steps), index=aligned.index)
    shifted_valid = shifted.notna() & aligned["hr_bpm"].notna()
    return corr(shifted.loc[valid_pair & awake_mask & shifted_valid], aligned.loc[valid_pair & awake_mask & shifted_valid, "hr_bpm"], "pearson")


def safe_diff(left: Any, right: Any) -> float | None:
    left_value = safe_float(left)
    right_value = safe_float(right)
    if left_value is None or right_value is None:
        return None
    return left_value - right_value


def attach_metadata(
    participant_features: pd.DataFrame,
    participant: pd.DataFrame,
    feature_matrix: pd.DataFrame,
) -> pd.DataFrame:
    keep_participant = [
        col
        for col in [
            "clinical_site",
            "study_group",
            "age",
            "study_visit_date",
            "recommended_split",
            "wearable_activity_monitor",
            "wearable_blood_glucose",
        ]
        if col in participant.columns
    ]
    keep_feature = [
        col
        for col in [
            "hba1c",
            "bmi",
            "glucose",
            "heart_rate",
            "sbp",
            "dbp",
            "has_hypertension",
            "has_hypotension",
            "has_mi",
            "has_other_cardiac",
        ]
        if col in feature_matrix.columns and col not in participant_features.columns
    ]
    out = participant_features.join(participant[keep_participant], how="left")
    out = out.join(feature_matrix[keep_feature], how="left")
    out["severity"] = out["study_group"].map(SEVERITY_MAP)
    return out.replace([np.inf, -np.inf], np.nan)


def add_participant_level_residual_features(df: pd.DataFrame, surrogate_shifts: list[int]) -> pd.DataFrame:
    out = df.copy()
    out[PRIMARY_FEATURE] = residualize_participant_feature(
        out,
        feature="glucose_hr_awake_pearson_r",
        covariates=["glucose_mean", "hr_mean"],
    )
    for shift in surrogate_shifts:
        feature = f"glucose_hr_awake_shift_{shift}min_pearson_r"
        out[f"{feature}_resid_glucose_hr_mean"] = residualize_participant_feature(
            out,
            feature=feature,
            covariates=["glucose_mean", "hr_mean"],
        )
    return out


def residualize_participant_feature(df: pd.DataFrame, feature: str, covariates: list[str]) -> pd.Series:
    residual = pd.Series(np.nan, index=df.index, dtype=float)
    columns = [feature] + [covariate for covariate in covariates if covariate in df.columns]
    if len(columns) < 2 or feature not in df.columns:
        return residual
    sub = df.loc[df["status"] == "analyzed", columns].replace([np.inf, -np.inf], np.nan).dropna()
    if len(sub) < max(30, len(columns) + 5):
        return residual
    y = sub[feature].astype(float).to_numpy()
    x = sub[[column for column in columns if column != feature]].astype(float).to_numpy()
    x = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.pinv(x) @ y
    residual.loc[sub.index] = y - x @ beta
    return residual


def group_summary(df: pd.DataFrame, features: list[str]) -> list[dict[str, Any]]:
    rows = []
    for feature in features:
        for group in GROUP_ORDER:
            group_df = df[df["study_group"] == group]
            analyzed = group_df[group_df["status"] == "analyzed"]
            values = pd.to_numeric(analyzed[feature], errors="coerce").dropna() if feature in analyzed.columns else pd.Series(dtype=float)
            rows.append(
                {
                    "feature": feature,
                    "study_group": group,
                    "label": GROUP_LABELS[group],
                    "n_eligible": int(len(group_df)),
                    "n_analyzed_status": int((group_df["status"] == "analyzed").sum()),
                    "n_feature_nonmissing": int(len(values)),
                    "n_excluded_min_aligned_hours": int((group_df["status"] == "excluded_min_aligned_hours").sum()),
                    "n_missing_cgm_or_hr": int((group_df["status"] == "missing_cgm_or_hr").sum()),
                    "mean": safe_float(values.mean()),
                    "median": safe_float(values.median()),
                    "sd": safe_float(values.std()),
                    "q25": safe_float(values.quantile(0.25)),
                    "q75": safe_float(values.quantile(0.75)),
                }
            )
    return rows


def model_summary(df: pd.DataFrame, features: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for feature in features:
        rows.extend(distribution_tests(df, feature))
        rows.extend(ols_sensitivity_rows(df, feature))
    return rows


def distribution_tests(df: pd.DataFrame, feature: str) -> list[dict[str, Any]]:
    groups = values_by_group(df, feature)
    rows: list[dict[str, Any]] = []
    rows.append({"feature": feature, "test": "kruskal_wallis", **kruskal(groups)})
    rows.append({"feature": feature, "test": "ordered_trend", **ordered_trend(groups)})
    rows.append(
        {
            "feature": feature,
            "test": "endpoint_effect",
            "contrast": "insulin_dependent_minus_healthy",
            "cohens_d": safe_float(cohens_d(groups[0], groups[-1])),
            "n_left": int(len(groups[0])),
            "n_right": int(len(groups[-1])),
        }
    )
    return rows


def values_by_group(df: pd.DataFrame, feature: str) -> list[pd.Series]:
    if feature not in df.columns:
        return [pd.Series(dtype=float) for _ in GROUP_ORDER]
    analyzed = df[df["status"] == "analyzed"].copy()
    return [
        pd.to_numeric(analyzed.loc[analyzed["study_group"] == group, feature], errors="coerce").dropna()
        for group in GROUP_ORDER
    ]


def kruskal(groups: list[pd.Series]) -> dict[str, Any]:
    nonempty = [group for group in groups if len(group) >= 2]
    if len(nonempty) < 2:
        return {"n": int(sum(len(group) for group in groups)), "statistic": None, "p_value": None}
    try:
        result = stats.kruskal(*nonempty)
    except ValueError as exc:
        return {"n": int(sum(len(group) for group in groups)), "statistic": None, "p_value": None, "error": str(exc)}
    return {
        "n": int(sum(len(group) for group in groups)),
        "statistic": safe_float(result.statistic),
        "p_value": safe_float(result.pvalue),
    }


def ordered_trend(groups: list[pd.Series]) -> dict[str, Any]:
    jt = jonckheere_terpstra(groups)
    severity = []
    values = []
    for idx, group in enumerate(groups):
        severity.extend([idx] * len(group))
        values.extend(group.astype(float).tolist())
    if len(values) < 3 or len(set(severity)) < 2:
        tau = None
        tau_p = None
        spearman_rho = None
        spearman_p = None
    else:
        tau_result = stats.kendalltau(severity, values)
        spearman_result = stats.spearmanr(severity, values)
        tau = safe_float(tau_result.statistic)
        tau_p = safe_float(tau_result.pvalue)
        spearman_rho = safe_float(spearman_result.statistic)
        spearman_p = safe_float(spearman_result.pvalue)
    return {
        "jonckheere_terpstra_u": safe_float(jt["u"]),
        "jt_z_normal_approx": safe_float(jt["z"]),
        "p_jt_positive_normal_approx": safe_float(jt["p_positive"]),
        "kendall_tau_b_tie_aware": tau,
        "p_kendall_tau_b_tie_aware": tau_p,
        "spearman_rho": spearman_rho,
        "p_spearman": spearman_p,
        "n": int(sum(len(group) for group in groups)),
    }


def jonckheere_terpstra(groups: list[pd.Series]) -> dict[str, float]:
    arrays = [pd.to_numeric(group, errors="coerce").dropna().to_numpy(dtype=float) for group in groups]
    u = 0.0
    for left_index, left in enumerate(arrays[:-1]):
        for right in arrays[left_index + 1 :]:
            if len(left) == 0 or len(right) == 0:
                continue
            comp = right[:, None] - left[None, :]
            u += float((comp > 0).sum() + 0.5 * (comp == 0).sum())
    ns = np.array([len(arr) for arr in arrays], dtype=float)
    n = float(ns.sum())
    mean = (n * n - np.sum(ns * ns)) / 4.0
    var = (n * n * (2 * n + 3) - np.sum(ns * ns * (2 * ns + 3))) / 72.0
    z = (u - mean) / math.sqrt(var) if var > 0 else float("nan")
    return {"u": u, "z": z, "p_positive": float(stats.norm.sf(z)) if np.isfinite(z) else float("nan")}


def ols_sensitivity_rows(df: pd.DataFrame, feature: str) -> list[dict[str, Any]]:
    return [
        ols_severity(df, feature, covariates=[], model="ols_unadjusted"),
        ols_severity(df, feature, covariates=["age", "clinical_site"], model="ols_age_site"),
        ols_severity(
            df,
            feature,
            covariates=[
                "age",
                "clinical_site",
                "hba1c",
                "bmi",
                "glucose_mean",
                "hr_mean",
                "activity_total_steps_proxy",
                "sleep_fraction",
            ],
            model="ols_full_available_covariates",
        ),
    ]


def ols_severity(df: pd.DataFrame, feature: str, covariates: list[str], model: str) -> dict[str, Any]:
    columns = [feature, "severity"] + [col for col in covariates if col in df.columns]
    sub = df.loc[df["status"] == "analyzed", columns].dropna().copy()
    base = {"feature": feature, "test": "ols_severity", "model": model, "n": int(len(sub))}
    if len(sub) < max(50, len(columns) + 5):
        return {**base, "error": "too_few_rows_after_covariate_dropna"}

    x_parts = [sub[["severity"]].astype(float)]
    used_covariates = []
    for covariate in covariates:
        if covariate not in sub.columns:
            continue
        if covariate == "clinical_site":
            dummies = pd.get_dummies(sub[covariate].astype(str), prefix=covariate, drop_first=True)
            if not dummies.empty:
                x_parts.append(dummies.astype(float))
                used_covariates.append(covariate)
            continue
        x_parts.append(sub[[covariate]].astype(float))
        used_covariates.append(covariate)
    x = pd.concat(x_parts, axis=1)
    x.insert(0, "intercept", 1.0)
    y = sub[feature].astype(float).to_numpy()
    x_mat = x.to_numpy(dtype=float)
    beta = np.linalg.pinv(x_mat) @ y
    fitted = x_mat @ beta
    resid = y - fitted
    rank = int(np.linalg.matrix_rank(x_mat))
    dof = max(len(y) - rank, 1)
    sigma2 = float(np.sum(resid**2) / dof)
    cov_beta = sigma2 * np.linalg.pinv(x_mat.T @ x_mat)
    se = np.sqrt(np.clip(np.diag(cov_beta), 0, np.inf))
    severity_idx = list(x.columns).index("severity")
    severity_coef = beta[severity_idx]
    severity_se = se[severity_idx]
    t_stat = severity_coef / severity_se if severity_se > 0 else np.nan
    p_value = 2 * stats.t.sf(abs(t_stat), dof) if np.isfinite(t_stat) else np.nan
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return {
        **base,
        "covariates": used_covariates,
        "severity_coef": safe_float(severity_coef),
        "severity_se": safe_float(severity_se),
        "severity_t": safe_float(t_stat),
        "p_severity": safe_float(p_value),
        "r2": safe_float(r2),
    }


def pairwise_summary(df: pd.DataFrame, features: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for feature in features:
        groups = values_by_group(df, feature)
        feature_rows = []
        p_values = []
        for left_idx, left_group in enumerate(GROUP_ORDER[:-1]):
            for right_idx in range(left_idx + 1, len(GROUP_ORDER)):
                right_group = GROUP_ORDER[right_idx]
                left = groups[left_idx]
                right = groups[right_idx]
                if len(left) < 2 or len(right) < 2:
                    p_value = None
                    u_stat = None
                else:
                    result = stats.mannwhitneyu(left, right, alternative="two-sided")
                    p_value = safe_float(result.pvalue)
                    u_stat = safe_float(result.statistic)
                p_values.append(p_value)
                feature_rows.append(
                    {
                        "feature": feature,
                        "left_group": left_group,
                        "right_group": right_group,
                        "left_label": GROUP_LABELS[left_group],
                        "right_label": GROUP_LABELS[right_group],
                        "n_left": int(len(left)),
                        "n_right": int(len(right)),
                        "mannwhitney_u": u_stat,
                        "p_raw": p_value,
                        "cohens_d_right_minus_left": safe_float(cohens_d(left, right)),
                    }
                )
        adjusted = fdr_bh(p_values)
        for row, p_adj in zip(feature_rows, adjusted):
            row["p_fdr_bh"] = p_adj
            rows.append(row)
    return rows


def surrogate_summary(df: pd.DataFrame, shifts: list[int], primary_feature: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    real_groups = values_by_group(df, primary_feature)
    real_endpoint_d = cohens_d(real_groups[0], real_groups[-1])
    for shift in shifts:
        feature = f"glucose_hr_awake_shift_{shift}min_pearson_r_resid_glucose_hr_mean"
        groups = values_by_group(df, feature)
        kw = kruskal(groups)
        trend = ordered_trend(groups)
        endpoint_d = cohens_d(groups[0], groups[-1])
        rows.append(
            {
                "feature": feature,
                "shift_minutes": int(shift),
                "n": kw.get("n"),
                "kruskal_h": kw.get("statistic"),
                "p_kruskal": kw.get("p_value"),
                "kendall_tau_b_tie_aware": trend.get("kendall_tau_b_tie_aware"),
                "p_kendall_tau_b_tie_aware": trend.get("p_kendall_tau_b_tie_aware"),
                "healthy_vs_insulin_d": safe_float(endpoint_d),
                "real_healthy_vs_insulin_d": safe_float(real_endpoint_d),
                "abs_d_ratio_real_over_surrogate": safe_ratio(abs_value(real_endpoint_d), abs_value(endpoint_d)),
            }
        )
    return rows


def fdr_bh(p_values: list[float | None]) -> list[float | None]:
    out: list[float | None] = [None for _ in p_values]
    valid = [(idx, float(p)) for idx, p in enumerate(p_values) if p is not None and np.isfinite(float(p))]
    if not valid:
        return out
    valid_sorted = sorted(valid, key=lambda item: item[1])
    m = len(valid_sorted)
    adjusted = [0.0 for _ in valid_sorted]
    running = 1.0
    for reverse_rank, (idx, p_value) in enumerate(reversed(valid_sorted), start=1):
        rank = m - reverse_rank + 1
        running = min(running, p_value * m / rank)
        adjusted[rank - 1] = running
    for (idx, _), value in zip(valid_sorted, adjusted):
        out[idx] = safe_float(min(value, 1.0))
    return out


def cohens_d(left: pd.Series, right: pd.Series) -> float:
    left = pd.to_numeric(left, errors="coerce").dropna()
    right = pd.to_numeric(right, errors="coerce").dropna()
    if len(left) < 3 or len(right) < 3:
        return float("nan")
    pooled = math.sqrt(((len(left) - 1) * left.var() + (len(right) - 1) * right.var()) / (len(left) + len(right) - 2))
    if pooled == 0 or not np.isfinite(pooled):
        return float("nan")
    return float((right.mean() - left.mean()) / pooled)


def participant_counts(df: pd.DataFrame) -> dict[str, Any]:
    status_counts = df["status"].value_counts(dropna=False).to_dict()
    group_counts = {}
    for group in GROUP_ORDER:
        group_df = df[df["study_group"] == group]
        group_counts[group] = {
            "eligible": int(len(group_df)),
            "analyzed": int((group_df["status"] == "analyzed").sum()),
            "excluded_min_aligned_hours": int((group_df["status"] == "excluded_min_aligned_hours").sum()),
            "missing_cgm_or_hr": int((group_df["status"] == "missing_cgm_or_hr").sum()),
            "error": int((group_df["status"] == "error").sum()),
        }
    return {
        "eligible": int(len(df)),
        "analyzed": int((df["status"] == "analyzed").sum()),
        "status_counts": {str(key): int(value) for key, value in status_counts.items()},
        "by_group": group_counts,
    }


def missingness_audit(df: pd.DataFrame) -> dict[str, Any]:
    columns = [
        "n_grid_points_pre_dropna",
        "n_missing_glucose_pre_dropna",
        "n_missing_hr_pre_dropna",
        "n_valid_glucose_hr_pairs",
        "n_valid_awake_pairs",
        "n_valid_sleep_pairs",
        "n_unlabeled_sleep_points",
        "aligned_hours",
    ]
    out: dict[str, Any] = {}
    for group in GROUP_ORDER:
        sub = df[df["study_group"] == group]
        out[group] = {}
        for column in columns:
            if column in sub.columns:
                out[group][column] = safe_float(pd.to_numeric(sub[column], errors="coerce").mean())
    return out


def search_medication_fields(root: Path, participant_index: Path, feature_matrix: Path) -> dict[str, Any]:
    keywords = [
        "medication",
        "drug",
        "drug_exposure",
        "rx",
        "rxnorm",
        "prescription",
        "beta_blocker",
        "antihypertensive",
        "statin",
        "metformin",
        "glp1",
        "sglt",
    ]
    possible_confounder_keywords = ["insulin"]
    records = []
    matching_columns = []
    possible_confounder_columns = []
    for path in [participant_index, feature_matrix]:
        columns = read_columns(path)
        matches = [column for column in columns if keyword_match(column, keywords)]
        possible_matches = [column for column in columns if keyword_match(column, possible_confounder_keywords)]
        if matches:
            matching_columns.append({"path": str(path), "columns": matches})
        if possible_matches:
            possible_confounder_columns.append({"path": str(path), "columns": possible_matches})
    if root.exists():
        scanned = 0
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in [".csv", ".tsv", ".parquet"]:
                continue
            scanned += 1
            columns = read_columns(path)
            name_match = keyword_match(path.name, keywords)
            column_matches = [column for column in columns if keyword_match(column, keywords)]
            if name_match or column_matches:
                records.append(
                    {
                        "path": str(path),
                        "name_keyword_match": bool(name_match),
                        "matching_columns": column_matches,
                    }
                )
        scanned_files = scanned
    else:
        scanned_files = 0
    return {
        "root": str(root),
        "keywords": keywords,
        "scanned_files": int(scanned_files),
        "matching_explicit_medication_feature_tables": matching_columns,
        "matching_explicit_medication_clinical_files": records,
        "possible_biomarker_or_treatment_confounder_fields": possible_confounder_columns,
        "medication_field_found": bool(matching_columns or records),
        "interpretation": (
            "Medication-like fields or files were found and should be reviewed before causal interpretation."
            if matching_columns or records
            else "No explicit medication/drug-exposure field was found in the searched paths; possible treatment-relevant biomarkers are reported separately."
        ),
    }


def read_columns(path: Path) -> list[str]:
    try:
        if path.suffix.lower() == ".parquet":
            return list(pd.read_parquet(path).columns)
        separator = "\t" if path.suffix.lower() == ".tsv" else ","
        return list(pd.read_csv(path, sep=separator, nrows=0).columns)
    except Exception:
        return []


def keyword_match(text: str, keywords: list[str]) -> bool:
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in str(text))
    tokens = normalized.split()
    for keyword in keywords:
        parts = "".join(ch.lower() if ch.isalnum() else " " for ch in keyword).split()
        if parts and all(part in tokens for part in parts):
            return True
    return False


def primary_metric_payload(
    analysis: pd.DataFrame,
    feature: str,
    model_rows: list[dict[str, Any]],
    pairwise_rows: list[dict[str, Any]],
    surrogate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    dist = distribution_tests(analysis, feature)
    full_model = next(
        (
            row
            for row in model_rows
            if row.get("feature") == feature and row.get("model") == "ols_full_available_covariates"
        ),
        {},
    )
    endpoint_pair = next(
        (
            row
            for row in pairwise_rows
            if row.get("feature") == feature
            and row.get("left_group") == GROUP_ORDER[0]
            and row.get("right_group") == GROUP_ORDER[-1]
        ),
        {},
    )
    return {
        "feature": feature,
        "distribution_tests": dist,
        "full_available_covariates_model": full_model,
        "healthy_vs_insulin_pairwise": endpoint_pair,
        "surrogate_negative_controls": surrogate_rows,
    }


def refutation_rule(
    analysis: pd.DataFrame,
    primary_feature: str,
    surrogate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    real_groups = values_by_group(analysis, primary_feature)
    real_endpoint_d = cohens_d(real_groups[0], real_groups[-1])
    shift_24h = next((row for row in surrogate_rows if row.get("shift_minutes") == 1440), {})
    surrogate_24h_d = safe_float(shift_24h.get("healthy_vs_insulin_d"))
    sleep_minus_awake = pd.to_numeric(
        analysis.loc[analysis["status"] == "analyzed", "sleep_minus_awake_pearson_r"],
        errors="coerce",
    ).dropna()
    median_sleep_minus_awake = safe_float(sleep_minus_awake.median())
    endpoint_rule = (
        real_endpoint_d > 2.0 * abs(surrogate_24h_d)
        if safe_float(real_endpoint_d) is not None and surrogate_24h_d is not None
        else None
    )
    sleep_specificity_rule = (
        median_sleep_minus_awake < 0
        if median_sleep_minus_awake is not None
        else None
    )
    passes = bool(endpoint_rule and sleep_specificity_rule) if endpoint_rule is not None and sleep_specificity_rule is not None else None
    return {
        "rule_id": "H-MIG01-PREFLIGHT-REFUTE-V1",
        "primary_feature": primary_feature,
        "criterion_1": "primary healthy-vs-insulin Cohen d must be positive and exceed 2x abs(1440-minute surrogate endpoint d)",
        "criterion_2": "median sleep_minus_awake_pearson_r must be negative, indicating awake coupling exceeds sleep coupling",
        "real_endpoint_d": safe_float(real_endpoint_d),
        "surrogate_1440_endpoint_d": surrogate_24h_d,
        "median_sleep_minus_awake_pearson_r": median_sleep_minus_awake,
        "endpoint_rule_pass": endpoint_rule,
        "sleep_specificity_rule_pass": sleep_specificity_rule,
        "probe_passes_refutation_rule": passes,
        "interpretation": "If this rule fails after execution, the proposal should remain probe_valid_only and must not be promoted to a supported biological claim.",
    }


def has_all_six_pairwise_rows(pairwise_rows: list[dict[str, Any]]) -> bool:
    feature_rows = [row for row in pairwise_rows if row.get("feature") == PRIMARY_FEATURE]
    pairs = {(row.get("left_group"), row.get("right_group")) for row in feature_rows}
    expected = set()
    for left_idx, left_group in enumerate(GROUP_ORDER[:-1]):
        for right_idx in range(left_idx + 1, len(GROUP_ORDER)):
            expected.add((left_group, GROUP_ORDER[right_idx]))
    return expected.issubset(pairs)


def safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return safe_float(numerator / denominator)


def abs_value(value: Any) -> float | None:
    number = safe_float(value)
    return abs(number) if number is not None else None


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if not np.isfinite(out):
        return None
    return out


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json(item) for item in value]
    if isinstance(value, tuple):
        return [clean_json(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return safe_float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


if __name__ == "__main__":
    main()
