"""Build publication-style figures for JEPA results.

Outputs are written under docs/decks/figures/jepa_results/ as PNG and PDF.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "decks" / "figures" / "jepa_results"

PALETTE = {
    "blue": "#0072B2",
    "sky": "#56B4E9",
    "orange": "#E69F00",
    "green": "#009E73",
    "purple": "#7B3294",
    "gray": "#6E7787",
    "black": "#1A1A1A",
    "light_gray": "#D9D9D9",
}


def _save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=320, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / name.replace(".png", ".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _style_axis(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.8)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.tick_params(axis="both", width=0.8, length=3.2, color=PALETTE["black"])


def _panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.12,
        1.04,
        label,
        transform=ax.transAxes,
        fontsize=9,
        fontweight="bold",
        va="bottom",
        ha="left",
    )


def plot_horizon_suite() -> None:
    path = ROOT / "foundation_jepa/window" / "artifacts" / "horizon_suite" / "summary.csv"
    df = pd.read_csv(path)
    order = ["aligned", "wrong_day", "participant_shuffle"]
    labels = {
        "aligned": "Aligned",
        "wrong_day": "Wrong-day",
        "participant_shuffle": "Participant shuffle",
    }
    colors = {
        "aligned": PALETTE["blue"],
        "wrong_day": PALETTE["orange"],
        "participant_shuffle": PALETTE["gray"],
    }

    summary = (
        df.groupby(["horizon_minutes", "control"])["test_jepa"]
        .agg(["mean", "std"])
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(7.2, 3.6), constrained_layout=True)
    for control in order:
        part = summary[summary["control"] == control].sort_values("horizon_minutes")
        ax.errorbar(
            part["horizon_minutes"],
            part["mean"],
            yerr=part["std"],
            marker="o",
            linewidth=1.8,
            markersize=4.6,
            capsize=2.4,
            color=colors[control],
            zorder=3,
        )
        ax.text(
            float(part["horizon_minutes"].iloc[-1]) + 6,
            float(part["mean"].iloc[-1]),
            labels[control],
            va="center",
            ha="left",
            color=colors[control],
            fontsize=8.2,
        )

    _panel_label(ax, "a")
    ax.set_xlabel("Prediction horizon (min)")
    ax.set_ylabel("Held-out JEPA loss")
    ax.set_xticks([0, 30, 60, 120])
    ax.set_xlim(-5, 157)
    ax.set_ylim(3.10, 4.52)
    _style_axis(ax)
    _save(fig, "horizon_suite.png")


def plot_event_type_heatmap() -> None:
    path = ROOT / "foundation_jepa/window" / "artifacts" / "event_type_control_suite" / "summary.csv"
    df = pd.read_csv(path)
    event_order = ["glucose_rise", "activity_bout", "dawn_proxy", "sleep_transition"]
    control_order = ["aligned", "wrong_day", "participant_shuffle"]

    pivot = (
        df.groupby(["event_mode", "control"])["test_jepa"]
        .mean()
        .unstack("control")
        .loc[event_order, control_order]
    )

    fig, ax = plt.subplots(figsize=(6.6, 3.45), constrained_layout=True)
    image = ax.imshow(pivot.values, cmap="Blues", vmin=3.45, vmax=4.50, aspect="auto")
    ax.set_xticks(
        np.arange(len(control_order)),
        labels=["Aligned", "Wrong-day", "Participant\nshuffle"],
    )
    ax.set_yticks(
        np.arange(len(event_order)),
        labels=["Glucose rise", "Activity bout", "Dawn proxy", "Sleep transition"],
    )
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            value = pivot.iloc[i, j]
            color = "white" if value > 4.05 else PALETTE["black"]
            ax.text(j, i, f"{value:.3f}", ha="center", va="center", color=color, fontsize=8.0)

    _panel_label(ax, "b")
    cbar = fig.colorbar(image, ax=ax, fraction=0.044, pad=0.025)
    cbar.set_label("Held-out JEPA loss", fontsize=8.0)
    cbar.ax.tick_params(labelsize=7.8, width=0.8, length=3)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0)
    _save(fig, "event_type_heatmap.png")


def plot_probe_gains() -> None:
    random_path = (
        ROOT
        / "foundation_jepa/window"
        / "artifacts"
        / "probe_runs"
        / "horizon_030min_seed_42_aligned"
        / "physiology_probe_metrics.csv"
    )
    event_path = (
        ROOT
        / "foundation_jepa/window"
        / "artifacts"
        / "event_probe_runs"
        / "mixed_events_horizon_030min_seed_42_aligned"
        / "robust_probes"
        / "physiology_probe_metrics.csv"
    )
    target_labels = [
        ("target_cgm_mean_z", "CGM mean", "test_r2"),
        ("target_cgm_delta_z", "CGM delta", "test_r2"),
        ("target_cgm_rise_event", "CGM rise", "test_auc"),
        ("target_hr_mean_z", "HR mean", "test_r2"),
        ("target_asleep_mean_z", "Asleep", "test_r2"),
        ("target_steps_mean_z", "Steps", "test_r2"),
        ("target_calories_mean_z", "Calories", "test_r2"),
        ("target_light_total_mean_z", "Light", "test_r2"),
    ]

    def gains(path: Path) -> pd.Series:
        df = pd.read_csv(path)
        rows = {}
        for label, display, metric in target_labels:
            sub = df[df["label"] == label].set_index("feature_set")
            rows[display] = float(sub.loc["jepa_embedding", metric] - sub.loc["context_summary", metric])
        return pd.Series(rows)

    random_gain = gains(random_path)
    event_gain = gains(event_path)
    order = event_gain.sort_values().index.tolist()
    random_gain = random_gain.loc[order]
    event_gain = event_gain.loc[order]

    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(7.2, 3.85), constrained_layout=True)
    ax.barh(y + 0.17, random_gain.values, height=0.30, color="#A6CEE3", label="Random windows")
    ax.barh(y - 0.17, event_gain.values, height=0.30, color=PALETTE["blue"], label="Mixed events")
    ax.axvline(0, color=PALETTE["black"], linewidth=0.8)
    ax.set_yticks(y, order)
    ax.set_xlabel("JEPA gain over context summary")
    ax.set_xlim(0, 0.18)
    ax.set_xticks([0.00, 0.05, 0.10, 0.15])
    _panel_label(ax, "c")
    _style_axis(ax)
    ax.legend(
        frameon=False,
        ncol=2,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.025),
        borderaxespad=0,
        handlelength=1.2,
        columnspacing=1.2,
    )
    _save(fig, "probe_gains.png")


def plot_sequence_ablation() -> None:
    path = ROOT / "foundation_jepa/sequence" / "artifacts" / "next_stage" / "summary.csv"
    df = pd.read_csv(path)
    configs = [
        "full_joint",
        "sequence_only_joint",
        "full_pure_jepa",
        "sequence_only_pure_jepa",
        "shuffle_all_joint",
    ]
    display = [
        "Full joint",
        "Sequence only",
        "Full pure JEPA",
        "Sequence pure JEPA",
        "Shuffle all",
    ]
    summary = df[df["config"].isin(configs)].groupby("config").agg(
        age_mae=("test_age_mae", "mean"),
        age_mae_sd=("test_age_mae", "std"),
        severity_acc=("test_severity_acc", "mean"),
    )
    summary = summary.loc[configs]

    y = np.arange(len(configs))
    fig, axes = plt.subplots(
        ncols=2,
        figsize=(7.2, 3.85),
        sharey=True,
        gridspec_kw={"width_ratios": [1.65, 1.0], "wspace": 0.04},
        constrained_layout=True,
    )
    ax0, ax1 = axes
    colors = [
        PALETTE["blue"],
        PALETTE["orange"],
        "#8073AC",
        "#B2ABD2",
        PALETTE["gray"],
    ]

    ax0.barh(y, summary["age_mae"], xerr=summary["age_mae_sd"], capsize=2, color=colors)
    ax0.set_yticks(y, display)
    ax0.invert_yaxis()
    ax0.set_xlabel("Age MAE (years)")
    ax0.set_xlim(0, 13.6)
    ax0.set_title("Age prediction", loc="left", fontsize=8.7)
    _panel_label(ax0, "d")
    _style_axis(ax0)

    ax1.hlines(y, xmin=0.20, xmax=summary["severity_acc"], color=PALETTE["light_gray"], linewidth=1.0)
    ax1.scatter(summary["severity_acc"], y, color=PALETTE["black"], s=19, zorder=3)
    ax1.set_xlabel("Severity accuracy")
    ax1.set_xlim(0.20, 0.72)
    ax1.set_xticks([0.25, 0.50, 0.70])
    ax1.set_title("Disease label", loc="left", fontsize=8.7)
    _style_axis(ax1)
    _save(fig, "sequence_ablation.png")


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8.3,
            "axes.titlesize": 8.7,
            "axes.labelsize": 8.3,
            "xtick.labelsize": 7.8,
            "ytick.labelsize": 7.8,
            "legend.fontsize": 7.8,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    plot_horizon_suite()
    plot_event_type_heatmap()
    plot_probe_gains()
    plot_sequence_ablation()
    print(f"Wrote figures to {OUT}")


if __name__ == "__main__":
    main()
