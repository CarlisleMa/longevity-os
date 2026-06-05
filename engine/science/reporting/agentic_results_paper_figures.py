#!/usr/bin/env python3
"""Paper-style figures for the agentic aging-clock result section.

Visual design is inspired by common aging-clock papers: predicted-vs-age
calibration panels, age-gap heatmaps, concordance matrices, forest/dot
association views, and control curves. The script avoids bar plots.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

from scripts.config import result_path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
OUT = ROOT / "docs" / "reports" / "agentic_results" / "paper_style_figures"


COL = {
    "ink": "#111827",
    "muted": "#667085",
    "grid": "#D8DEE8",
    "blue": "#0072B2",
    "sky": "#56B4E9",
    "teal": "#009E73",
    "orange": "#E69F00",
    "verm": "#D55E00",
    "purple": "#6F5AA7",
    "gray": "#8A94A6",
}


FAMILY_COLORS = {
    "Clinical/system clocks": COL["blue"],
    "Functional time-series clocks": COL["teal"],
    "Pretrained imaging clocks": COL["orange"],
    "Pretrained signal clocks": "#4E9F3D",
    "Multimodal baseline": COL["purple"],
}


DISPLAY_NAMES = {
    "immune_inflammatory": "Immune /\ninflammatory",
    "metabolic": "Metabolic",
    "renal": "Renal",
    "hepatic": "Hepatic",
    "cardiovascular": "Cardiovascular",
    "hematologic": "Hematologic",
    "cognitive": "Cognitive",
    "circadian": "Circadian",
    "cgm_metabolic": "CGM\nmetabolic",
    "autonomic": "Autonomic",
    "sleep": "Sleep",
    "physical": "Physical",
    "environmental": "Environment",
    "retinal": "Retinal",
    "cardiac": "Cardiac",
    "retinal_image": "Retinal image",
    "cardiac_ecg": "ECG/cardiac",
    "multimodal_static": "Multimodal static",
    "unified_age_gap_stack": "Age-gap stack",
}


AGE_GAP_ORDER = [
    "immune_inflammatory_age_accel",
    "hematologic_age_accel",
    "metabolic_age_accel",
    "cgm_metabolic_age_accel",
    "renal_age_accel",
    "hepatic_age_accel",
    "cardiovascular_age_accel",
    "autonomic_age_accel",
    "sleep_age_accel",
    "physical_age_accel",
    "circadian_age_accel",
    "cognitive_age_accel",
    "environmental_age_accel",
    "retinal_age_accel",
    "cardiac_age_accel",
]


def pretty_clock(name: str) -> str:
    base = name.replace("_age_accel", "")
    return DISPLAY_NAMES.get(base, base.replace("_", "\n").title())


def setup() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "font.family": "DejaVu Sans",
            "font.size": 9,
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


def save(fig: plt.Figure, name: str) -> None:
    for ext in ["png", "pdf", "svg"]:
        fig.savefig(OUT / f"{name}.{ext}", dpi=300, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def load_perf() -> pd.DataFrame:
    path = ROOT / "docs" / "reports" / "agentic_results" / "tables" / "clock_performance_merged.csv"
    if not path.exists():
        raise FileNotFoundError("Run scripts/reporting/agentic_results_analysis.py first")
    return pd.read_csv(path)


def regression_panel(ax, df: pd.DataFrame, y_col: str, title: str, color: str) -> None:
    d = df.copy()
    if "split" in d.columns:
        d = d[d["split"].astype(str).eq("test")]
    elif "recommended_split" in d.columns:
        d = d[d["recommended_split"].astype(str).eq("test")]
    d = d[["age", y_col]].dropna()
    x = d["age"].to_numpy(float)
    y = d[y_col].to_numpy(float)
    if len(d) > 5:
        xy = np.vstack([x, y])
        try:
            dens = gaussian_kde(xy)(xy)
        except Exception:
            dens = np.ones_like(x)
    else:
        dens = np.ones_like(x)
    order = np.argsort(dens)
    x, y, dens = x[order], y[order], dens[order]

    ax.scatter(x, y, c=dens, cmap="viridis", s=16, alpha=0.82, linewidths=0)
    lo = min(np.nanmin(x), np.nanmin(y)) - 2
    hi = max(np.nanmax(x), np.nanmax(y)) + 2
    ax.plot([lo, hi], [lo, hi], color=COL["gray"], linewidth=1.0, linestyle="--")
    if len(x) > 1:
        z = np.polyfit(x, y, 1)
        xx = np.linspace(lo, hi, 100)
        ax.plot(xx, z[0] * xx + z[1], color=color, linewidth=1.8)
    mae = np.mean(np.abs(y - x))
    ss_res = np.sum((y - x) ** 2)
    ss_tot = np.sum((x - x.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot
    r = np.corrcoef(x, y)[0, 1]
    ax.text(0.04, 0.94, f"n={len(x)}\nMAE={mae:.2f}y\nR²={r2:.2f}, r={r:.2f}",
            transform=ax.transAxes, va="top", ha="left", fontsize=8,
            bbox=dict(facecolor="white", edgecolor=COL["grid"], boxstyle="round,pad=0.25"))
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_title(title, loc="left", weight="bold")
    ax.set_xlabel("Chronological age")
    ax.set_ylabel("Predicted age")
    ax.grid(color=COL["grid"], linewidth=0.6, alpha=0.7)


def fig_clock_calibration() -> None:
    fm = pd.read_parquet(result_path("feature_matrix.parquet"))
    retinal = pd.read_parquet(result_path("retinal_age_accel.parquet"))
    cardiac = pd.read_parquet(result_path("cardiac_age_accel.parquet"))
    multi = pd.read_parquet(result_path("multimodal_clock_age_accel.parquet")).join(fm[["recommended_split"]])
    age_accel = pd.read_parquet(result_path("age_accel.parquet")).join(fm[["recommended_split"]])

    fig, axes = plt.subplots(2, 2, figsize=(9.5, 8.5))
    regression_panel(axes[0, 0], retinal, "retinal_predicted_age", "Retinal image clock", COL["orange"])
    regression_panel(axes[0, 1], cardiac, "cardiac_predicted_age", "ECG/cardiac clock", "#4E9F3D")
    regression_panel(axes[1, 0], age_accel.reset_index().rename(columns={"cardiovascular_predicted_age": "pred", "recommended_split": "recommended_split"}), "pred", "Clinical cardiovascular clock", COL["blue"])
    regression_panel(axes[1, 1], multi.reset_index(), "multi_predicted_age", "Multimodal static clock", COL["purple"])
    fig.suptitle("Clock calibration: predicted age versus chronological age on held-out test participants",
                 x=0.02, ha="left", fontsize=14, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save(fig, "figA_clock_calibration_scatter")


def fig_clock_landscape() -> None:
    perf = load_perf().copy()
    perf = perf[np.isfinite(perf["mae"]) & np.isfinite(perf["r_squared"])]
    perf["label"] = perf["clock_name"].str.replace("_", " ").str.title()
    fig, ax = plt.subplots(figsize=(8.3, 5.8))

    for fam, d in perf.groupby("family"):
        ax.scatter(
            d["mae"],
            d["r_squared"],
            s=np.clip((d["n_features"].fillna(10).to_numpy() + 3) * 18, 90, 430),
            color=FAMILY_COLORS.get(fam, COL["gray"]),
            alpha=0.82,
            edgecolor="white",
            linewidth=0.8,
            label=fam,
        )
    label_set = {
        "multimodal_static",
        "retinal_image",
        "cardiovascular",
        "cardiac_ecg",
        "circadian",
        "unified_age_gap_stack",
    }
    for row in perf.itertuples(index=False):
        if row.clock_name in label_set:
            ax.annotate(
                DISPLAY_NAMES.get(row.clock_name, row.label.replace("Static", "static").replace("Image", "image").replace("Age Gap Stack", "age-gap stack")),
                (row.mae, row.r_squared),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8,
            )
    ax.invert_xaxis()
    ax.set_xlabel("Test MAE, years (left is better)")
    ax.set_ylabel("Test R² (higher is better)")
    ax.set_title("Clock benchmark landscape: performance, modality family, and feature scale", loc="left", weight="bold")
    ax.grid(color=COL["grid"], linewidth=0.65, alpha=0.75)
    ax.legend(
        frameon=False,
        fontsize=8,
        loc="upper left",
        bbox_to_anchor=(0.0, -0.18),
        ncol=2,
        handletextpad=0.7,
        columnspacing=1.3,
    )
    fig.subplots_adjust(bottom=0.26)
    save(fig, "figB_clock_benchmark_landscape")


def fig_agegap_heatmap() -> None:
    sub = pd.read_csv(result_path("aging_subtypes.csv"))
    accel_cols = [c for c in AGE_GAP_ORDER if c in sub.columns]
    names = [pretty_clock(c) for c in accel_cols]
    z = sub[accel_cols].sub(sub[accel_cols].mean()).div(sub[accel_cols].std(ddof=0))
    z = pd.concat([sub[["cluster"]], z], axis=1)
    means = z.groupby("cluster")[accel_cols].mean().sort_index()
    sizes = sub.groupby("cluster").size()
    labels = [f"Subtype {i}\n(n={sizes.loc[i]:,})" for i in means.index]
    lim = float(np.nanpercentile(np.abs(means.values), 98))
    lim = max(0.45, min(1.2, lim))

    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.6), gridspec_kw={"width_ratios": [1.1, 1.6]})
    im = axes[0].imshow(means.values, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
    axes[0].set_yticks(np.arange(len(labels)))
    axes[0].set_yticklabels(labels)
    axes[0].set_xticks(np.arange(len(names)))
    axes[0].set_xticklabels(names, rotation=45, ha="right", fontsize=7)
    axes[0].set_title("Subtype-average age-gap profiles", loc="left", weight="bold")
    cbar = fig.colorbar(im, ax=axes[0], fraction=0.04, pad=0.02)
    cbar.set_label("Mean z-scored age gap")

    mat = pd.read_csv(result_path("concordance_matrix.csv"), index_col=0)
    order = [c.replace("_age_accel", "") for c in AGE_GAP_ORDER if c.replace("_age_accel", "") in mat.columns]
    im2 = axes[1].imshow(mat.loc[order, order], cmap="RdBu_r", vmin=-1, vmax=1)
    axes[1].set_xticks(np.arange(len(order)))
    axes[1].set_yticks(np.arange(len(order)))
    axes[1].set_xticklabels([pretty_clock(o) for o in order], rotation=45, ha="right", fontsize=6.5)
    axes[1].set_yticklabels([pretty_clock(o) for o in order], fontsize=6.5)
    axes[1].set_title("Cross-clock age-gap concordance", loc="left", weight="bold")
    cbar2 = fig.colorbar(im2, ax=axes[1], fraction=0.04, pad=0.02)
    cbar2.set_label("Pearson r")
    fig.suptitle("Aging is multidimensional: organ/system age gaps form profiles, not one axis",
                 x=0.02, ha="left", fontsize=13.5, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save(fig, "figC_agegap_profiles_and_concordance")


def fig_diabetes_agegap_trajectory() -> None:
    grad = pd.read_csv(result_path("diabetes_gradient.csv")).copy()
    group_cols = ["mean_Healthy", "mean_Pre-diabetes", "mean_Oral med", "mean_Insulin"]
    group_labels = ["Healthy", "Pre-diabetes", "Oral med", "Insulin"]
    grad["delta_insulin_healthy"] = grad["mean_Insulin"] - grad["mean_Healthy"]
    grad = grad.sort_values("delta_insulin_healthy", ascending=False)

    heat = grad.set_index("clock")[group_cols]
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 6.3), gridspec_kw={"width_ratios": [1.05, 0.95]})
    lim = max(1.5, float(np.nanpercentile(np.abs(heat.values), 95)))
    im = axes[0].imshow(heat.values, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
    axes[0].set_yticks(np.arange(len(heat)))
    axes[0].set_yticklabels([pretty_clock(c).replace("\n", " ") for c in heat.index], fontsize=7.5)
    axes[0].set_xticks(np.arange(len(group_cols)))
    axes[0].set_xticklabels(group_labels, rotation=25, ha="right")
    axes[0].set_title("Mean age gap across glycemic severity", loc="left", weight="bold")
    axes[0].set_xlabel("Clinical group")
    cbar = fig.colorbar(im, ax=axes[0], fraction=0.045, pad=0.02)
    cbar.set_label("Mean age gap (years)")

    top = grad.head(10).sort_values("delta_insulin_healthy")
    y = np.arange(len(top))
    for i, (_, row) in enumerate(top.iterrows()):
        xs = [row[c] for c in group_cols]
        axes[1].plot(xs, np.repeat(i, 4), color=COL["grid"], linewidth=1.4, zorder=1)
        axes[1].scatter(xs, np.repeat(i, 4), c=[COL["blue"], COL["sky"], COL["orange"], COL["verm"]],
                        s=[34, 34, 42, 48], edgecolor="white", linewidth=0.7, zorder=2)
    axes[1].axvline(0, color=COL["gray"], linewidth=0.8, linestyle="--")
    axes[1].set_yticks(y)
    axes[1].set_yticklabels([pretty_clock(c).replace("\n", " ") for c in top["clock"]], fontsize=8)
    axes[1].set_xlabel("Mean age gap (years)")
    axes[1].set_title("Largest severity trajectories", loc="left", weight="bold")
    axes[1].grid(axis="x", color=COL["grid"], linewidth=0.65, alpha=0.75)
    legend = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=COL["blue"], markeredgecolor="white", markersize=6, label="Healthy"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=COL["sky"], markeredgecolor="white", markersize=6, label="Pre-diabetes"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=COL["orange"], markeredgecolor="white", markersize=6, label="Oral med"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=COL["verm"], markeredgecolor="white", markersize=6, label="Insulin"),
    ]
    axes[1].legend(handles=legend, frameon=False, fontsize=7.5, loc="lower right")

    fig.suptitle("Age-gap residuals recover disease-relevant heterogeneity without using disease labels",
                 x=0.02, ha="left", fontsize=13.5, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save(fig, "figD_diabetes_agegap_trajectory")


def feature_family(feature: str) -> str:
    if "glucose_hr" in feature:
        return "Glucose-HR"
    if "glucose_activity" in feature:
        return "Glucose-activity"
    if "entropy" in feature:
        return "Glucose entropy"
    if "hr_activity" in feature:
        return "HR-activity"
    return "Other"


def fig_coupling_association_map() -> None:
    atlas = pd.read_csv(result_path("coupling_atlas.csv")).copy()
    atlas["neglog10_fdr"] = -np.log10(atlas["p_adjusted_severity_fdr"].clip(lower=1e-300))
    atlas["family"] = atlas["feature"].map(feature_family)
    colors = {
        "Glucose-HR": COL["blue"],
        "Glucose-activity": COL["orange"],
        "Glucose entropy": COL["teal"],
        "HR-activity": COL["purple"],
        "Other": COL["gray"],
    }

    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.9), gridspec_kw={"width_ratios": [1.25, 1]})
    for fam, d in atlas.groupby("family"):
        axes[0].scatter(
            d["healthy_vs_insulin_d"],
            d["neglog10_fdr"],
            s=np.clip(np.abs(d["severity_spearman_rho"]) * 550 + 30, 35, 220),
            color=colors.get(fam, COL["gray"]),
            alpha=0.82,
            edgecolor="white",
            linewidth=0.7,
            label=fam,
        )
    axes[0].axvline(0, color=COL["gray"], linestyle="--", linewidth=0.8)
    axes[0].set_xlabel("Effect size: Healthy vs insulin-dependent (Cohen's d)")
    axes[0].set_ylabel("-log10(FDR), age/site-adjusted severity")
    axes[0].set_title("Coupling atlas association map", loc="left", weight="bold")
    axes[0].legend(frameon=False, fontsize=8)
    axes[0].grid(color=COL["grid"], linewidth=0.65, alpha=0.75)
    top_features = {
        "glucose_hr_awake_r": ("awake Glu-HR", (10, 14)),
        "glucose_activity_spearman_r": ("Glu-activity rank", (10, 12)),
    }
    top = atlas[atlas["feature"].isin(top_features)]
    short = {
        "glucose_hr_awake_r": "awake Glu-HR",
        "glucose_hr_spearman_r": "Glu-HR rank",
        "glucose_hr_partial_r_activity_sleep": "Glu-HR partial",
        "glucose_hr_zero_lag_r": "Glu-HR 0-lag",
        "glucose_activity_spearman_r": "Glu-activity rank",
    }
    for row in top.itertuples(index=False):
        label, offset = top_features[row.feature]
        axes[0].annotate(label, (row.healthy_vs_insulin_d, row.neglog10_fdr),
                         xytext=offset, textcoords="offset points", fontsize=7.5)
    axes[0].set_xlim(-0.33, 0.68)

    pred = pd.read_csv(result_path("coupling_prediction_performance.csv"))
    p = pred[pred["feature_set"].isin(["coupling_only", "interpretable_no_levels", "coupling_plus_summary"])].copy()
    p = p[p["outcome"].isin(["insulin_vs_healthy", "hba1c", "frailty_index", "allostatic_load"])]
    p["metric"] = np.where(p["task"].eq("binary"), p["auroc"], p["r2"])
    p["outcome_label"] = p["outcome"].map({
        "insulin_vs_healthy": "Insulin AUROC",
        "hba1c": "HbA1c R²",
        "frailty_index": "Frailty R²",
        "allostatic_load": "Allostatic R²",
    })
    xmap = {o: i for i, o in enumerate(["Insulin AUROC", "HbA1c R²", "Frailty R²", "Allostatic R²"])}
    ymap = {"coupling_only": 2, "interpretable_no_levels": 1, "coupling_plus_summary": 0}
    axes[1].scatter(
        [xmap[o] for o in p["outcome_label"]],
        [ymap[f] for f in p["feature_set"]],
        s=p["metric"] * 650,
        c=p["metric"],
        cmap="viridis",
        vmin=0,
        vmax=1,
        edgecolor="white",
        linewidth=0.7,
    )
    for row in p.itertuples(index=False):
        axes[1].text(xmap[row.outcome_label], ymap[row.feature_set], f"{row.metric:.2f}",
                     ha="center", va="center", fontsize=7.5, color="white", weight="bold")
    axes[1].set_xticks(range(4))
    axes[1].set_xticklabels(["Insulin\nAUROC", "HbA1c\nR²", "Frailty\nR²", "Allostatic\nR²"])
    axes[1].set_yticks([0, 1, 2])
    axes[1].set_yticklabels(["Coupling +\nsummary", "No raw\nlevels", "Coupling\nonly"])
    axes[1].set_title("Prediction value matrix", loc="left", weight="bold")
    axes[1].set_xlim(-0.6, 3.6)
    axes[1].set_ylim(-0.6, 2.6)
    axes[1].grid(color=COL["grid"], linewidth=0.65, alpha=0.75)

    fig.suptitle("Dynamic physiology result: coupling features behave like aging/resilience phenotypes",
                 x=0.02, ha="left", fontsize=13.5, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save(fig, "figD_coupling_association_and_prediction_map")


def fig_foundation_controls_dotline() -> None:
    seq = pd.read_csv(ROOT / "foundation_jepa/sequence" / "artifacts" / "next_stage" / "summary.csv")
    configs = [
        "full_joint",
        "static_only_joint",
        "shuffle_sequences_joint",
        "drop_clinical_joint",
        "sequence_only_joint",
        "shuffle_all_joint",
    ]
    s = (
        seq[seq["config"].isin(configs)]
        .groupby("config")
        .agg(mean=("test_age_mae", "mean"), sd=("test_age_mae", "std"))
        .reindex(configs)
        .reset_index()
    )
    label = {
        "full_joint": "Full joint",
        "static_only_joint": "Static only",
        "shuffle_sequences_joint": "Shuffle sequences",
        "drop_clinical_joint": "Drop clinical",
        "sequence_only_joint": "Sequence only",
        "shuffle_all_joint": "Shuffle all",
    }
    s["label"] = s["config"].map(label)

    win = pd.read_csv(ROOT / "foundation_jepa/window" / "artifacts" / "horizon_suite" / "summary.csv")
    w = win.groupby(["horizon_minutes", "control"])["test_jepa"].agg(["mean", "std"]).reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.7), gridspec_kw={"width_ratios": [0.95, 1.15]})
    y = np.arange(len(s))[::-1]
    axes[0].errorbar(s["mean"], y, xerr=s["sd"].fillna(0), fmt="o", color=COL["purple"],
                     ecolor=COL["grid"], elinewidth=2, capsize=3, markersize=7)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(s["label"])
    axes[0].set_xlabel("Test age MAE (years)")
    axes[0].set_title("Sequence-level endpoint check", loc="left", weight="bold")
    axes[0].grid(axis="x", color=COL["grid"], linewidth=0.65, alpha=0.75)
    axes[0].invert_xaxis()
    axes[0].text(0.02, 0.04, "Static-only ≈ full joint;\nsequence-only is weak for age.",
                 transform=axes[0].transAxes, fontsize=8.5, color=COL["muted"],
                 bbox=dict(facecolor="white", edgecolor=COL["grid"], boxstyle="round,pad=0.25"))

    control_colors = {"aligned": COL["teal"], "wrong_day": COL["orange"], "participant_shuffle": COL["verm"]}
    for control, d in w.groupby("control"):
        d = d.sort_values("horizon_minutes")
        axes[1].plot(d["horizon_minutes"], d["mean"], marker="o", linewidth=2.2,
                     color=control_colors[control], label=control.replace("_", " "))
        axes[1].fill_between(d["horizon_minutes"], d["mean"] - d["std"], d["mean"] + d["std"],
                             color=control_colors[control], alpha=0.12, linewidth=0)
    axes[1].set_xlabel("Prediction horizon (min)")
    axes[1].set_ylabel("Test JEPA loss")
    axes[1].set_title("Window-level temporal control", loc="left", weight="bold")
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].grid(color=COL["grid"], linewidth=0.65, alpha=0.75)

    fig.suptitle("Foundation-model handoff: agent-generated controls separate static shortcuts from temporal alignment",
                 x=0.02, ha="left", fontsize=13.5, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save(fig, "figE_foundation_model_controls")


def main() -> None:
    setup()
    fig_clock_calibration()
    fig_clock_landscape()
    fig_agegap_heatmap()
    fig_diabetes_agegap_trajectory()
    fig_coupling_association_map()
    fig_foundation_controls_dotline()
    print(f"Wrote paper-style figures to {OUT}")


if __name__ == "__main__":
    main()
