"""
Phase 2 per-participant feature extraction:
  H-NEW03: Post-glucose-excursion HR response dynamics
  H-NEW10: Activity-glucose coupling reversal (exercise vs recovery)

Usage:
    python -m scripts.hypothesis.hypothesis_phase2 --num-shards 32 --shard-index 0
    python -m scripts.hypothesis.hypothesis_phase2 --limit 10  # pilot
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from scripts.config import RESULTS_DIR, result_path
from scripts.loaders.cgm import load_cgm
from scripts.loaders.wearable import load_wearable_submodality
from scripts.utils.temporal import align_timeseries
from scripts.utils.timezone import get_timezone

warnings.filterwarnings("ignore")

FREQ = "5min"
MIN_POINTS = 144


def _as_numeric(df, col, out):
    d = df[[col]].copy()
    d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.rename(columns={col: out})
    return d.dropna()


def load_aligned(person_id):
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

    # Activity
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

    # Sleep mask
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
                tz = get_timezone(person_id)
                local = aligned.index.tz_convert(tz)
                h = local.hour + local.minute / 60.0
                aligned["asleep"] = ((h >= 22.0) | (h < 6.0)).astype(float)
        else:
            tz = get_timezone(person_id)
            local = aligned.index.tz_convert(tz)
            h = local.hour + local.minute / 60.0
            aligned["asleep"] = ((h >= 22.0) | (h < 6.0)).astype(float)
    except Exception:
        tz = get_timezone(person_id)
        local = aligned.index.tz_convert(tz)
        h = local.hour + local.minute / 60.0
        aligned["asleep"] = ((h >= 22.0) | (h < 6.0)).astype(float)

    return aligned


# ── H-NEW03: Post-excursion HR response ──────────────────────────────

def detect_excursions(glucose, threshold=30, debounce=24):
    """Detect glucose excursions: rises > threshold mg/dL above 2h rolling mean."""
    if len(glucose) < 48:
        return []
    rolling_mean = pd.Series(glucose).rolling(24, center=False, min_periods=12).mean().values
    excursions = []
    last_exc = -debounce
    for i in range(24, len(glucose)):
        if np.isfinite(glucose[i]) and np.isfinite(rolling_mean[i]):
            if glucose[i] - rolling_mean[i] > threshold and (i - last_exc) >= debounce:
                excursions.append(i)
                last_exc = i
    return excursions


def compute_excursion_hr_response(aligned):
    """H-NEW03: Event-triggered HR response to glucose excursions."""
    g = aligned["cgm_glucose_mg_dl"].values
    h = aligned["hr_bpm"].values
    asleep = aligned["asleep"].values
    activity = aligned["activity_steps"].values

    excursions = detect_excursions(g, threshold=30, debounce=24)
    if len(excursions) < 3:
        return {}

    pre_window = 6   # 30 min pre
    post_window = 18  # 90 min post

    hr_aucs = []
    hr_peaks = []
    hr_latencies = []
    hr_recoveries = []
    exc_magnitudes = []
    wake_excursions = []

    # Also random controls
    rng = np.random.RandomState(42)
    all_indices = list(range(pre_window, len(g) - post_window))
    non_exc = [i for i in all_indices if all(abs(i - e) > post_window for e in excursions)]
    ctrl_indices = rng.choice(non_exc, size=min(len(excursions), len(non_exc)), replace=False) if non_exc else []

    ctrl_aucs = []

    for exc_idx in excursions:
        if exc_idx - pre_window < 0 or exc_idx + post_window >= len(h):
            continue

        hr_window = h[exc_idx - pre_window:exc_idx + post_window]
        g_window = g[exc_idx - pre_window:exc_idx + post_window]

        if np.sum(np.isfinite(hr_window)) < 12:
            continue

        # Baseline: mean HR in pre-excursion window
        baseline_hr = np.nanmean(hr_window[:pre_window])
        if not np.isfinite(baseline_hr):
            continue

        post_hr = hr_window[pre_window:] - baseline_hr
        post_hr_clean = np.where(np.isfinite(post_hr), post_hr, 0)

        # AUC of HR response (0-90 min)
        auc = float(np.sum(post_hr_clean) * 5)  # in bpm*minutes
        hr_aucs.append(auc)

        # Peak amplitude and latency
        peak_idx = np.argmax(post_hr_clean)
        hr_peaks.append(float(post_hr_clean[peak_idx]))
        hr_latencies.append(float(peak_idx * 5))  # minutes

        # Recovery: time to return to 50% of peak
        peak_val = post_hr_clean[peak_idx]
        if peak_val > 0:
            half_val = peak_val * 0.5
            recovery_time = np.nan
            for j in range(peak_idx, len(post_hr_clean)):
                if post_hr_clean[j] <= half_val:
                    recovery_time = float((j - peak_idx) * 5)
                    break
            hr_recoveries.append(recovery_time)
        else:
            hr_recoveries.append(np.nan)

        # Excursion magnitude
        exc_magnitudes.append(float(g[exc_idx] - np.nanmean(g[max(0, exc_idx - 24):exc_idx])))

        # Is this awake?
        wake_excursions.append(asleep[exc_idx] == 0)

    # Random control AUC
    for ctrl_idx in ctrl_indices:
        hr_window = h[ctrl_idx - pre_window:ctrl_idx + post_window]
        baseline_hr = np.nanmean(hr_window[:pre_window])
        if np.isfinite(baseline_hr) and np.sum(np.isfinite(hr_window)) >= 12:
            post_hr = hr_window[pre_window:] - baseline_hr
            ctrl_aucs.append(float(np.nansum(np.where(np.isfinite(post_hr), post_hr, 0)) * 5))

    features = {}
    features["n_excursions"] = len(hr_aucs)

    if len(hr_aucs) < 3:
        return features

    features["exc_hr_auc_mean"] = float(np.nanmean(hr_aucs))
    features["exc_hr_auc_sd"] = float(np.nanstd(hr_aucs))
    features["exc_hr_peak_mean"] = float(np.nanmean(hr_peaks))
    features["exc_hr_latency_mean"] = float(np.nanmean(hr_latencies))
    features["exc_hr_recovery_mean"] = float(np.nanmean([r for r in hr_recoveries if np.isfinite(r)]) if any(np.isfinite(r) for r in hr_recoveries) else np.nan)
    features["exc_magnitude_mean"] = float(np.nanmean(exc_magnitudes))

    # Stereotypy: inter-excursion CV of HR AUC
    if np.nanmean(hr_aucs) != 0:
        features["exc_hr_auc_cv"] = float(np.nanstd(hr_aucs) / abs(np.nanmean(hr_aucs)))

    # Negative control: random window AUC
    if len(ctrl_aucs) >= 3:
        features["ctrl_hr_auc_mean"] = float(np.nanmean(ctrl_aucs))
        features["exc_vs_ctrl_auc_diff"] = features["exc_hr_auc_mean"] - features["ctrl_hr_auc_mean"]

    # Wake-only subset
    wake_aucs = [a for a, w in zip(hr_aucs, wake_excursions) if w]
    if len(wake_aucs) >= 3:
        features["exc_hr_auc_wake_mean"] = float(np.nanmean(wake_aucs))

    # Normalize by excursion magnitude
    if len(exc_magnitudes) >= 3 and np.nanmean(exc_magnitudes) > 0:
        features["exc_hr_per_mg_dl"] = float(np.nanmean(hr_aucs) / np.nanmean(exc_magnitudes))

    return features


# ── H-NEW10: Activity-glucose coupling reversal ──────────────────────

def detect_activity_bouts(activity, min_steps=20, min_bins=3):
    """Detect walking bouts: >= min_steps per 5-min bin for >= min_bins consecutive bins."""
    bouts = []
    in_bout = False
    bout_start = 0
    for i in range(len(activity)):
        if activity[i] >= min_steps:
            if not in_bout:
                bout_start = i
                in_bout = True
        else:
            if in_bout and (i - bout_start) >= min_bins:
                bouts.append((bout_start, i))
            in_bout = False
    if in_bout and (len(activity) - bout_start) >= min_bins:
        bouts.append((bout_start, len(activity)))
    return bouts


def compute_activity_glucose_reversal(aligned, person_id):
    """H-NEW10: glucose-activity coupling during exercise vs recovery."""
    g = aligned["cgm_glucose_mg_dl"].values
    activity = aligned["activity_steps"].values
    asleep = aligned["asleep"].values

    # Only waking hours
    tz = get_timezone(person_id)
    local_hour = aligned.index.tz_convert(tz).hour
    morning_mask = (local_hour >= 6) & (local_hour < 10) & (asleep == 0)  # Focus on morning bouts

    bouts = detect_activity_bouts(activity)
    if len(bouts) < 3:
        return {}

    exercise_corrs = []
    recovery_corrs = []
    exercise_glucose_changes = []
    recovery_glucose_changes = []

    for start, end in bouts:
        bout_len = end - start
        recovery_end = min(end + bout_len, len(g))

        # Exercise period
        g_ex = g[start:end]
        a_ex = activity[start:end]
        mask_ex = np.isfinite(g_ex) & np.isfinite(a_ex) & (a_ex > 0)
        if mask_ex.sum() >= 3:
            exercise_corrs.append(float(stats.spearmanr(g_ex[mask_ex], a_ex[mask_ex])[0]))
            exercise_glucose_changes.append(float(g_ex[mask_ex][-1] - g_ex[mask_ex][0]) if mask_ex.sum() > 1 else np.nan)

        # Recovery period (same duration after bout)
        if recovery_end > end + 3:
            g_rec = g[end:recovery_end]
            a_rec = activity[end:recovery_end]
            mask_rec = np.isfinite(g_rec)
            if mask_rec.sum() >= 3:
                recovery_glucose_changes.append(float(np.nanmean(g_rec) - g_ex[mask_ex][-1]) if mask_ex.sum() > 0 else np.nan)

    features = {}
    features["n_activity_bouts"] = len(bouts)

    if len(exercise_corrs) < 3:
        return features

    features["exercise_glucose_activity_r"] = float(np.nanmean(exercise_corrs))
    features["exercise_glucose_change"] = float(np.nanmean([c for c in exercise_glucose_changes if np.isfinite(c)])) if exercise_glucose_changes else np.nan
    features["recovery_glucose_change"] = float(np.nanmean([c for c in recovery_glucose_changes if np.isfinite(c)])) if recovery_glucose_changes else np.nan

    # Phase reversal: is exercise glucose change negative and recovery positive?
    if np.isfinite(features.get("exercise_glucose_change", np.nan)) and np.isfinite(features.get("recovery_glucose_change", np.nan)):
        features["glucose_phase_reversal"] = float(features["recovery_glucose_change"] - features["exercise_glucose_change"])

    return features


# ── Main ──────────────────────────────────────────────────────────────

def process_participant(person_id):
    aligned = load_aligned(person_id)
    if aligned.empty or len(aligned) < MIN_POINTS:
        return None
    features = {"person_id": person_id}
    features.update(compute_excursion_hr_response(aligned))
    features.update(compute_activity_glucose_reversal(aligned, person_id))
    return features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    cf = pd.read_parquet(result_path("coupling_features.parquet"))
    all_ids = sorted(cf.index.tolist())
    if args.limit > 0:
        all_ids = all_ids[:args.limit]
    shard_ids = [pid for i, pid in enumerate(all_ids) if i % args.num_shards == args.shard_index]
    print(f"Phase2 shard {args.shard_index}/{args.num_shards}: {len(shard_ids)} participants")

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
        print("No results.")
        return
    df = pd.DataFrame(results).set_index("person_id")
    out_path = args.output or str(result_path("hypothesis_phase2_features.parquet"))
    df.to_parquet(out_path)
    print(f"Wrote {len(df)} rows x {len(df.columns)} cols to {out_path}")


if __name__ == "__main__":
    main()
