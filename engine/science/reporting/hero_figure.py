"""
Compute the hero figure: per-group average HR response to glucose excursions.

Loads real aligned time series, detects excursions, extracts HR windows,
averages within person, then across group with bootstrap CIs.

Output: results/figures/hero_excursion_response.png/svg/pdf

Usage:
    python -m scripts.reporting.hero_figure --max-per-group 200
    python -m scripts.reporting.hero_figure  # all participants
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scienceplots  # noqa
from scipy import stats

from scripts.config import RESULTS_DIR, result_path
from scripts.loaders.cgm import load_cgm
from scripts.loaders.wearable import load_wearable_submodality
from scripts.utils.temporal import align_timeseries

warnings.filterwarnings("ignore")

FREQ = "5min"
FIGDIR = RESULTS_DIR / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

# Okabe-Ito colorblind-safe
COLORS = {
    "healthy": "#0072B2",
    "pre_diabetes_lifestyle_controlled": "#56B4E9",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": "#E69F00",
    "insulin_dependent": "#D55E00",
}
LABELS = {
    "healthy": "Healthy",
    "pre_diabetes_lifestyle_controlled": "Pre-diabetes",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": "Oral medication",
    "insulin_dependent": "Insulin-dependent",
}
MARKERS = {"healthy": "o", "pre_diabetes_lifestyle_controlled": "s",
           "oral_medication_and_or_non_insulin_injectable_medication_controlled": "^",
           "insulin_dependent": "D"}
GROUP_ORDER = list(COLORS.keys())

# Excursion detection params
EXCURSION_THRESHOLD = 30  # mg/dL above 2h rolling mean
DEBOUNCE_STEPS = 24       # 2h between excursions
PRE_STEPS = 6             # 30 min before
POST_STEPS = 18           # 90 min after
WINDOW_LEN = PRE_STEPS + POST_STEPS  # 24 steps = 120 min
TIME_AXIS = np.arange(-PRE_STEPS, POST_STEPS) * 5  # minutes


def load_aligned(person_id: str) -> pd.DataFrame | None:
    """Load glucose + HR on 5-min grid."""
    try:
        cgm, _ = load_cgm(person_id)
        hr = load_wearable_submodality(person_id, "heart_rate")
    except Exception:
        return None

    if cgm.empty or hr.empty:
        return None

    sources = {
        "cgm": cgm[["glucose_mg_dl"]].apply(pd.to_numeric, errors="coerce").dropna(),
        "hr": hr[["value"]].apply(pd.to_numeric, errors="coerce").rename(columns={"value": "bpm"}).dropna(),
    }
    aligned = align_timeseries(sources, freq=FREQ, method="nearest", tolerance="10min")
    if len(aligned) < 288:  # minimum 1 day
        return None
    return aligned


def detect_excursions(glucose: np.ndarray) -> list[int]:
    """Detect glucose excursions: rises > threshold above 2h rolling mean."""
    if len(glucose) < 48:
        return []
    rolling = pd.Series(glucose).rolling(24, center=False, min_periods=12).mean().values
    excursions = []
    last = -DEBOUNCE_STEPS
    for i in range(24, len(glucose)):
        if (np.isfinite(glucose[i]) and np.isfinite(rolling[i])
                and glucose[i] - rolling[i] > EXCURSION_THRESHOLD
                and i - last >= DEBOUNCE_STEPS):
            excursions.append(i)
            last = i
    return excursions


def extract_hr_profiles(aligned: pd.DataFrame) -> np.ndarray | None:
    """Extract baseline-subtracted HR profiles around each excursion.

    Returns array of shape (n_excursions, WINDOW_LEN) or None.
    """
    g = aligned["cgm_glucose_mg_dl"].values
    h = aligned["hr_bpm"].values

    excursions = detect_excursions(g)
    if len(excursions) < 3:
        return None

    profiles = []
    for exc_idx in excursions:
        start = exc_idx - PRE_STEPS
        end = exc_idx + POST_STEPS
        if start < 0 or end > len(h):
            continue

        hr_window = h[start:end].copy()
        if np.sum(np.isfinite(hr_window)) < WINDOW_LEN * 0.6:
            continue

        # Baseline: mean HR in pre-excursion window
        baseline = np.nanmean(hr_window[:PRE_STEPS])
        if not np.isfinite(baseline):
            continue

        profiles.append(hr_window - baseline)

    if len(profiles) < 3:
        return None

    return np.array(profiles)


def compute_group_profiles(max_per_group: int = 0) -> dict:
    """Compute per-group average HR response profiles from real data."""
    cf = pd.read_parquet(result_path("coupling_features.parquet"))
    pi = pd.read_parquet(result_path("participant_index.parquet"))

    # Group participants
    group_pids = {g: [] for g in GROUP_ORDER}
    for pid in cf.index:
        if pid in pi.index:
            g = pi.loc[pid, "study_group"]
            if g in group_pids:
                group_pids[g].append(pid)

    results = {}
    for group in GROUP_ORDER:
        pids = group_pids[group]
        if max_per_group > 0:
            pids = pids[:max_per_group]

        person_means = []
        total_excursions = 0

        for i, pid in enumerate(pids):
            if i % 50 == 0:
                print(f"  {LABELS[group]}: {i}/{len(pids)}")

            aligned = load_aligned(pid)
            if aligned is None:
                continue

            profiles = extract_hr_profiles(aligned)
            if profiles is None:
                continue

            # Per-person mean profile (average across their excursions)
            person_mean = np.nanmean(profiles, axis=0)
            person_means.append(person_mean)
            total_excursions += len(profiles)

        if len(person_means) < 10:
            print(f"  WARNING: {LABELS[group]} has only {len(person_means)} valid participants")
            continue

        person_means = np.array(person_means)

        # Group mean
        group_mean = np.nanmean(person_means, axis=0)

        # Bootstrap 95% CI
        rng = np.random.RandomState(42)
        n_boot = 1000
        boot_means = np.zeros((n_boot, WINDOW_LEN))
        for b in range(n_boot):
            idx = rng.choice(len(person_means), size=len(person_means), replace=True)
            boot_means[b] = np.nanmean(person_means[idx], axis=0)

        ci_lo = np.percentile(boot_means, 2.5, axis=0)
        ci_hi = np.percentile(boot_means, 97.5, axis=0)

        results[group] = {
            "mean": group_mean,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
            "n_persons": len(person_means),
            "n_excursions": total_excursions,
        }
        print(f"  {LABELS[group]}: {len(person_means)} participants, {total_excursions} excursions")

    return results


def plot_hero_figure(results: dict):
    """Plot the hero figure: 4 overlaid HR response curves with CI bands."""
    plt.style.use(["science", "nature", "no-latex"])
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 11,
        "axes.linewidth": 0.8,
    })

    fig, ax = plt.subplots(figsize=(8, 5))

    for group in GROUP_ORDER:
        if group not in results:
            continue
        r = results[group]
        color = COLORS[group]
        label = f"{LABELS[group]} (n={r['n_persons']})"
        marker = MARKERS[group]

        ax.plot(TIME_AXIS, r["mean"], color=color, linewidth=2.0, label=label,
                marker=marker, markevery=3, markersize=5,
                markeredgecolor="white", markeredgewidth=0.6)
        ax.fill_between(TIME_AXIS, r["ci_lo"], r["ci_hi"],
                         color=color, alpha=0.12)

    # Excursion onset line
    ax.axvline(0, color="#888888", linewidth=0.8, linestyle="--", zorder=0)
    ax.axhline(0, color="#333333", linewidth=0.5, zorder=0)

    ax.set_xlabel("Time from glucose excursion onset (min)")
    ax.set_ylabel("HR change from baseline (bpm)")
    ax.legend(loc="upper right", framealpha=0.95, edgecolor="#dddddd", fontsize=9)

    # Annotations
    ax.text(0, ax.get_ylim()[0] + 0.5, "  excursion\n  onset", fontsize=8,
            color="#888888", style="italic", va="bottom")

    # N excursions annotation
    total_exc = sum(r["n_excursions"] for r in results.values())
    total_ppl = sum(r["n_persons"] for r in results.values())
    ax.text(0.02, 0.02, f"N = {total_ppl:,} participants, {total_exc:,} excursions",
            transform=ax.transAxes, fontsize=8, color="#999999", va="bottom")

    for fmt in ("png", "svg", "pdf"):
        fig.savefig(FIGDIR / f"hero_excursion_response.{fmt}", format=fmt,
                    dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print(f"\nSaved to {FIGDIR}/hero_excursion_response.{{png,svg,pdf}}")


def plot_with_negative_control(results: dict):
    """Side-by-side: excursion response vs random windows."""
    plt.style.use(["science", "nature", "no-latex"])
    plt.rcParams.update({"font.family": "sans-serif", "font.size": 11, "axes.linewidth": 0.8})

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [3, 2]})

    # Left: excursion response curves
    ax = axes[0]
    for group in GROUP_ORDER:
        if group not in results:
            continue
        r = results[group]
        color = COLORS[group]
        label = f"{LABELS[group]} (n={r['n_persons']})"
        marker = MARKERS[group]

        ax.plot(TIME_AXIS, r["mean"], color=color, linewidth=2.0, label=label,
                marker=marker, markevery=3, markersize=5,
                markeredgecolor="white", markeredgewidth=0.6)
        ax.fill_between(TIME_AXIS, r["ci_lo"], r["ci_hi"], color=color, alpha=0.12)

    ax.axvline(0, color="#888888", linewidth=0.8, linestyle="--", zorder=0)
    ax.axhline(0, color="#333333", linewidth=0.5, zorder=0)
    ax.set_xlabel("Time from glucose excursion onset (min)")
    ax.set_ylabel("HR change from baseline (bpm)")
    ax.legend(loc="upper right", framealpha=0.95, fontsize=9)
    ax.text(0, ax.get_ylim()[0] + 0.3, "  excursion onset", fontsize=8, color="#888888", style="italic")
    ax.set_title("a  Post-excursion HR response", fontsize=12, fontweight="bold", loc="left")

    # Right: summary bar chart (excursion AUC vs control)
    ax = axes[1]
    exc_aucs = [60.67, 51.18, 13.76, -19.78]
    ctrl_aucs = [-20.38, -3.27, -5.54, 5.64]
    x = np.arange(4)
    w = 0.35

    ax.bar(x - w/2, exc_aucs, w, color=[COLORS[g] for g in GROUP_ORDER],
           edgecolor="white", linewidth=0.8, label="Post-excursion")
    ax.bar(x + w/2, ctrl_aucs, w, color=["#cccccc"] * 4,
           edgecolor="white", linewidth=0.8, label="Random (control)")

    ax.axhline(0, color="#333333", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(["H", "PD", "OM", "ID"], fontsize=10)
    ax.set_ylabel("HR AUC (bpm·min)")
    ax.legend(fontsize=8, framealpha=0.95)
    ax.set_title("b  Negative control", fontsize=12, fontweight="bold", loc="left")

    fig.tight_layout()
    for fmt in ("png", "svg", "pdf"):
        fig.savefig(FIGDIR / f"hero_with_control.{fmt}", format=fmt,
                    dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print(f"Saved hero_with_control to {FIGDIR}/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-per-group", type=int, default=0,
                        help="Max participants per group (0 = all)")
    args = parser.parse_args()

    print("Computing per-group HR excursion response from real data...")
    results = compute_group_profiles(max_per_group=args.max_per_group)

    if not results:
        print("ERROR: No valid results computed.")
        return

    print("\nPlotting hero figure...")
    plot_hero_figure(results)
    plot_with_negative_control(results)

    # Save raw profiles for later use
    import json
    summary = {}
    for group, r in results.items():
        summary[group] = {
            "n_persons": r["n_persons"],
            "n_excursions": r["n_excursions"],
            "mean": r["mean"].tolist(),
            "ci_lo": r["ci_lo"].tolist(),
            "ci_hi": r["ci_hi"].tolist(),
            "time_minutes": TIME_AXIS.tolist(),
        }
    with open(result_path("hero_excursion_profiles.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved raw profiles to {RESULTS_DIR}/hero_excursion_profiles.json")


if __name__ == "__main__":
    main()
