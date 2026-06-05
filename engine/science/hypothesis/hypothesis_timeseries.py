"""
Combined per-participant time-series feature extraction for hypotheses:
  H-NEW01: Frequency-resolved coupling (spectral coherence at 6 bands)
  H-NEW06: Per-night nocturnal coupling → next-day glucose
  H-NEW13: Sleep-wake coupling reorganization speed
  H-NEW17: Diurnal 4h-block coupling profile

Designed for Slurm array parallelism. Each shard processes a subset of participants.

Usage:
    python -m scripts.hypothesis.hypothesis_timeseries --num-shards 16 --shard-index 0
    python -m scripts.hypothesis.hypothesis_timeseries --limit 10  # pilot
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal, stats

from scripts.config import RESULTS_DIR, result_path
from scripts.loaders.cgm import load_cgm
from scripts.loaders.wearable import load_wearable_submodality
from scripts.utils.temporal import align_timeseries
from scripts.utils.timezone import get_timezone

warnings.filterwarnings("ignore")

FREQ = "5min"
STEP_SEC = 300  # 5 min in seconds
FS = 1.0 / STEP_SEC  # sampling frequency in Hz
MIN_POINTS = 144  # 12h minimum


# ──────────────────────────────────────────────────────────────────────
# Data loading (reuses coupling_features.py patterns)
# ──────────────────────���───────────────────────────────────────────────

def _as_numeric(df: pd.DataFrame, col: str, out: str) -> pd.DataFrame:
    d = df[[col]].copy()
    d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.rename(columns={col: out})
    return d.dropna()


def load_aligned(person_id: str) -> pd.DataFrame:
    """Load glucose + HR + activity + sleep on 5-min grid."""
    sources = {}
    try:
        cgm, _ = load_cgm(person_id)
    except FileNotFoundError:
        return pd.DataFrame()
    if not cgm.empty:
        sources["cgm"] = _as_numeric(cgm, "glucose_mg_dl", "glucose_mg_dl")

    try:
        hr = load_wearable_submodality(person_id, "heart_rate")
    except Exception:
        hr = pd.DataFrame()
    if not hr.empty:
        sources["hr"] = _as_numeric(hr, "value", "bpm")

    if "cgm" not in sources or "hr" not in sources:
        return pd.DataFrame()

    aligned = align_timeseries(sources, freq=FREQ, method="nearest", tolerance="10min")

    # Add activity
    try:
        activity = load_wearable_submodality(person_id, "physical_activity")
        if not activity.empty and "value" in activity.columns:
            activity["value"] = pd.to_numeric(activity["value"], errors="coerce").clip(lower=0)
            steps = pd.Series(
                activity["value"].to_numpy(dtype=float),
                index=pd.DatetimeIndex(activity["start_time"]),
            ).sort_index()
            steps_5 = steps.resample(FREQ).sum()
            aligned["activity_steps"] = steps_5.reindex(aligned.index, method="nearest",
                                                         tolerance=pd.Timedelta("150s")).fillna(0.0)
    except Exception:
        pass
    if "activity_steps" not in aligned.columns:
        aligned["activity_steps"] = 0.0

    # Add sleep
    try:
        sleep = load_wearable_submodality(person_id, "sleep")
        if not sleep.empty and {"start_time", "end_time"}.issubset(sleep.columns):
            sleep_clean = sleep[sleep["value"].astype(str).str.lower() != "awake"].dropna(subset=["start_time", "end_time"])
            if not sleep_clean.empty:
                s_pos = aligned.index.searchsorted(pd.DatetimeIndex(sleep_clean["start_time"]), side="left")
                e_pos = aligned.index.searchsorted(pd.DatetimeIndex(sleep_clean["end_time"]), side="left")
                diff = np.zeros(len(aligned) + 1, dtype=int)
                for s, e in zip(s_pos, e_pos):
                    s, e = max(0, min(int(s), len(aligned))), max(0, min(int(e), len(aligned)))
                    if e > s:
                        diff[s] += 1
                        diff[e] -= 1
                aligned["asleep"] = (np.cumsum(diff[:-1]) > 0).astype(float)
            else:
                aligned["asleep"] = _heuristic_sleep(aligned.index, person_id)
        else:
            aligned["asleep"] = _heuristic_sleep(aligned.index, person_id)
    except Exception:
        aligned["asleep"] = _heuristic_sleep(aligned.index, person_id)

    return aligned


def _heuristic_sleep(index, person_id):
    tz = get_timezone(person_id)
    local = index.tz_convert(tz)
    h = local.hour + local.minute / 60.0
    return ((h >= 22.0) | (h < 6.0)).astype(float)


def _valid(g, h, min_n=24):
    """Return clean paired arrays."""
    mask = np.isfinite(g) & np.isfinite(h)
    if mask.sum() < min_n:
        return None, None
    return g[mask], h[mask]


# ──────────────────────────────────────────────────────────────────────
# H-NEW01: Frequency-resolved spectral coherence
# ──────────��───────────────────────────────────────────────────────────

# Frequency bands (in Hz at 5-min sampling = 1/300 Hz)
# Period -> freq: f = 1/(period_in_seconds)
BANDS = {
    "30_60min": (1 / 3600, 1 / 1800),         # 30-60 min periods
    "1_2h":     (1 / 7200, 1 / 3600),         # 1-2 h
    "2_4h":     (1 / 14400, 1 / 7200),        # 2-4 h
    "4_8h":     (1 / 28800, 1 / 14400),       # 4-8 h
}


def compute_spectral_coherence(glucose: np.ndarray, hr: np.ndarray) -> dict:
    """Compute coherence between glucose and HR at multiple frequency bands.

    Uses Welch's method with segments sized for the lowest frequency band.
    """
    g, h = _valid(glucose, hr, min_n=MIN_POINTS)
    if g is None:
        return {}

    # Welch coherence: nperseg should be ~2x the longest period of interest (8h = 96 steps)
    nperseg = min(192, len(g) // 4)  # 192 steps = 16h, but cap at len/4
    if nperseg < 48:  # need at least 4h segments
        return {}

    freqs, coh = signal.coherence(g, h, fs=FS, nperseg=nperseg, noverlap=nperseg // 2)

    features = {}
    for band_name, (f_lo, f_hi) in BANDS.items():
        mask = (freqs >= f_lo) & (freqs <= f_hi)
        if mask.sum() > 0:
            features[f"coherence_{band_name}"] = float(np.mean(coh[mask]))
        else:
            features[f"coherence_{band_name}"] = np.nan

    # Also compute broadband coherence for comparison
    features["coherence_broadband"] = float(np.mean(coh[(freqs > 0)]))

    return features


# ─────��────────────────────────────���───────────────────────────────────
# H-NEW17: Diurnal 4h-block coupling
# ──────────────────────────────────────────────────────────────────────

TOD_BLOCKS = {
    "00_04": (0, 4),
    "04_08": (4, 8),
    "08_12": (8, 12),
    "12_16": (12, 16),
    "16_20": (16, 20),
    "20_24": (20, 24),
}


def compute_diurnal_coupling(aligned: pd.DataFrame, person_id: str) -> dict:
    """Compute glucose-HR coupling in 4h time-of-day blocks, pooling across days."""
    tz = get_timezone(person_id)
    local_hour = aligned.index.tz_convert(tz).hour

    features = {}
    block_couplings = []
    block_hours = []

    for block_name, (h_start, h_end) in TOD_BLOCKS.items():
        mask = (local_hour >= h_start) & (local_hour < h_end)
        subset = aligned.loc[mask]
        if len(subset) < 24:
            features[f"diurnal_r_{block_name}"] = np.nan
            continue

        g = subset["cgm_glucose_mg_dl"].values
        h = subset["hr_bpm"].values
        gv, hv = _valid(g, h)
        if gv is None:
            features[f"diurnal_r_{block_name}"] = np.nan
            continue

        r = float(np.corrcoef(gv, hv)[0, 1])
        features[f"diurnal_r_{block_name}"] = r

        # Also activity-adjusted: residualize glucose and HR on activity
        if "activity_steps" in subset.columns:
            act = subset.loc[np.isfinite(g) & np.isfinite(h), "activity_steps"].values
            if len(act) == len(gv) and np.std(act) > 0:
                from numpy.linalg import lstsq
                A = np.column_stack([act, np.ones(len(act))])
                g_resid = gv - A @ lstsq(A, gv, rcond=None)[0]
                h_resid = hv - A @ lstsq(A, hv, rcond=None)[0]
                if np.std(g_resid) > 0 and np.std(h_resid) > 0:
                    features[f"diurnal_r_act_adj_{block_name}"] = float(np.corrcoef(g_resid, h_resid)[0, 1])

        block_couplings.append(r)
        block_hours.append((h_start + h_end) / 2)

    # Cosinor fit to the diurnal profile
    if len(block_couplings) >= 4:
        couplings = np.array(block_couplings)
        hours = np.array(block_hours)
        omega = 2 * np.pi / 24
        cos_term = np.cos(omega * hours)
        sin_term = np.sin(omega * hours)
        A_mat = np.column_stack([cos_term, sin_term, np.ones(len(hours))])
        try:
            beta = np.linalg.lstsq(A_mat, couplings, rcond=None)[0]
            amplitude = np.sqrt(beta[0] ** 2 + beta[1] ** 2)
            acrophase = np.arctan2(-beta[1], beta[0]) * 12 / np.pi  # hours
            mesor = beta[2]
            fitted = A_mat @ beta
            ss_res = np.sum((couplings - fitted) ** 2)
            ss_tot = np.sum((couplings - couplings.mean()) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            features["diurnal_amplitude"] = float(amplitude)
            features["diurnal_acrophase_h"] = float(acrophase % 24)
            features["diurnal_mesor"] = float(mesor)
            features["diurnal_cosinor_r2"] = float(r2)
        except Exception:
            pass

    # Range: max - min coupling across blocks
    if len(block_couplings) >= 3:
        features["diurnal_range"] = float(max(block_couplings) - min(block_couplings))
        features["diurnal_sd"] = float(np.std(block_couplings))

    return features


# ─────────────���────────────────────────────────────────────────────────
# H-NEW06: Per-night nocturnal coupling → next-day glucose
# ────────��─────────────────────────────────────────────────────────────

def compute_nocturnal_nextday(aligned: pd.DataFrame, person_id: str) -> dict:
    """Compute per-night glucose-HR coupling and next-day glucose metrics."""
    tz = get_timezone(person_id)
    local = aligned.index.tz_convert(tz)
    dates = local.normalize().unique().sort_values()

    nights = []
    for date in dates[:-1]:  # skip last day (no next day)
        # Night: 11pm - 6am next day (local time)
        night_start = date + pd.Timedelta(hours=23)
        night_end = date + pd.Timedelta(hours=30)  # 6am next day
        # Next day: 6am - 10pm
        day_start = date + pd.Timedelta(hours=30)  # 6am
        day_end = date + pd.Timedelta(hours=46)    # 10pm

        night_mask = (local >= night_start) & (local < night_end)
        day_mask = (local >= day_start) & (local < day_end)

        night_data = aligned.loc[night_mask]
        day_data = aligned.loc[day_mask]

        if len(night_data) < 24 or len(day_data) < 24:  # min 2h night, 2h day
            continue

        g_night = night_data["cgm_glucose_mg_dl"].values
        h_night = night_data["hr_bpm"].values
        gv, hv = _valid(g_night, h_night, min_n=12)
        if gv is None:
            continue

        night_r = float(np.corrcoef(gv, hv)[0, 1])
        night_glucose_mean = float(np.nanmean(g_night))

        # Next-day metrics
        g_day = day_data["cgm_glucose_mg_dl"].dropna().values
        if len(g_day) < 24:
            continue

        day_glucose_mean = float(np.nanmean(g_day))
        day_glucose_cv = float(np.nanstd(g_day) / np.nanmean(g_day)) if np.nanmean(g_day) > 0 else np.nan
        day_tir = float(np.mean((g_day >= 70) & (g_day <= 180)))

        nights.append({
            "night_r": night_r,
            "night_glucose_mean": night_glucose_mean,
            "day_glucose_mean": day_glucose_mean,
            "day_glucose_cv": day_glucose_cv,
            "day_tir": day_tir,
        })

    features = {}
    if len(nights) < 3:
        return features

    ndf = pd.DataFrame(nights)
    features["n_nights"] = len(nights)
    features["nocturnal_coupling_mean"] = float(ndf["night_r"].mean())
    features["nocturnal_coupling_sd"] = float(ndf["night_r"].std())

    # Within-person correlation: nocturnal coupling → next-day glucose
    if len(ndf) >= 4:
        for outcome in ["day_glucose_mean", "day_glucose_cv", "day_tir"]:
            r, p = stats.spearmanr(ndf["night_r"], ndf[outcome])
            features[f"nocturnal_r_vs_{outcome}_rho"] = float(r)
            features[f"nocturnal_r_vs_{outcome}_p"] = float(p)

        # Partial: controlling for nocturnal glucose mean
        from numpy.linalg import lstsq
        C = np.column_stack([ndf["night_glucose_mean"].values, np.ones(len(ndf))])
        for outcome in ["day_glucose_mean"]:
            x = ndf["night_r"].values
            y = ndf[outcome].values
            rx = x - C @ lstsq(C, x, rcond=None)[0]
            ry = y - C @ lstsq(C, y, rcond=None)[0]
            if np.std(rx) > 0 and np.std(ry) > 0:
                r, p = stats.spearmanr(rx, ry)
                features[f"nocturnal_r_vs_{outcome}_partial_rho"] = float(r)

    return features


# ────────────────���─────────────────────────────────────��───────────────
# H-NEW13: Sleep-wake coupling reorganization speed
# ──────────────────────────────────────────────────────────��───────────

def compute_sleepwake_transition(aligned: pd.DataFrame, person_id: str) -> dict:
    """Measure coupling reorganization at sleep-wake transitions."""
    asleep = aligned["asleep"].values
    g = aligned["cgm_glucose_mg_dl"].values
    h = aligned["hr_bpm"].values

    # Detect wake transitions: asleep -> awake
    transitions = []
    for i in range(1, len(asleep)):
        if asleep[i - 1] == 1.0 and asleep[i] == 0.0:
            transitions.append(i)

    if len(transitions) < 3:
        return {}

    # For each transition, compute coupling in sliding 45-min (9-step) windows
    # from -90 min to +120 min relative to wake time
    window_size = 9  # 45 min at 5-min steps
    pre_steps = 18   # 90 min before
    post_steps = 24   # 120 min after
    offsets = list(range(-pre_steps, post_steps - window_size + 1))

    all_profiles = []
    for t_idx in transitions:
        start = t_idx - pre_steps
        end = t_idx + post_steps
        if start < 0 or end >= len(g):
            continue

        profile = []
        for off in offsets:
            w_start = t_idx + off
            w_end = w_start + window_size
            gw = g[w_start:w_end]
            hw = h[w_start:w_end]
            mask = np.isfinite(gw) & np.isfinite(hw)
            if mask.sum() >= 5 and np.std(gw[mask]) > 0 and np.std(hw[mask]) > 0:
                profile.append(float(np.corrcoef(gw[mask], hw[mask])[0, 1]))
            else:
                profile.append(np.nan)

        all_profiles.append(profile)

    if len(all_profiles) < 3:
        return {}

    profiles = np.array(all_profiles)
    mean_profile = np.nanmean(profiles, axis=0)

    # Find the transition point (offset = 0 corresponds to wake time)
    wake_idx = pre_steps  # index in offsets array corresponding to t=0

    features = {}
    features["n_wake_transitions"] = len(all_profiles)

    # Pre-wake coupling (last 60 min of sleep: offsets from -12 to 0)
    pre_indices = [i for i, o in enumerate(offsets) if -12 <= o < 0]
    post_indices = [i for i, o in enumerate(offsets) if 0 <= o < 12]  # first 60 min awake

    pre_coupling = np.nanmean(mean_profile[pre_indices]) if pre_indices else np.nan
    post_coupling = np.nanmean(mean_profile[post_indices]) if post_indices else np.nan

    features["pre_wake_coupling"] = float(pre_coupling)
    features["post_wake_coupling"] = float(post_coupling)
    features["wake_coupling_change"] = float(post_coupling - pre_coupling)

    # Reorganization speed: how many minutes until coupling stabilizes post-wake
    # Define "stabilized" as within 1 SD of the post-90min mean
    late_post = [i for i, o in enumerate(offsets) if o >= 12]  # 60+ min post-wake
    if late_post:
        stable_mean = np.nanmean(mean_profile[late_post])
        stable_sd = np.nanstd(mean_profile[late_post])
        # Find first post-wake window within stable_mean ± stable_sd
        reorg_time = np.nan
        for i, o in enumerate(offsets):
            if o < 0:
                continue
            if np.isfinite(mean_profile[i]) and abs(mean_profile[i] - stable_mean) <= max(stable_sd, 0.05):
                reorg_time = float(o * 5)  # convert steps to minutes
                break
        features["reorganization_time_min"] = reorg_time
        features["stable_coupling"] = float(stable_mean)

    # Inter-transition variability of the coupling change
    changes = []
    for prof in all_profiles:
        pre_vals = [prof[i] for i in pre_indices if np.isfinite(prof[i])]
        post_vals = [prof[i] for i in post_indices if np.isfinite(prof[i])]
        if pre_vals and post_vals:
            changes.append(np.mean(post_vals) - np.mean(pre_vals))
    if len(changes) >= 3:
        features["coupling_change_cv"] = float(np.std(changes) / abs(np.mean(changes))) if abs(np.mean(changes)) > 0.01 else np.nan

    return features


# ──────────────────────────────────────────────────────────────────────
# Main: process all participants
# ─────────────────��────────────────────────────────���───────────────────

def process_participant(person_id: str) -> dict | None:
    """Extract all hypothesis features for one participant."""
    aligned = load_aligned(person_id)
    if aligned.empty or len(aligned) < MIN_POINTS:
        return None

    g = aligned["cgm_glucose_mg_dl"].values
    h = aligned["hr_bpm"].values

    features = {"person_id": person_id}

    # H-NEW01: Spectral coherence
    features.update(compute_spectral_coherence(g, h))

    # H-NEW17: Diurnal coupling
    features.update(compute_diurnal_coupling(aligned, person_id))

    # H-NEW06: Nocturnal → next-day
    features.update(compute_nocturnal_nextday(aligned, person_id))

    # H-NEW13: Sleep-wake transition
    features.update(compute_sleepwake_transition(aligned, person_id))

    return features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    # Use coupling_features index: these are participants with valid aligned glucose+HR
    cf = pd.read_parquet(result_path("coupling_features.parquet"))
    all_ids = sorted(cf.index.tolist())

    if args.limit > 0:
        all_ids = all_ids[:args.limit]

    # Shard
    shard_ids = [pid for i, pid in enumerate(all_ids) if i % args.num_shards == args.shard_index]
    print(f"Shard {args.shard_index}/{args.num_shards}: {len(shard_ids)} participants")

    results = []
    for i, pid in enumerate(shard_ids):
        if i % 25 == 0:
            print(f"  Processing {i}/{len(shard_ids)}: {pid}")
        try:
            row = process_participant(pid)
            if row:
                results.append(row)
        except Exception as e:
            print(f"  ERROR {pid}: {e}")

    if not results:
        print("No results produced.")
        return

    df = pd.DataFrame(results).set_index("person_id")
    out_path = args.output or str(result_path("hypothesis_timeseries_features.parquet"))
    df.to_parquet(out_path)
    print(f"Wrote {len(df)} rows x {len(df.columns)} cols to {out_path}")


if __name__ == "__main__":
    main()
