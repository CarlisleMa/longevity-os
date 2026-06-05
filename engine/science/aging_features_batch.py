"""Batch compute per-person multimodal features for aging clock training.

Processes all 2,280 AI-READI participants, extracting features from:
  - CGM (glycemic variability, time-in-range, circadian glucose)
  - Wearable (circadian rhythm, sleep architecture, HR, activity)
  - Environment (air quality, light exposure, temperature)
  - Cardiac ECG (resting HR, conduction intervals from manifest)

Outputs results/features/multimodal_features.parquet: ~2280 rows x ~50 feature columns.

Usage:
    python -m scripts.aging_features_batch          # all participants
    python -m scripts.aging_features_batch --n 20   # first 20 (testing)
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback

import numpy as np
import pandas as pd

from .config import RESULTS_DIR, result_path
from .participant_index import load_participant_index
from .loaders.cgm import load_cgm, compute_cgm_metrics, compute_cgm_circadian_metrics
from .features_wearable import (
    compute_sleep_architecture,
    compute_daily_summary,
    compute_circadian_metrics,
)
from .loaders.environment import load_environment
from .utils.timezone import get_timezone


# ---------------------------------------------------------------------------
# CGM features (~15 features)
# ---------------------------------------------------------------------------

def compute_cgm_features(person_id: str) -> dict:
    """Extract CGM features for one participant.

    Uses existing load_cgm, compute_cgm_metrics, and
    compute_cgm_circadian_metrics from scripts/loaders/cgm.py.

    Returns dict with keys prefixed 'cgm_' for clarity in the final matrix.
    """
    df, _meta = load_cgm(person_id)
    if df.empty:
        return {}

    # Coerce glucose to numeric — some records have "Low"/"High" string
    # sentinels from the Dexcom G6 (below 40 or above 400 mg/dL). These
    # become NaN and are excluded by compute_cgm_metrics via .dropna().
    df["glucose_mg_dl"] = pd.to_numeric(df["glucose_mg_dl"], errors="coerce")

    # Standard glycemic metrics (mean, sd, cv, TIR 5-level, GRI, LBGI, HBGI,
    # GMI, MAGE, data completeness)
    metrics = compute_cgm_metrics(df)
    if not metrics:
        return {}

    # Circadian CGM (dawn phenomenon, nocturnal mean/CV)
    circ = compute_cgm_circadian_metrics(df, person_id)
    # circ contains 'agp' (DataFrame) which we don't need as a scalar feature
    circ.pop("agp", None)

    # Select the features we want for the aging clock matrix.
    # From compute_cgm_metrics:
    out = {
        "cgm_mean_glucose": metrics.get("mean_glucose"),
        "cgm_sd_glucose": metrics.get("std_glucose"),
        "cgm_cv_glucose": metrics.get("cv"),
        "cgm_tir": metrics.get("tir"),
        "cgm_tbr_level1": metrics.get("tbr_low"),
        "cgm_tbr_level2": metrics.get("tbr_vlow"),
        "cgm_tar_level1": metrics.get("tar_high"),
        "cgm_tar_level2": metrics.get("tar_vhigh"),
        "cgm_gri": metrics.get("gri"),
        "cgm_lbgi": metrics.get("lbgi"),
        "cgm_hbgi": metrics.get("hbgi"),
        "cgm_gmi": metrics.get("gmi"),
        "cgm_mage": metrics.get("mage"),
        # From circadian metrics:
        "cgm_dawn_phenomenon": circ.get("dawn_phenomenon"),
        "cgm_nocturnal_mean": circ.get("nocturnal_mean"),
        "cgm_nocturnal_cv": circ.get("nocturnal_cv"),
    }
    return out


# ---------------------------------------------------------------------------
# Wearable features (~20 features)
# ---------------------------------------------------------------------------

def compute_wearable_features(person_id: str) -> dict:
    """Extract wearable features for one participant.

    Uses existing functions from scripts/features_wearable.py:
      - compute_circadian_metrics -> IS, IV, M10, L5, RA, cosinor params
      - compute_sleep_architecture -> per-night sleep, aggregated to person level
      - compute_daily_summary -> per-day HR, steps, calories, aggregated
    """
    out = {}

    # --- Circadian rhythm metrics ---
    circ = compute_circadian_metrics(person_id)
    if circ:
        out["wear_is"] = circ.get("is_")
        out["wear_iv"] = circ.get("iv")
        out["wear_m10"] = circ.get("m10")
        out["wear_l5"] = circ.get("l5")
        out["wear_ra"] = circ.get("ra")
        out["wear_cosinor_amplitude"] = circ.get("cosinor_amplitude")
        out["wear_cosinor_acrophase"] = circ.get("cosinor_acrophase_hr")
        out["wear_cosinor_mesor"] = circ.get("cosinor_mesor")

    # --- Sleep architecture (person-level aggregates) ---
    sa = compute_sleep_architecture(person_id)
    if not sa.empty and len(sa) > 0:
        out["wear_mean_tst"] = round(float(sa["tst_min"].mean()), 1)
        out["wear_mean_se"] = round(float(sa["se"].mean()), 2)
        out["wear_mean_waso"] = round(float(sa["waso_min"].mean()), 1)
        if "rem_pct" in sa.columns:
            out["wear_mean_rem_pct"] = round(float(sa["rem_pct"].mean()), 2)
        if "deep_pct" in sa.columns:
            out["wear_mean_deep_pct"] = round(float(sa["deep_pct"].mean()), 2)
        # Sleep regularity: SD of sleep midpoint across nights
        if "sleep_midpoint_hr" in sa.columns:
            midpoints = sa["sleep_midpoint_hr"].dropna()
            if len(midpoints) >= 2:
                out["wear_sleep_regularity"] = round(float(midpoints.std()), 2)

    # --- Daily summary aggregates (HR, steps, calories) ---
    daily = compute_daily_summary(person_id)
    if not daily.empty and len(daily) > 0:
        # Resting HR: median across days of the per-day resting HR
        if "resting_hr" in daily.columns:
            vals = daily["resting_hr"].dropna()
            if len(vals) > 0:
                out["wear_resting_hr"] = round(float(vals.median()), 1)

        # Nocturnal HR: median of per-day nighttime HR mean
        if "hr_mean_night" in daily.columns:
            vals = daily["hr_mean_night"].dropna()
            if len(vals) > 0:
                out["wear_nocturnal_hr"] = round(float(vals.median()), 1)

        # Diurnal HR: median of per-day daytime HR mean
        if "hr_mean_day" in daily.columns:
            vals = daily["hr_mean_day"].dropna()
            if len(vals) > 0:
                out["wear_diurnal_hr"] = round(float(vals.median()), 1)

        # Nocturnal dip %: median across days
        if "nocturnal_hr_dip" in daily.columns:
            vals = daily["nocturnal_hr_dip"].dropna()
            if len(vals) > 0:
                out["wear_nocturnal_dip_pct"] = round(float(vals.median()), 2)

        # Steps: mean daily steps
        if "daily_steps" in daily.columns:
            vals = daily["daily_steps"].dropna()
            if len(vals) > 0:
                out["wear_mean_daily_steps"] = round(float(vals.mean()), 0)

        # Active calories: mean daily active calories
        if "daily_active_calories" in daily.columns:
            vals = daily["daily_active_calories"].dropna()
            if len(vals) > 0:
                out["wear_mean_active_calories"] = round(float(vals.mean()), 1)

    return out


# ---------------------------------------------------------------------------
# Environment features (~8 features)
# ---------------------------------------------------------------------------

# Bright-light threshold: lch2 (480 nm, blue) relative intensity above which
# counts as "bright outdoor light". The sensor range is 0-1 relative units;
# based on exploratory analysis, 0.3 captures sunlight exposure periods.
_BRIGHT_LIGHT_THRESHOLD = 0.3


def compute_environment_features(person_id: str) -> dict:
    """Extract environment features for one participant.

    Uses load_environment() from scripts/loaders/environment.py.
    """
    df, _meta = load_environment(person_id)
    if df.empty:
        return {}

    tz = get_timezone(person_id)
    local_idx = df.index.tz_convert(tz)

    out = {}

    # --- Air quality ---
    if "pm2.5" in df.columns:
        pm25 = df["pm2.5"].dropna()
        if len(pm25) > 0:
            out["env_mean_pm25"] = round(float(pm25.mean()), 2)
            out["env_max_pm25"] = round(float(pm25.max()), 2)

    # --- Light exposure ---
    if "lch2" in df.columns:
        lch2 = df["lch2"].dropna()
        if len(lch2) > 0:
            # Bright light hours: count of 5-sec samples above threshold,
            # converted to hours
            bright_samples = (lch2 > _BRIGHT_LIGHT_THRESHOLD).sum()
            # Each sample is 5 seconds
            out["env_bright_light_hours"] = round(
                float(bright_samples * 5 / 3600), 2
            )

        # Evening light exposure: mean lch2 between 8pm-midnight local time
        hour = local_idx.hour
        evening_mask = (hour >= 20) & (hour < 24)
        lch2_local = pd.Series(df["lch2"].values, index=local_idx)
        evening_light = lch2_local[evening_mask].dropna()
        if len(evening_light) > 0:
            out["env_evening_light_exposure"] = round(
                float(evening_light.mean()), 4
            )

    # --- Temperature ---
    if "temp" in df.columns:
        temp = df["temp"].dropna()
        if len(temp) > 0:
            out["env_mean_temp"] = round(float(temp.mean()), 2)
            # Temp range: average of (daily max - daily min)
            temp_local = pd.Series(
                temp.to_numpy(dtype=float),
                index=pd.DatetimeIndex(temp.index).tz_convert(tz),
            )
            if len(temp_local) > 0:
                daily_range = temp_local.groupby(temp_local.index.date).apply(
                    lambda g: g.max() - g.min()
                )
                if len(daily_range) > 0:
                    out["env_temp_range"] = round(float(daily_range.mean()), 2)

    # --- Humidity ---
    if "hum" in df.columns:
        hum = df["hum"].dropna()
        if len(hum) > 0:
            # Data is already 0-100% per loader docstring
            out["env_mean_humidity"] = round(float(hum.mean()), 2)

    return out


# ---------------------------------------------------------------------------
# Cardiac features (from participant index, no signal processing)
# ---------------------------------------------------------------------------

_CARDIAC_COLS = ["ecg_rate", "ecg_pr", "ecg_qrsd", "ecg_qt", "ecg_qtc"]


def extract_cardiac_features(participant_index: pd.DataFrame) -> pd.DataFrame:
    """Extract cardiac ECG features from the pre-built participant index.

    These are manifest-level measurements already aggregated per person:
    resting HR, PR interval, QRS duration, QT, QTc.

    Returns DataFrame indexed by person_id with cardiac feature columns.
    """
    available = [c for c in _CARDIAC_COLS if c in participant_index.columns]
    if not available:
        return pd.DataFrame(index=participant_index.index)
    return participant_index[available].copy()


# ---------------------------------------------------------------------------
# Main batch loop
# ---------------------------------------------------------------------------

def compute_all_features(n: int | None = None) -> pd.DataFrame:
    """Loop over all participants, compute features, return DataFrame.

    Args:
        n: If set, only process the first n participants (for testing).

    Returns:
        DataFrame with person_id as index, ~50 feature columns.
    """
    # Load participant index for modality flags and cardiac features
    pidx = load_participant_index()
    person_ids = list(pidx.index)
    if n is not None:
        person_ids = person_ids[:n]

    total = len(person_ids)
    print(f"Processing {total} participants...")

    # Extract cardiac features in bulk (already in the index)
    cardiac_df = extract_cardiac_features(pidx)

    rows = []
    errors = []
    t0 = time.time()

    for i, pid in enumerate(person_ids):
        row = {"person_id": pid}

        # --- CGM ---
        has_cgm = pidx.loc[pid, "wearable_blood_glucose"]
        if has_cgm:
            try:
                cgm_feats = compute_cgm_features(pid)
                row.update(cgm_feats)
            except Exception as e:
                errors.append((pid, "cgm", str(e)))
        # else: NaN by default (missing keys become NaN in DataFrame)

        # --- Wearable ---
        has_wearable = pidx.loc[pid, "wearable_activity_monitor"]
        if has_wearable:
            try:
                wear_feats = compute_wearable_features(pid)
                row.update(wear_feats)
            except Exception as e:
                errors.append((pid, "wearable", str(e)))

        # --- Environment ---
        has_env = pidx.loc[pid, "environment"]
        if has_env:
            try:
                env_feats = compute_environment_features(pid)
                row.update(env_feats)
            except Exception as e:
                errors.append((pid, "environment", str(e)))

        # --- Cardiac (from pre-extracted index) ---
        has_ecg = pidx.loc[pid, "cardiac_ecg"]
        if has_ecg and pid in cardiac_df.index:
            for col in _CARDIAC_COLS:
                if col in cardiac_df.columns:
                    val = cardiac_df.loc[pid, col]
                    row[col] = val if pd.notna(val) else np.nan

        rows.append(row)

        # Progress reporting
        if (i + 1) % 100 == 0 or (i + 1) == total:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (total - i - 1) / rate if rate > 0 else 0
            print(
                f"  [{i + 1}/{total}] "
                f"{elapsed:.0f}s elapsed, "
                f"{rate:.1f} participants/s, "
                f"ETA {eta:.0f}s, "
                f"{len(errors)} errors so far"
            )

    # Build DataFrame
    features = pd.DataFrame(rows).set_index("person_id")

    # Report errors
    if errors:
        print(f"\n{len(errors)} errors encountered:")
        for pid, modality, msg in errors[:20]:
            print(f"  {pid} [{modality}]: {msg}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")

    elapsed_total = time.time() - t0
    print(f"\nDone in {elapsed_total:.0f}s. Shape: {features.shape}")
    print(f"Feature columns: {list(features.columns)}")

    return features


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch compute multimodal features for aging clocks."
    )
    parser.add_argument(
        "--n", type=int, default=None,
        help="Process only the first N participants (for testing).",
    )
    args = parser.parse_args()

    features = compute_all_features(n=args.n)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = result_path("multimodal_features.parquet")
    features.to_parquet(out_path)
    print(f"\nSaved to {out_path}")
    print(f"\n{features.describe()}")
