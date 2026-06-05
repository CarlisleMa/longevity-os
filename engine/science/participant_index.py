"""Build a unified participant-level index joining all manifests.

Produces one row per person with:
  - Core demographics from participants.tsv
  - File paths and summary stats from each modality manifest
  - Temporal metadata (visit date, continuous modality date ranges)

Output: Parquet file in results/features/participant_index.parquet
"""

import pandas as pd
import numpy as np

from .config import RESULTS_DIR, result_path
from .participants import load_participants
from .loaders.ecg import load_ecg_manifest
from .loaders.cgm import load_cgm_manifest
from .loaders.wearable import load_wearable_manifest
from .loaders.environment import load_environment_manifest
from .loaders.retinal import (
    load_oct_manifest, load_octa_manifest,
    load_photography_manifest, load_flio_manifest,
)

OUTPUT_PATH = result_path("participant_index.parquet")


def _agg_ecg(manifest: pd.DataFrame) -> pd.DataFrame:
    """Aggregate ECG manifest to one row per person."""
    agg = manifest.groupby("person_id").agg(
        ecg_n_recordings=("wfdb_hea_filepath", "count"),
        ecg_rate=("Rate", "first"),
        ecg_pr=("PR", "first"),
        ecg_qrsd=("QRSD", "first"),
        ecg_qt=("QT", "first"),
        ecg_qtc=("QTc", "first"),
        ecg_position=("participant_position", "first"),
    )
    return agg


def _agg_cgm(manifest: pd.DataFrame) -> pd.DataFrame:
    """Aggregate CGM manifest to one row per person."""
    return manifest.set_index("person_id")[[
        "glucose_level_record_count",
        "average_glucose_level_mg_dl",
        "glucose_sensor_sampling_duration_days",
    ]].rename(columns={
        "glucose_level_record_count": "cgm_n_records",
        "average_glucose_level_mg_dl": "cgm_mean_glucose",
        "glucose_sensor_sampling_duration_days": "cgm_duration_days",
    })


def _agg_wearable(manifest: pd.DataFrame) -> pd.DataFrame:
    """Aggregate wearable manifest to one row per person."""
    cols = {
        "average_heartrate_bpm": "wearable_mean_hr",
        "average_oxygen_saturation_pct": "wearable_mean_spo2",
        "average_stress_level": "wearable_mean_stress",
        "average_sleep_hours": "wearable_mean_sleep_hrs",
        "average_respiratory_rate_bpm": "wearable_mean_rr",
        "average_daily_activity": "wearable_mean_daily_activity",
        "average_active_calories_kcal": "wearable_mean_calories",
        "sensor_sampling_duration_days": "wearable_duration_days",
    }
    sub = manifest.set_index("person_id")
    available = {k: v for k, v in cols.items() if k in sub.columns}
    result = sub[list(available.keys())].rename(columns=available)
    for col in result.columns:
        result[col] = pd.to_numeric(result[col], errors="coerce")
    return result


def _agg_env(manifest: pd.DataFrame) -> pd.DataFrame:
    """Aggregate environment manifest to one row per person."""
    return manifest.set_index("person_id")[[
        "number_of_observations",
        "sensor_sampling_extent_in_days",
        "sensor_location",
    ]].rename(columns={
        "number_of_observations": "env_n_observations",
        "sensor_sampling_extent_in_days": "env_duration_days",
        "sensor_location": "env_sensor_location",
    })


def _agg_retinal(oct_m, octa_m, photo_m, flio_m) -> pd.DataFrame:
    """Count files per person per retinal modality."""
    indices = []
    for manifest in (oct_m, octa_m, photo_m, flio_m):
        if not manifest.empty:
            indices.append(pd.Index(manifest["person_id"].dropna().astype(str).unique()))
    if not indices:
        return pd.DataFrame()

    all_ids = indices[0]
    for idx in indices[1:]:
        all_ids = all_ids.union(idx)
    counts = pd.DataFrame(index=all_ids)

    if not oct_m.empty:
        counts["oct_n_files"] = oct_m.groupby("person_id").size()
    if not octa_m.empty:
        counts["octa_n_files"] = octa_m.groupby("person_id").size()
    if not photo_m.empty:
        counts["photo_n_files"] = photo_m.groupby("person_id").size()
    if not flio_m.empty:
        counts["flio_n_files"] = flio_m.groupby("person_id").size()
    return counts


def build_participant_index(save: bool = True) -> pd.DataFrame:
    """Build the unified participant index.

    Joins participants.tsv with aggregated summaries from all modality manifests.
    Saves to results/features/participant_index.parquet if save=True.
    """
    participants = load_participants()

    # Load and aggregate each modality
    ecg_agg = _agg_ecg(load_ecg_manifest())
    cgm_agg = _agg_cgm(load_cgm_manifest())
    wearable_agg = _agg_wearable(load_wearable_manifest())
    env_agg = _agg_env(load_environment_manifest())
    retinal_agg = _agg_retinal(
        load_oct_manifest(), load_octa_manifest(),
        load_photography_manifest(), load_flio_manifest(),
    )

    # Join all
    index = participants.copy()
    for agg in [ecg_agg, cgm_agg, wearable_agg, env_agg, retinal_agg]:
        if not agg.empty:
            index = index.join(agg, how="left")

    if save:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        index.to_parquet(OUTPUT_PATH)

    return index


def load_participant_index() -> pd.DataFrame:
    """Load the pre-built participant index from Parquet."""
    if not OUTPUT_PATH.exists():
        return build_participant_index(save=True)
    return pd.read_parquet(OUTPUT_PATH)
