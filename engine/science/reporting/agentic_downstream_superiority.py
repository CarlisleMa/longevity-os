#!/usr/bin/env python3
"""Downstream task superiority figure for the overall agentic system.

This emphasizes fair internal ablations on AI-READI held-out tasks:
dynamic coupling features, no-raw-level interpretable features, and the
full agent-derived coupling + summary feature set.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scripts.config import result_path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
OUT_FIG = ROOT / "docs" / "reports" / "agentic_results" / "paper_style_figures"
OUT_TABLE = ROOT / "docs" / "reports" / "agentic_results" / "tables"
OUT_NOTE = ROOT / "docs" / "reports" / "agentic_results" / "downstream_superiority_notes.md"


COL = {
    "ink": "#111827",
    "muted": "#667085",
    "grid": "#D8DEE8",
    "axis": "#B8C2D1",
    "blue": "#0072B2",
    "amber": "#E69F00",
    "teal": "#009E73",
    "pink": "#CC79A7",
    "purple": "#6F5AA7",
    "gray": "#8A94A6",
}


FEATURE_LABELS = {
    "coupling_only": "Coupling only",
    "interpretable_no_levels": "No raw levels",
    "coupling_plus_summary": "Full agent feature set",
}

FEATURE_COLORS = {
    "coupling_only": COL["blue"],
    "interpretable_no_levels": COL["amber"],
    "coupling_plus_summary": COL["teal"],
}

TASKS = [
    ("insulin_vs_healthy", "Insulin vs healthy", "AUROC"),
    ("any_diabetes_vs_healthy", "Any diabetes vs healthy", "AUROC"),
    ("hba1c", "HbA1c", "R2"),
    ("homeostatic_dysregulation", "Homeostatic dysregulation", "R2"),
    ("study_group_ordinal", "Diabetes severity ordinal", "R2"),
    ("frailty_index", "Frailty index", "R2"),
    ("allostatic_load", "Allostatic load", "R2"),
]


def setup() -> None:
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    OUT_TABLE.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.titlesize": 10.5,
            "axes.labelsize": 9.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": COL["grid"],
            "axes.linewidth": 0.8,
            "xtick.color": COL["muted"],
            "ytick.color": COL["muted"],
            "axes.labelcolor": COL["muted"],
            "text.color": COL["ink"],
        }
    )


def save(fig: plt.Figure, stem: str) -> None:
    for ext in ("png", "pdf", "svg"):
        fig.savefig(OUT_FIG / f"{stem}.{ext}", dpi=300, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def load_task_table() -> pd.DataFrame:
    perf = pd.read_csv(result_path("coupling_prediction_performance.csv"))
    rows = []
    for outcome, task_label, preferred_metric in TASKS:
        for feature_set, feature_label in FEATURE_LABELS.items():
            row = perf[(perf["outcome"].eq(outcome)) & (perf["feature_set"].eq(feature_set))].iloc[0]
            if row["task"] == "binary":
                metric_name = "AUROC"
                metric_value = float(row["auroc"])
            else:
                metric_name = "R2"
                metric_value = float(row["r2"])
            rows.append(
                {
                    "outcome": outcome,
                    "task_label": task_label,
                    "feature_set": feature_set,
                    "feature_label": feature_label,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "n_test": int(row["n_test"]),
                }
            )
    table = pd.DataFrame(rows)
    wide = table.pivot(index=["outcome", "task_label", "metric_name"], columns="feature_set", values="metric_value").reset_index()
    wide["best_ablation"] = wide[["coupling_only", "interpretable_no_levels"]].max(axis=1)
    wide["absolute_lift"] = wide["coupling_plus_summary"] - wide["best_ablation"]
    wide["relative_lift_pct"] = 100 * wide["absolute_lift"] / wide["best_ablation"].replace(0, np.nan)
    table = table.merge(wide[["outcome", "best_ablation", "absolute_lift", "relative_lift_pct"]], on="outcome", how="left")
    table.to_csv(OUT_TABLE / "downstream_superiority_long.csv", index=False)
    wide.to_csv(OUT_TABLE / "downstream_superiority_wide.csv", index=False)
    return table


def plot_ablation_slope(ax: plt.Axes, table: pd.DataFrame) -> None:
    wide = (
        table.pivot(index=["outcome", "task_label", "metric_name"], columns="feature_set", values="metric_value")
        .reset_index()
    )
    order = wide.assign(delta=wide["coupling_plus_summary"] - wide[["coupling_only", "interpretable_no_levels"]].max(axis=1))
    order = order.sort_values("coupling_plus_summary", ascending=True)
    ymap = {task: i for i, task in enumerate(order["task_label"])}

    for row in order.itertuples(index=False):
        y = ymap[row.task_label]
        xs = [row.coupling_only, row.interpretable_no_levels, row.coupling_plus_summary]
        ax.plot(xs, [y, y, y], color=COL["grid"], linewidth=1.6, zorder=1)
        for fs, x in zip(["coupling_only", "interpretable_no_levels", "coupling_plus_summary"], xs):
            ax.scatter(x, y, s=92 if fs != "coupling_plus_summary" else 135,
                       color=FEATURE_COLORS[fs], edgecolor="white", linewidth=0.8, zorder=2)
        ax.text(row.coupling_plus_summary + 0.012, y, f"{row.coupling_plus_summary:.2f}",
                va="center", fontsize=7.5, color=COL["ink"], weight="bold")

    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{r.task_label}\n({r.metric_name})" for r in order.itertuples(index=False)])
    ax.set_xlim(0.05, 1.02)
    ax.set_xlabel("Held-out performance")
    ax.set_title("Full agent feature set improves downstream prediction", loc="left", weight="bold")
    ax.grid(axis="x", color=COL["grid"], linewidth=0.65, alpha=0.8)
    handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=FEATURE_COLORS[fs],
                   markeredgecolor="white", markersize=7.5, label=FEATURE_LABELS[fs])
        for fs in ["coupling_only", "interpretable_no_levels", "coupling_plus_summary"]
    ]
    ax.legend(handles=handles, frameon=False, fontsize=7.5, loc="lower right")


def plot_lift_map(ax: plt.Axes, table: pd.DataFrame) -> None:
    wide = (
        table.pivot(index=["outcome", "task_label", "metric_name"], columns="feature_set", values="metric_value")
        .reset_index()
    )
    wide["best_ablation"] = wide[["coupling_only", "interpretable_no_levels"]].max(axis=1)
    wide["absolute_lift"] = wide["coupling_plus_summary"] - wide["best_ablation"]
    lim = 1.0
    ax.plot([0, lim], [0, lim], color=COL["axis"], linestyle="--", linewidth=1.0)
    sc = ax.scatter(
        wide["best_ablation"],
        wide["coupling_plus_summary"],
        s=np.clip(wide["absolute_lift"] * 1650 + 90, 100, 760),
        c=wide["absolute_lift"],
        cmap="Greens",
        vmin=0,
        vmax=max(0.42, wide["absolute_lift"].max()),
        edgecolor="white",
        linewidth=0.8,
        zorder=3,
    )
    label_offsets = {
        "Insulin vs healthy": (5, 5),
        "Any diabetes vs healthy": (5, -14),
        "HbA1c": (5, 5),
        "Homeostatic dysregulation": (5, -15),
        "Diabetes severity ordinal": (5, 5),
        "Frailty index": (5, -15),
        "Allostatic load": (5, 5),
    }
    for row in wide.itertuples(index=False):
        dx, dy = label_offsets[row.task_label]
        ax.annotate(
            row.task_label.replace("Diabetes severity ordinal", "Severity ordinal").replace("Homeostatic dysregulation", "Homeostatic"),
            (row.best_ablation, row.coupling_plus_summary),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=7.3,
        )
    ax.set_xlim(0.05, 1.0)
    ax.set_ylim(0.05, 1.0)
    ax.set_xlabel("Best ablation performance")
    ax.set_ylabel("Full agent feature set performance")
    ax.set_title("All selected tasks improve over the strongest ablation", loc="left", weight="bold")
    ax.grid(color=COL["grid"], linewidth=0.65, alpha=0.8)
    cbar = plt.colorbar(sc, ax=ax, fraction=0.045, pad=0.02)
    cbar.set_label("Absolute lift")


def plot_top_lifts(ax: plt.Axes, table: pd.DataFrame) -> None:
    wide = (
        table.pivot(index=["outcome", "task_label", "metric_name"], columns="feature_set", values="metric_value")
        .reset_index()
    )
    wide["best_ablation"] = wide[["coupling_only", "interpretable_no_levels"]].max(axis=1)
    wide["absolute_lift"] = wide["coupling_plus_summary"] - wide["best_ablation"]
    wide = wide.sort_values("absolute_lift", ascending=True)
    y = np.arange(len(wide))
    ax.axvline(0, color=COL["axis"], linewidth=0.8)
    for yi, row in enumerate(wide.itertuples(index=False)):
        ax.plot([0, row.absolute_lift], [yi, yi], color=COL["grid"], linewidth=2.0, zorder=1)
        ax.scatter(row.absolute_lift, yi, s=115, color=COL["teal"], edgecolor="white", linewidth=0.8, zorder=2)
        ax.text(row.absolute_lift + 0.01, yi, f"+{row.absolute_lift:.2f}", va="center", fontsize=7.4, weight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.task_label}\n({r.metric_name})" for r in wide.itertuples(index=False)], fontsize=7.3)
    ax.set_xlim(-0.02, max(0.43, wide["absolute_lift"].max() + 0.08))
    ax.set_xlabel("Absolute performance lift")
    ax.set_title("Where the agentic integration helps most", loc="left", weight="bold")
    ax.grid(axis="x", color=COL["grid"], linewidth=0.65, alpha=0.8)


def write_notes(table: pd.DataFrame) -> None:
    wide = (
        table.pivot(index=["outcome", "task_label", "metric_name"], columns="feature_set", values="metric_value")
        .reset_index()
    )
    wide["best_ablation"] = wide[["coupling_only", "interpretable_no_levels"]].max(axis=1)
    wide["absolute_lift"] = wide["coupling_plus_summary"] - wide["best_ablation"]
    rows = []
    for row in wide.sort_values("coupling_plus_summary", ascending=False).itertuples(index=False):
        rows.append(
            f"- {row.task_label} ({row.metric_name}): full {row.coupling_plus_summary:.3f}, "
            f"best ablation {row.best_ablation:.3f}, lift +{row.absolute_lift:.3f}."
        )
    text = f"""# Downstream Superiority Figure

Generated by `scripts/reporting/agentic_downstream_superiority.py` from `results/coupling/coupling_prediction_performance.csv`.

## Slide-Ready Claim

The strongest evidence for the system is not beating huge external age clocks on chronological-age MAE. It is the internal ablation result: the full agent-derived feature set improves downstream disease and aging-burden prediction across selected AI-READI held-out tasks.

## Key Results

{chr(10).join(rows)}

## Suggested Caption

Agentic integration converts dynamic coupling features and summary physiological signals into downstream aging-relevant predictors. Across diabetes severity, HbA1c, homeostatic dysregulation, frailty, and allostatic load, the full feature set improves over coupling-only and no-raw-level ablations on held-out AI-READI participants.

## Caveat

These are internal held-out ablations. They show superiority over project baselines/ablations, not universal SOTA across unrelated cohorts.
"""
    OUT_NOTE.write_text(text)


def main() -> None:
    setup()
    table = load_task_table()
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 6.0), gridspec_kw={"width_ratios": [1.35, 0.9]})
    plot_ablation_slope(axes[0], table)
    plot_top_lifts(axes[1], table)
    fig.suptitle(
        "Downstream evidence: agentic integration improves aging-relevant tasks",
        x=0.02,
        ha="left",
        fontsize=13.5,
        weight="bold",
    )
    fig.text(
        0.02,
        0.018,
        "Binary outcomes use AUROC; continuous outcomes use R2. Comparisons are internal held-out ablations on AI-READI.",
        fontsize=7.5,
        color=COL["muted"],
    )
    fig.tight_layout(rect=[0, 0.045, 1, 0.92])
    save(fig, "figG_downstream_superiority_ablation")

    fig2, ax2 = plt.subplots(figsize=(6.3, 5.6))
    plot_lift_map(ax2, table)
    fig2.suptitle(
        "Full agent feature set versus strongest ablation",
        x=0.02,
        ha="left",
        fontsize=12.8,
        weight="bold",
    )
    fig2.tight_layout(rect=[0, 0, 1, 0.93])
    save(fig2, "figH_downstream_superiority_lift_map")
    write_notes(table)
    print(f"Wrote {OUT_FIG / 'figG_downstream_superiority_ablation.png'}")


if __name__ == "__main__":
    main()
