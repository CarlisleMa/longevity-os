"""Dexcom G6 continuous glucose monitoring (CGM) loader.

Parses Open mHealth blood-glucose v3.0 JSON files.
Computes standard glycemic metrics: TIR, CV, MAGE, mean, time-in-ranges.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import CGM_DATA_DIR, CGM_MANIFEST, CGM_TIR_LOW, CGM_TIR_HIGH

_manifest_cache = {}


def load_cgm_manifest() -> pd.DataFrame:
    """Load wearable_blood_glucose/manifest.tsv."""
    if "df" in _manifest_cache:
        return _manifest_cache["df"]
    df = pd.read_csv(CGM_MANIFEST, sep="\t", dtype={"person_id": str})
    _manifest_cache["df"] = df
    return df


def load_cgm(person_id: str) -> tuple[pd.DataFrame, dict]:
    """Load CGM data for a participant.

    Returns (df, header_meta) where:
      df columns:
        - timestamp (UTC datetime, as index)
        - glucose_mg_dl (int)
        - transmitter_id (str)
        - device_id (str)
      header_meta: dict with timezone, schema_id, acquisition_rate, etc.
    """
    json_path = CGM_DATA_DIR / person_id / f"{person_id}_DEX.json"
    if not json_path.exists():
        raise FileNotFoundError(f"No CGM data for person_id={person_id}: {json_path}")

    with open(json_path) as f:
        data = json.load(f)

    header = data.get("header", {})
    header_meta = {
        "timezone": header.get("timezone", ""),
        "schema_name": header.get("schema_id", {}).get("name", ""),
        "schema_version": header.get("schema_id", {}).get("version", ""),
        "modality": header.get("modality", ""),
        "patient_id": header.get("patient_id", header.get("uuid", "")),
    }

    records = []
    for entry in data["body"]["cgm"]:
        ts = entry["effective_time_frame"]["time_interval"]["start_date_time"]
        records.append({
            "timestamp": pd.to_datetime(ts, utc=True),
            "glucose_mg_dl": entry["blood_glucose"]["value"],
            "transmitter_id": entry.get("transmitter_id", ""),
            "device_id": entry.get("source_device_id", ""),
        })

    df = pd.DataFrame(records)
    df = df.sort_values("timestamp").set_index("timestamp")
    return df, header_meta


def compute_cgm_metrics(df: pd.DataFrame) -> dict:
    """Compute standard glycemic metrics from a CGM DataFrame.

    Args:
        df: DataFrame from load_cgm() with glucose_mg_dl column.

    Returns dict with keys:
        mean_glucose, std_glucose, cv (Battelino 2019 *Diabetes Care* primary
            variability metric),
        tir (time in range 70-180), tbr (<70), tar (>180) — 3-level convenience,
        tbr_vlow (<54), tbr_low (54-69), tar_high (181-250), tar_vhigh (>250)
            — 5-level consensus per Battelino 2019 *Diabetes Care* Table 2,
        gri (Glycemia Risk Index; Klonoff 2023 *J Diabetes Sci Technol*
            17:1226-1242, PMID 35348391): 3.0·VLow + 2.4·Low + 1.6·VHigh + 0.8·High
            (note: no TIR term),
        lbgi, hbgi (Low/High Blood Glucose Index; Kovatchev 1998 *Diabetes Care*
            21:1870 PMID 9802735; 2006 update *Diabetes Care* 29:2433),
        gmi (Glucose Management Indicator; Bergenstal 2018 *Diabetes Care*
            41:2275, PMID 30224348): 3.31 + 0.02392 × mean_glucose,
        mage (Service 1970 *Diabetes*),
        pct_expected_readings, longest_gap_min, n_gaps_gt_20min
            (data completeness per 2019 consensus: ≥70% capture over ≥14d
            is the reliability threshold; AI-READI targets ~10d),
        n_readings, duration_days
    """
    g = df["glucose_mg_dl"].dropna()
    n = len(g)
    if n == 0:
        return {}

    mean_g = g.mean()
    std_g = g.std()
    cv = std_g / mean_g if mean_g > 0 else np.nan

    # 3-level (backwards-compatible) and 5-level TIR
    tir = ((g >= CGM_TIR_LOW) & (g <= CGM_TIR_HIGH)).mean()
    tbr = (g < CGM_TIR_LOW).mean()
    tar = (g > CGM_TIR_HIGH).mean()

    tbr_vlow = (g < 54).mean()
    tbr_low = ((g >= 54) & (g < 70)).mean()
    tar_high = ((g > 180) & (g <= 250)).mean()
    tar_vhigh = (g > 250).mean()

    # Glycemia Risk Index (Klonoff 2023). Expressed in percentage points.
    gri = 3.0 * tbr_vlow * 100 + 2.4 * tbr_low * 100 + 1.6 * tar_vhigh * 100 + 0.8 * tar_high * 100

    # LBGI/HBGI via Kovatchev symmetrization (glucose in mg/dL)
    lbgi, hbgi = _compute_lbgi_hbgi(g.values)

    # GMI
    gmi = 3.31 + 0.02392 * mean_g

    # MAGE: mean amplitude of glycemic excursions (peak-nadir > 1 SD)
    mage = _compute_mage(g.values, std_g)

    # Data completeness
    duration = (df.index.max() - df.index.min()).total_seconds() / 86400
    expected = duration * 288  # 288 = 1440 min/day ÷ 5-min sampling
    pct_expected = n / expected * 100 if expected > 0 else np.nan

    diffs = df.index.to_series().diff().dropna()
    diffs_min = diffs.dt.total_seconds() / 60
    longest_gap_min = float(diffs_min.max()) if len(diffs_min) else 0.0
    n_gaps_gt_20 = int((diffs_min > 20).sum())

    return {
        "mean_glucose": round(mean_g, 2),
        "std_glucose": round(std_g, 2),
        "cv": round(cv, 4),
        "tir": round(tir, 4),
        "tbr": round(tbr, 4),
        "tar": round(tar, 4),
        "tbr_vlow": round(tbr_vlow, 4),
        "tbr_low": round(tbr_low, 4),
        "tar_high": round(tar_high, 4),
        "tar_vhigh": round(tar_vhigh, 4),
        "gri": round(gri, 2),
        "lbgi": round(lbgi, 2),
        "hbgi": round(hbgi, 2),
        "gmi": round(gmi, 2),
        "mage": round(mage, 2),
        "pct_expected_readings": round(pct_expected, 1),
        "longest_gap_min": round(longest_gap_min, 1),
        "n_gaps_gt_20min": n_gaps_gt_20,
        "n_readings": n,
        "duration_days": round(duration, 1),
    }


def _compute_lbgi_hbgi(glucose: np.ndarray) -> tuple[float, float]:
    """Low/High Blood Glucose Index via Kovatchev 1998/2006 risk transform.

    Maps asymmetric mg/dL glucose scale into symmetric log-space:
        f(BG) = 1.509 × ([ln(BG)]^1.084 − 5.381)
        r(BG) = 10 × f(BG)²
        rl(BG) = r(BG) if f<0 else 0   (hypoglycemia risk)
        rh(BG) = r(BG) if f>0 else 0   (hyperglycemia risk)
        LBGI = mean(rl),  HBGI = mean(rh)

    BG=112.5 mg/dL maps to f=0 (zero risk); risk rises symmetrically for
    deviations in either direction.

    Reference: Kovatchev BP et al., "Assessment of risk for severe hypoglycemia
    among adults with IDDM," Diabetes Care 1998;21:1870-1875 (PMID 9802735).
    Updated: Kovatchev BP et al., "Evaluation of a new measure of blood glucose
    variability in diabetes," Diabetes Care 2006;29:2433-2438.
    """
    g = glucose[(glucose > 0) & ~np.isnan(glucose)]
    if len(g) == 0:
        return (0.0, 0.0)
    f = 1.509 * (np.log(g) ** 1.084 - 5.381)
    r = 10 * f ** 2
    # Kovatchev 1998 defines LBGI/HBGI as means over ALL readings (zero for the
    # non-risk side), not means over only risky readings.
    lbgi = float(np.where(f < 0, r, 0).mean())
    hbgi = float(np.where(f > 0, r, 0).mean())
    return (lbgi, hbgi)


def _compute_mage(glucose: np.ndarray, sd: float) -> float:
    """Compute MAGE from glucose array using peak-nadir method."""
    if len(glucose) < 3 or sd == 0:
        return 0.0

    # Find local extrema
    excursions = []
    last_extreme = glucose[0]
    going_up = glucose[1] > glucose[0]

    for i in range(1, len(glucose) - 1):
        if going_up and glucose[i] > glucose[i + 1]:
            # Found a peak
            amplitude = abs(glucose[i] - last_extreme)
            if amplitude > sd:
                excursions.append(amplitude)
            last_extreme = glucose[i]
            going_up = False
        elif not going_up and glucose[i] < glucose[i + 1]:
            # Found a nadir
            amplitude = abs(last_extreme - glucose[i])
            if amplitude > sd:
                excursions.append(amplitude)
            last_extreme = glucose[i]
            going_up = True

    return float(np.mean(excursions)) if excursions else 0.0


# ── Circadian CGM metrics (require local time) ─────────────────────────────

def compute_cgm_circadian_metrics(
    df: pd.DataFrame,
    person_id: str,
    bin_minutes: int = 30,
) -> dict:
    """Local-time-dependent CGM metrics: AGP percentile curves + dawn phenomenon.

    Args:
        df: CGM DataFrame from load_cgm() with UTC DatetimeIndex.
        person_id: used to look up IANA timezone via utils.timezone.
        bin_minutes: AGP bin size (default 30 min → 48 bins/day).

    Returns dict with:
        agp: DataFrame indexed by time-of-day bin with p10/p25/p50/p75/p90 columns
            (Ambulatory Glucose Profile; Mazze 2013 *Diab Tech & Ther*; endorsed
            in CGM consensus as the standard visualization)
        dawn_phenomenon: mean(06:00-09:00 local) - mean(00:00-06:00 local), mg/dL
            (Monnier 2012 *Diabetes & Metabolism*; reflects hepatic insulin
            resistance — present in ~50% of T2DM)
        nocturnal_mean: mean glucose 00:00-06:00 local, mg/dL
        nocturnal_nadir: min glucose 00:00-06:00 local, mg/dL
        nocturnal_cv: CV of glucose 00:00-06:00 local
    """
    from ..utils.timezone import to_local

    if df.empty:
        return {}
    g = df["glucose_mg_dl"].dropna()
    if len(g) == 0:
        return {}

    local_idx = to_local(g.index, person_id)
    g_local = pd.Series(g.values, index=local_idx)

    # AGP: percentile curves by time-of-day bin
    minutes_from_midnight = g_local.index.hour * 60 + g_local.index.minute
    bin_idx = (minutes_from_midnight // bin_minutes).astype(int)
    agp = (
        pd.DataFrame({"glucose": g_local.values, "bin": bin_idx})
        .groupby("bin")["glucose"]
        .quantile([0.10, 0.25, 0.50, 0.75, 0.90])
        .unstack()
    )
    agp.columns = ["p10", "p25", "p50", "p75", "p90"]
    # Convert bin index back to time-of-day (minutes from midnight)
    agp.index = agp.index * bin_minutes
    agp.index.name = "minutes_from_midnight"

    hour = g_local.index.hour
    # Dawn phenomenon & nocturnal metrics
    pre_dawn = g_local[(hour >= 0) & (hour < 6)]
    post_dawn = g_local[(hour >= 6) & (hour < 9)]
    dawn = (post_dawn.mean() - pre_dawn.mean()) if len(pre_dawn) > 0 and len(post_dawn) > 0 else np.nan
    nocturnal_mean = pre_dawn.mean() if len(pre_dawn) > 0 else np.nan
    nocturnal_nadir = pre_dawn.min() if len(pre_dawn) > 0 else np.nan
    nocturnal_cv = (pre_dawn.std() / pre_dawn.mean()) if len(pre_dawn) > 0 and pre_dawn.mean() > 0 else np.nan

    return {
        "agp": agp,
        "dawn_phenomenon": round(float(dawn), 2) if not np.isnan(dawn) else np.nan,
        "nocturnal_mean": round(float(nocturnal_mean), 2) if not np.isnan(nocturnal_mean) else np.nan,
        "nocturnal_nadir": float(nocturnal_nadir) if not np.isnan(nocturnal_nadir) else np.nan,
        "nocturnal_cv": round(float(nocturnal_cv), 4) if not np.isnan(nocturnal_cv) else np.nan,
    }
