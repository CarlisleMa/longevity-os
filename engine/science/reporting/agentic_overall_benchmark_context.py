#!/usr/bin/env python3
"""Overall agent benchmark context figure.

The figure separates fair internal AI-READI held-out comparisons from
external published aging-clock reference points. External references are
context only because they are not trained or evaluated on the same cohort.
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
OUT_NOTE = ROOT / "docs" / "reports" / "agentic_results" / "overall_agent_benchmark_notes.md"


COL = {
    "ink": "#111827",
    "muted": "#667085",
    "grid": "#D8DEE8",
    "axis": "#B8C2D1",
    "blue": "#0072B2",
    "amber": "#E69F00",
    "teal": "#009E73",
    "pink": "#CC79A7",
    "verm": "#D55E00",
    "purple": "#6F5AA7",
    "gray": "#8A94A6",
}


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


def load_clock_context() -> pd.DataFrame:
    perf = pd.read_csv(OUT_TABLE / "clock_performance_merged.csv")
    key = perf.set_index("clock_name")
    rows = [
        {
            "label": "Published retinal DL, UKB",
            "group": "External reference",
            "metric": "MAE",
            "mae": 3.55,
            "r2": np.nan,
            "source": "Zhu et al., British Journal of Ophthalmology / UK Biobank",
            "note": "External cohort; context only",
        },
        {
            "label": "Published AI-ECG heart age",
            "group": "External reference",
            "metric": "MAE",
            "mae": 5.80,
            "r2": 0.70,
            "source": "AI ECG-heart age 12-lead DNN",
            "note": "External cohort; context only",
        },
    ]
    for name, label, group in [
        ("multimodal_static", "AI-READI multimodal static", "AI-READI held-out"),
        ("retinal_image", "AI-READI retinal image", "AI-READI held-out"),
        ("cardiovascular", "AI-READI cardiovascular clinical", "AI-READI held-out"),
        ("cardiac_ecg", "AI-READI ECG/cardiac", "AI-READI held-out"),
    ]:
        row = key.loc[name]
        rows.append(
            {
                "label": label,
                "group": group,
                "metric": "MAE",
                "mae": float(row["mae"]),
                "r2": float(row["r_squared"]),
                "source": "This project",
                "note": "Same AI-READI split",
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUT_TABLE / "overall_age_clock_context.csv", index=False)
    return out


def load_downstream_matrix() -> pd.DataFrame:
    perf = pd.read_csv(result_path("coupling_prediction_performance.csv"))
    outcomes = [
        ("insulin_vs_healthy", "Insulin\nAUROC"),
        ("any_diabetes_vs_healthy", "Any diabetes\nAUROC"),
        ("hba1c", "HbA1c\nR2"),
        ("homeostatic_dysregulation", "Homeostatic\nR2"),
        ("study_group_ordinal", "Study group\nR2"),
        ("frailty_index", "Frailty\nR2"),
    ]
    feature_sets = [
        ("coupling_only", "Coupling only"),
        ("interpretable_no_levels", "No raw levels"),
        ("coupling_plus_summary", "Coupling + summary"),
    ]
    rows = []
    for fs, fs_label in feature_sets:
        for outcome, outcome_label in outcomes:
            d = perf[(perf["feature_set"].eq(fs)) & (perf["outcome"].eq(outcome))].iloc[0]
            if d["task"] == "binary":
                metric = float(d["auroc"])
                metric_name = "AUROC"
            else:
                metric = float(d["r2"])
                metric_name = "R2"
            rows.append(
                {
                    "feature_set": fs,
                    "feature_set_label": fs_label,
                    "outcome": outcome,
                    "outcome_label": outcome_label,
                    "metric_name": metric_name,
                    "metric_value": metric,
                    "n_test": int(d["n_test"]),
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(OUT_TABLE / "overall_downstream_task_matrix.csv", index=False)
    return out


def plot_age_context(ax: plt.Axes, age: pd.DataFrame) -> None:
    order = [
        "Published retinal DL, UKB",
        "Published AI-ECG heart age",
        "AI-READI multimodal static",
        "AI-READI retinal image",
        "AI-READI cardiovascular clinical",
        "AI-READI ECG/cardiac",
    ]
    age = age.set_index("label").loc[order].reset_index()
    y = np.arange(len(age))[::-1]
    colors = {
        "AI-READI multimodal static": COL["purple"],
        "AI-READI retinal image": COL["amber"],
        "AI-READI cardiovascular clinical": COL["blue"],
        "AI-READI ECG/cardiac": COL["teal"],
    }
    for i, row in enumerate(age.itertuples(index=False)):
        yi = y[i]
        if row.group == "External reference":
            ax.scatter(row.mae, yi, s=105, marker="D", facecolor="white", edgecolor=COL["gray"], linewidth=1.8, zorder=3)
            ax.text(row.mae + 0.13, yi, "external", va="center", fontsize=7.2, color=COL["muted"])
        else:
            ax.scatter(row.mae, yi, s=140, marker="o", color=colors[row.label], edgecolor="white", linewidth=0.9, zorder=3)
            ax.text(row.mae + 0.13, yi, f"R2={row.r2:.2f}", va="center", fontsize=7.2, color=COL["muted"])
    ax.set_yticks(y)
    ax.set_yticklabels(age["label"])
    ax.set_xlabel("Age prediction MAE, years (lower is better)")
    ax.set_title("Age-clock context", loc="left", weight="bold")
    ax.set_xlim(3.0, 9.6)
    ax.grid(axis="x", color=COL["grid"], linewidth=0.65, alpha=0.8)
    ax.text(
        0.02,
        0.03,
        "Hollow diamonds: external context only",
        transform=ax.transAxes,
        fontsize=7.5,
        color=COL["muted"],
        ha="left",
        va="bottom",
    )


def plot_downstream_matrix(ax: plt.Axes, mat: pd.DataFrame) -> None:
    x_order = ["Insulin\nAUROC", "Any diabetes\nAUROC", "HbA1c\nR2", "Homeostatic\nR2", "Study group\nR2", "Frailty\nR2"]
    y_order = ["Coupling only", "No raw levels", "Coupling + summary"]
    xmap = {x: i for i, x in enumerate(x_order)}
    ymap = {y: i for i, y in enumerate(y_order[::-1])}

    xs = [xmap[x] for x in mat["outcome_label"]]
    ys = [ymap[y] for y in mat["feature_set_label"]]
    vals = mat["metric_value"].to_numpy(float)
    ax.scatter(
        xs,
        ys,
        s=np.clip(vals * 620, 55, 600),
        c=vals,
        cmap="viridis",
        vmin=0,
        vmax=1,
        edgecolor="white",
        linewidth=0.8,
    )
    for row in mat.itertuples(index=False):
        ax.text(
            xmap[row.outcome_label],
            ymap[row.feature_set_label],
            f"{row.metric_value:.2f}",
            ha="center",
            va="center",
            fontsize=7.2,
            color="white",
            weight="bold",
        )
    ax.set_xticks(range(len(x_order)))
    ax.set_xticklabels(x_order)
    ax.set_yticks(range(len(y_order)))
    ax.set_yticklabels(y_order[::-1])
    ax.set_xlim(-0.55, len(x_order) - 0.45)
    ax.set_ylim(-0.55, len(y_order) - 0.45)
    ax.grid(color=COL["grid"], linewidth=0.65, alpha=0.8)
    ax.set_title("Downstream task matrix (AI-READI held-out)", loc="left", weight="bold")
    ax.text(
        0.0,
        -0.22,
        "Binary outcomes use AUROC; continuous outcomes use R2.",
        transform=ax.transAxes,
        fontsize=7.3,
        color=COL["muted"],
        ha="left",
        va="top",
    )


def write_notes() -> None:
    text = """# Overall Agent Benchmark Context

Generated by `scripts/reporting/agentic_overall_benchmark_context.py`.

## What This Figure Shows

- Left panel: AI-READI age-clock performance on the project held-out split, with two external published aging-clock reference points for scale only.
- Right panel: fair AI-READI held-out downstream task performance for agent-generated dynamic physiology feature sets.

## Slide-Ready Takeaway

The overall agentic workflow is not only producing clocks; it also produces downstream predictive artifacts. The multimodal static clock is the strongest internal age predictor, while the dynamic physiology layer is strongest for diabetes and clinical-burden endpoints when coupling features are combined with summary features.

## Important Caveat

The external retinal and ECG points are not SOTA claims on AI-READI. They are published reference points from different cohorts, tasks, and model inputs. The defensible comparison is the right-panel internal held-out matrix.

## Key Numbers

- Multimodal static age clock: MAE 5.20 years, R2 0.650.
- Retinal image age clock: MAE 6.03 years, R2 0.527.
- Best narrow clinical age clock: cardiovascular, MAE 8.13 years, R2 0.194.
- Coupling + summary features: insulin-vs-healthy AUROC 0.952; HbA1c R2 0.674; homeostatic dysregulation R2 0.603.

## External Reference Points

- Retinal DL age model in UK Biobank: MAE 3.55 years, r 0.81.
- AI-ECG heart-age DNN: MAE 5.8 years, R2 0.7.
"""
    OUT_NOTE.write_text(text)


def main() -> None:
    setup()
    age = load_clock_context()
    downstream = load_downstream_matrix()
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 6.1), gridspec_kw={"width_ratios": [0.9, 1.35]})
    plot_age_context(axes[0], age)
    plot_downstream_matrix(axes[1], downstream)
    fig.suptitle(
        "Overall agent performance: clocks, residual features, and downstream tasks",
        x=0.02,
        ha="left",
        fontsize=13.5,
        weight="bold",
    )
    fig.text(
        0.02,
        0.015,
        "External reference points are cross-dataset context only; AI-READI downstream matrix is the fair held-out comparison.",
        fontsize=7.5,
        color=COL["muted"],
    )
    fig.tight_layout(rect=[0, 0.06, 1, 0.91])
    save(fig, "figF_overall_agent_benchmark_context")
    write_notes()
    print(f"Wrote {OUT_FIG / 'figF_overall_agent_benchmark_context.png'}")


if __name__ == "__main__":
    main()
