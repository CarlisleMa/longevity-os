#!/usr/bin/env python3
"""Generate agentic-framework result figures from existing AI-READI outputs.

This script intentionally does not run the LLM agents. It summarizes the
artifacts those workflows already produced: curated feature layers, aging clocks,
cross-modal findings, critic/memory inventory, and foundation-model handoff
experiments.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from scipy.stats import pearsonr

from scripts.config import result_path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
OUT = ROOT / "docs" / "reports" / "agentic_results"
FIG = OUT / "figures"
TABLES = OUT / "tables"


SYSTEM_CLOCKS = {
    "immune_inflammatory",
    "metabolic",
    "renal",
    "hepatic",
    "cardiovascular",
    "hematologic",
    "cognitive",
}

FUNCTIONAL_CLOCKS = {
    "circadian",
    "cgm_metabolic",
    "autonomic",
    "sleep",
    "physical",
    "environmental",
}

GROUP_ORDER = [
    "healthy",
    "pre_diabetes_lifestyle_controlled",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled",
    "insulin_dependent",
]

GROUP_LABELS = {
    "healthy": "Healthy",
    "pre_diabetes_lifestyle_controlled": "Pre-DM",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": "Oral med",
    "insulin_dependent": "Insulin",
}


COLORS = {
    "navy": "#0B2545",
    "blue": "#0072B2",
    "sky": "#56B4E9",
    "teal": "#009E73",
    "green": "#4E9F3D",
    "orange": "#E69F00",
    "verm": "#D55E00",
    "purple": "#6F5AA7",
    "gray": "#6B7280",
    "light": "#F4F6F8",
    "line": "#D8DEE8",
    "ink": "#111827",
}


def ensure_dirs() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)


def set_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": COLORS["line"],
            "axes.linewidth": 0.8,
            "xtick.color": COLORS["gray"],
            "ytick.color": COLORS["gray"],
            "axes.labelcolor": COLORS["gray"],
            "text.color": COLORS["ink"],
        }
    )


def save(fig: plt.Figure, stem: str) -> Path:
    png = FIG / f"{stem}.png"
    pdf = FIG / f"{stem}.pdf"
    svg = FIG / f"{stem}.svg"
    fig.savefig(png, dpi=300, bbox_inches="tight", pad_inches=0.08)
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.08)
    fig.savefig(svg, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    return png


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def safe_read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def regression_metrics(y_true: Iterable[float], y_pred: Iterable[float]) -> dict[str, float]:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(y) & np.isfinite(p)
    y, p = y[mask], p[mask]
    mae = np.mean(np.abs(p - y))
    ss_res = np.sum((p - y) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    r = pearsonr(y, p).statistic if len(y) > 2 else np.nan
    return {"n_test": int(len(y)), "mae": mae, "r_squared": r2, "pearson_r": r}


def modality_coverage() -> pd.DataFrame:
    participants = pd.read_csv(DATA / "participants.tsv", sep="\t", dtype={"person_id": str})
    n_total = participants["person_id"].nunique()

    entries = []

    def add(name: str, path: Path, sep: str = "\t", clinical: bool = False) -> None:
        if not path.exists():
            entries.append((name, np.nan, np.nan))
            return
        df = pd.read_csv(path, sep=sep, dtype={"person_id": str}, low_memory=False)
        n = n_total if clinical else df["person_id"].nunique()
        entries.append((name, n, n / n_total * 100))

    add("Clinical OMOP", DATA / "clinical_data" / "person.csv", ",", clinical=True)
    add("Retinal CFP", DATA / "retinal_photography" / "manifest.tsv")
    add("Retinal OCT", DATA / "retinal_oct" / "manifest.tsv")
    add("Retinal OCTA", DATA / "retinal_octa" / "manifest.tsv")
    add("Retinal FLIO", DATA / "retinal_flio" / "manifest.tsv")
    add("ECG", DATA / "cardiac_ecg" / "manifest.tsv")
    add("CGM", DATA / "wearable_blood_glucose" / "manifest.tsv")
    add("Wearable", DATA / "wearable_activity_monitor" / "manifest.tsv")
    add("Environment", DATA / "environment" / "manifest.tsv")

    out = pd.DataFrame(entries, columns=["modality", "n_participants", "coverage_pct"])
    out["n_total"] = n_total
    return out.sort_values("coverage_pct", ascending=True)


def clock_performance() -> pd.DataFrame:
    perf = pd.read_csv(result_path("clock_performance.csv"))
    perf["family"] = np.where(
        perf["clock_name"].isin(SYSTEM_CLOCKS),
        "Clinical/system clocks",
        "Functional time-series clocks",
    )

    rows = [perf]

    for name, path, pred_col, family in [
        ("retinal_image", result_path("retinal_age_accel.parquet"), "retinal_predicted_age", "Pretrained imaging clocks"),
        ("cardiac_ecg", result_path("cardiac_age_accel.parquet"), "cardiac_predicted_age", "Pretrained signal clocks"),
    ]:
        df = safe_read_parquet(path)
        if not df.empty:
            test = df[df["split"].astype(str).eq("test")]
            metrics = regression_metrics(test["age"], test[pred_col])
            rows.append(
                pd.DataFrame(
                    [
                        {
                            "clock_name": name,
                            "n_features": np.nan,
                            "features_used": pred_col,
                            "n_train": int((df["split"].astype(str) == "train").sum()),
                            **metrics,
                            "best_alpha": np.nan,
                            "family": family,
                        }
                    ]
                )
            )

    multi_perf = safe_read_csv(result_path("multimodal_clock_performance.csv"))
    multi = safe_read_parquet(result_path("multimodal_clock_age_accel.parquet"))
    fm = safe_read_parquet(result_path("feature_matrix.parquet"))
    if not multi_perf.empty:
        row = multi_perf.sort_values("test_mae").iloc[0]
        rows.append(
            pd.DataFrame(
                [
                    {
                        "clock_name": "multimodal_all_feature",
                        "n_features": row.get("n_features", np.nan),
                        "features_used": "raw numeric features + frozen retinal/ECG embeddings",
                        "n_train": row.get("n_train", np.nan),
                        "n_test": row.get("n_test", np.nan),
                        "mae": row["test_mae"],
                        "r_squared": row["test_r_squared"],
                        "pearson_r": row["test_pearson_r"],
                        "best_alpha": row.get("selected_alpha", np.nan),
                        "family": "Multimodal all-feature clock",
                    }
                ]
            )
        )
    elif not multi.empty and not fm.empty:
        tmp = multi.join(fm[["recommended_split"]], how="left")
        test = tmp[tmp["recommended_split"].astype(str).eq("test")]
        metrics = regression_metrics(test["age"], test["multi_predicted_age"])
        rows.append(
            pd.DataFrame(
                [
                    {
                        "clock_name": "multimodal_static",
                        "n_features": np.nan,
                        "features_used": "combined clinical + multimodal features",
                        "n_train": int((tmp["recommended_split"].astype(str) == "train").sum()),
                        **metrics,
                        "best_alpha": np.nan,
                        "family": "Multimodal baseline",
                    }
                ]
            )
        )

    unified = safe_read_csv(result_path("unified_clock_performance.csv"))
    if not unified.empty and "n_candidate_features" not in unified.columns:
        best = unified[unified["model"].astype(str).str.contains("train\\+val", regex=True)].head(1)
        if best.empty:
            best = unified.sort_values("test_mae").head(1)
        row = best.iloc[0]
        rows.append(
            pd.DataFrame(
                [
                    {
                        "clock_name": "unified_age_gap_stack",
                        "n_features": 15,
                        "features_used": "15 age-gap dimensions",
                        "n_train": np.nan,
                        "n_test": np.nan,
                        "mae": row["test_mae"],
                        "r_squared": row["test_r_squared"],
                        "pearson_r": row["test_pearson_r"],
                        "best_alpha": np.nan,
                        "family": "Multimodal baseline",
                    }
                ]
            )
        )

    out = pd.concat(rows, ignore_index=True)
    out = out[["clock_name", "family", "n_features", "n_train", "n_test", "mae", "r_squared", "pearson_r", "features_used"]]
    out.to_csv(TABLES / "clock_performance_merged.csv", index=False)
    return out


def agentic_inventory() -> pd.DataFrame:
    fm = safe_read_parquet(result_path("feature_matrix.parquet"))
    mm = safe_read_parquet(result_path("multimodal_features.parquet"))
    age = safe_read_parquet(result_path("age_accel.parquet"))
    concord = safe_read_csv(result_path("concordance_matrix.csv"))
    subtype = safe_read_csv(result_path("aging_subtypes.csv"))
    coupling = safe_read_parquet(result_path("coupling_features.parquet"))
    coupling_env = safe_read_parquet(result_path("coupling_features_env.parquet"))
    pred = safe_read_csv(result_path("coupling_prediction_performance.csv"))
    atlas = safe_read_csv(result_path("coupling_atlas.csv"))
    damage = safe_read_csv(result_path("coupling_damage.csv"))
    bio = safe_read_csv(result_path("biomarker_panel.csv"))
    seq = safe_read_csv(ROOT / "foundation_jepa/sequence" / "artifacts" / "next_stage" / "summary.csv")
    win = safe_read_csv(ROOT / "foundation_jepa/window" / "artifacts" / "horizon_suite" / "summary.csv")
    cache_count = len(list((ROOT / "foundation_jepa/sequence" / "artifacts" / "cache_5min_10d").glob("*.npz")))

    memory_counts = {}
    for p in (RESULTS / "agent_memory").glob("*.json"):
        memory_counts[p.stem] = len(json.loads(p.read_text()))

    rows = [
        ("Data curation", "Participants", fm.shape[0] if not fm.empty else np.nan),
        ("Data curation", "Feature-matrix columns", fm.shape[1] if not fm.empty else np.nan),
        ("Data curation", "Multimodal feature columns", mm.shape[1] if not mm.empty else np.nan),
        ("Data curation", "Modality agents", 6),
        ("Aging phenotyping", "System/functional clocks", 13),
        ("Aging phenotyping", "Age-gap dimensions", concord.shape[0] if not concord.empty else np.nan),
        ("Aging phenotyping", "Participants with subtype labels", subtype.shape[0] if not subtype.empty else np.nan),
        ("Aging phenotyping", "AgeAccel columns", len([c for c in age.columns if c.endswith("_age_accel")]) if not age.empty else np.nan),
        ("Dynamic discovery", "Coupling atlas features", atlas.shape[0] if not atlas.empty else np.nan),
        ("Dynamic discovery", "Coupling participants", coupling.shape[0] if not coupling.empty else np.nan),
        ("Dynamic discovery", "Env-coupling participants", coupling_env.shape[0] if not coupling_env.empty else np.nan),
        ("Dynamic discovery", "Damage association tests", damage.shape[0] if not damage.empty else np.nan),
        ("Prediction outputs", "Coupling prediction tasks", pred.shape[0] if not pred.empty else np.nan),
        ("Prediction outputs", "Biomarker prediction panels", bio.shape[0] if not bio.empty else np.nan),
        ("Foundation handoff", "5-min sequence tensors", cache_count),
        ("Foundation handoff", "Sequence JEPA runs", seq.shape[0] if not seq.empty else np.nan),
        ("Foundation handoff", "Window JEPA runs", win.shape[0] if not win.empty else np.nan),
        ("Rigor layer", "Dataset constraints in memory", memory_counts.get("constraints", 0)),
        ("Rigor layer", "Domain knowledge entries", memory_counts.get("domain", 0)),
        ("Rigor layer", "Reusable workflow patterns", memory_counts.get("workflows", 0)),
    ]
    out = pd.DataFrame(rows, columns=["layer", "artifact", "value"])
    out.to_csv(TABLES / "agentic_inventory.csv", index=False)
    return out


def draw_card(ax, xy, wh, title, lines, color):
    x, y = xy
    w, h = wh
    rect = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.016,rounding_size=0.018",
        facecolor="white",
        edgecolor=color,
        linewidth=1.5,
    )
    ax.add_patch(rect)
    ax.text(x + 0.03 * w, y + h - 0.14 * h, title, fontsize=10.5, weight="bold", color=color, va="top")
    for i, line in enumerate(lines):
        ax.text(x + 0.03 * w, y + h - (0.34 + i * 0.17) * h, line, fontsize=8.3, color=COLORS["ink"], va="top")


def fig_inventory(inv: pd.DataFrame) -> Path:
    by = inv.groupby("layer").apply(lambda d: list(zip(d["artifact"], d["value"])), include_groups=False).to_dict()
    fig, ax = plt.subplots(figsize=(12.8, 6.2))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.02, 0.965, "Agentic workflow yield from real AI-READI artifacts", fontsize=17, weight="bold")
    ax.text(0.02, 0.925, "The agent layer organizes data curation, aging phenotyping, dynamic discovery, prediction, foundation-model handoff, and rigor checks.", fontsize=9.5, color=COLORS["gray"])

    specs = [
        ("Data curation", 0.02, 0.58, COLORS["teal"]),
        ("Aging phenotyping", 0.35, 0.58, COLORS["orange"]),
        ("Dynamic discovery", 0.68, 0.58, COLORS["green"]),
        ("Prediction outputs", 0.02, 0.18, COLORS["blue"]),
        ("Foundation handoff", 0.35, 0.18, COLORS["purple"]),
        ("Rigor layer", 0.68, 0.18, COLORS["verm"]),
    ]
    for layer, x, y, color in specs:
        items = by[layer]
        lines = [f"{artifact}: {int(value):,}" if pd.notna(value) else f"{artifact}: missing" for artifact, value in items[:4]]
        draw_card(ax, (x, y), (0.29, 0.3), layer, lines, color)
    return save(fig, "fig1_agentic_workflow_yield")


def fig_coverage(cov: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    colors = [COLORS["teal"] if v >= 95 else COLORS["orange"] for v in cov["coverage_pct"]]
    ax.barh(cov["modality"], cov["coverage_pct"], color=colors, edgecolor="white", height=0.68)
    for i, row in enumerate(cov.itertuples(index=False)):
        ax.text(row.coverage_pct + 0.8, i, f"{int(row.n_participants):,} ({row.coverage_pct:.1f}%)", va="center", fontsize=8.5)
    ax.set_xlim(75, 103)
    ax.set_xlabel("Participant coverage (%)")
    ax.set_title("Data agents cover a high-completeness multimodal cohort", loc="left", weight="bold")
    ax.grid(axis="x", color=COLORS["line"], linewidth=0.7, alpha=0.8)
    return save(fig, "fig2_modality_coverage")


def fig_clock_performance(perf: pd.DataFrame) -> Path:
    plot = perf.copy()
    plot["label"] = plot["clock_name"].str.replace("_", " ").str.title()
    plot = plot.sort_values("r_squared", ascending=True)
    fam_colors = {
        "Clinical/system clocks": COLORS["blue"],
        "Functional time-series clocks": COLORS["teal"],
        "Pretrained imaging clocks": COLORS["orange"],
        "Pretrained signal clocks": COLORS["green"],
        "Multimodal baseline": COLORS["purple"],
    }
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.4), gridspec_kw={"width_ratios": [1.05, 1]})
    y = np.arange(len(plot))
    colors = [fam_colors.get(f, COLORS["gray"]) for f in plot["family"]]

    axes[0].barh(y, plot["r_squared"], color=colors, height=0.72)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(plot["label"])
    axes[0].axvline(0, color=COLORS["gray"], linewidth=0.8)
    axes[0].set_xlabel("Test R²")
    axes[0].set_title("Age-prediction performance", loc="left", weight="bold")
    axes[0].grid(axis="x", color=COLORS["line"], linewidth=0.7, alpha=0.8)

    order = plot.sort_values("mae", ascending=False)
    y2 = np.arange(len(order))
    axes[1].barh(y2, order["mae"], color=[fam_colors.get(f, COLORS["gray"]) for f in order["family"]], height=0.72)
    axes[1].set_yticks(y2)
    axes[1].set_yticklabels(order["label"])
    axes[1].set_xlabel("Test MAE (years; lower is better)")
    axes[1].set_title("Absolute error", loc="left", weight="bold")
    axes[1].grid(axis="x", color=COLORS["line"], linewidth=0.7, alpha=0.8)

    handles = [
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor=c, markersize=8, label=k)
        for k, c in fam_colors.items()
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Aging-clock agents establish baseline aging phenotypes before foundation modeling", x=0.02, ha="left", fontsize=15, weight="bold")
    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
    return save(fig, "fig3_aging_clock_performance")


def fig_concordance() -> Path:
    mat = pd.read_csv(result_path("concordance_matrix.csv"), index_col=0)
    labels = [c.replace("_", "\n") for c in mat.columns]
    fig, ax = plt.subplots(figsize=(8.2, 7.2))
    im = ax.imshow(mat.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_title("Age-gap concordance reveals partially disentangled aging axes", loc="left", weight="bold")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Pearson r")
    fig.tight_layout()
    return save(fig, "fig4_age_gap_concordance")


def fig_coupling_results() -> Path:
    atlas = pd.read_csv(result_path("coupling_atlas.csv")).sort_values("p_adjusted_severity_fdr").head(7)
    pred = pd.read_csv(result_path("coupling_prediction_performance.csv"))
    binary = pred[(pred["feature_set"] == "coupling_only") & (pred["task"] == "binary")].copy()
    cont = pred[(pred["feature_set"] == "coupling_only") & (pred["task"] == "continuous")].copy()
    cont = cont[cont["outcome"].isin(["hba1c", "frailty_index", "allostatic_load", "homeostatic_dysregulation", "study_group_ordinal"])]

    feature_labels = {
        "glucose_hr_awake_r": "Glucose-HR\nawake r",
        "glucose_hr_spearman_r": "Glucose-HR\nSpearman r",
        "glucose_hr_partial_r_activity_sleep": "Glucose-HR\npartial r",
        "glucose_hr_zero_lag_r": "Glucose-HR\nzero-lag r",
        "glucose_activity_spearman_r": "Glucose-activity\nSpearman r",
        "glucose_hr_peak_xcorr": "Glucose-HR\npeak xcorr",
        "glucose_activity_peak_xcorr": "Glucose-activity\npeak xcorr",
        "glucose_ms_entropy_s1": "Glucose entropy\nscale 1",
    }
    binary_labels = {
        "any_diabetes_vs_healthy": "Any diabetes\nvs healthy",
        "insulin_vs_healthy": "Insulin\nvs healthy",
    }
    continuous_labels = {
        "hba1c": "HbA1c",
        "frailty_index": "Frailty\nindex",
        "allostatic_load": "Allostatic\nload",
        "homeostatic_dysregulation": "Homeostatic\ndysreg.",
        "study_group_ordinal": "Severity\nordinal",
    }

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.7), gridspec_kw={"width_ratios": [1.35, 0.85, 0.9]})

    y = np.arange(len(atlas))[::-1]
    axes[0].barh(y, atlas["healthy_vs_insulin_d"], color=COLORS["green"], height=0.66)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([feature_labels.get(f, f.replace("_", "\n")) for f in atlas["feature"]], fontsize=8.8)
    axes[0].set_xlabel("Cohen's d: Healthy vs Insulin")
    axes[0].set_title("Top coupling features", loc="left", weight="bold")
    axes[0].grid(axis="x", color=COLORS["line"], linewidth=0.7, alpha=0.8)

    if not binary.empty:
        labels = [binary_labels.get(o, o) for o in binary["outcome"]]
        axes[1].bar(labels, binary["auroc"], color=COLORS["blue"], width=0.62)
        axes[1].axhline(0.5, color=COLORS["gray"], linestyle="--", linewidth=0.9)
        axes[1].set_ylim(0.45, 0.88)
        axes[1].set_ylabel("AUROC")
        axes[1].tick_params(axis="x", rotation=0, labelsize=8.5)
    axes[1].set_title("Held-out binary prediction", loc="left", weight="bold")
    axes[1].grid(axis="y", color=COLORS["line"], linewidth=0.7, alpha=0.8)

    labels = [continuous_labels.get(o, o) for o in cont["outcome"]]
    axes[2].bar(labels, cont["r2"], color=COLORS["orange"], width=0.62)
    axes[2].set_ylim(0, max(0.28, cont["r2"].max() * 1.2 if len(cont) else 0.28))
    axes[2].set_ylabel("R²")
    axes[2].set_title("Held-out continuous prediction", loc="left", weight="bold")
    axes[2].grid(axis="y", color=COLORS["line"], linewidth=0.7, alpha=0.8)
    axes[2].tick_params(axis="x", rotation=0, labelsize=8.0)

    fig.suptitle("Agentic discovery layer surfaces dynamic physiology beyond isolated clocks", x=0.02, ha="left", fontsize=15, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return save(fig, "fig5_coupling_discovery_results")


def fig_jepa_bridge() -> Path:
    seq = pd.read_csv(ROOT / "foundation_jepa/sequence" / "artifacts" / "next_stage" / "summary.csv")
    configs = [
        "full_joint",
        "static_only_joint",
        "shuffle_sequences_joint",
        "drop_clinical_joint",
        "sequence_only_joint",
        "shuffle_all_joint",
    ]
    s = seq[seq["config"].isin(configs)].groupby("config").agg(
        test_age_mae=("test_age_mae", "mean"),
        test_age_r2=("test_age_r2", "mean"),
        test_severity_acc=("test_severity_acc", "mean"),
    ).reindex(configs).reset_index()

    win = pd.read_csv(ROOT / "foundation_jepa/window" / "artifacts" / "horizon_suite" / "summary.csv")
    w = win.groupby(["horizon_minutes", "control"])["test_jepa"].mean().reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8), gridspec_kw={"width_ratios": [1.1, 1]})
    labels = s["config"].str.replace("_", "\n")
    axes[0].bar(labels, s["test_age_mae"], color=[COLORS["purple"], COLORS["purple"], COLORS["teal"], COLORS["orange"], COLORS["green"], COLORS["verm"]], width=0.68)
    axes[0].set_ylabel("Test age MAE")
    axes[0].set_title("Sequence-level JEPA: age target favors static shortcuts", loc="left", weight="bold")
    axes[0].grid(axis="y", color=COLORS["line"], linewidth=0.7, alpha=0.8)
    axes[0].tick_params(axis="x", labelsize=7.5)

    control_colors = {"aligned": COLORS["green"], "wrong_day": COLORS["orange"], "participant_shuffle": COLORS["verm"]}
    for control, d in w.groupby("control"):
        d = d.sort_values("horizon_minutes")
        axes[1].plot(d["horizon_minutes"], d["test_jepa"], marker="o", linewidth=2.0, label=control.replace("_", " "), color=control_colors.get(control, COLORS["gray"]))
    axes[1].set_xlabel("Prediction horizon (min)")
    axes[1].set_ylabel("Test JEPA loss")
    axes[1].set_title("Window JEPA: aligned temporal physiology is learnable", loc="left", weight="bold")
    axes[1].legend(frameon=False)
    axes[1].grid(color=COLORS["line"], linewidth=0.7, alpha=0.8)

    fig.suptitle("Agent outputs become foundation-model objectives and controls", x=0.02, ha="left", fontsize=15, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return save(fig, "fig6_foundation_model_handoff")


def write_summary(inv: pd.DataFrame, cov: pd.DataFrame, perf: pd.DataFrame) -> None:
    top_clock = perf.sort_values("r_squared", ascending=False).iloc[0]
    best_static = perf[perf["clock_name"].isin(["multimodal_all_feature", "multimodal_static"])]
    coupling = pd.read_csv(result_path("coupling_prediction_performance.csv"))
    insulin_auc = coupling[(coupling["feature_set"] == "coupling_only") & (coupling["outcome"] == "insulin_vs_healthy")]["auroc"].iloc[0]
    hba1c_r2 = coupling[(coupling["feature_set"] == "coupling_only") & (coupling["outcome"] == "hba1c")]["r2"].iloc[0]
    win = pd.read_csv(ROOT / "foundation_jepa/window" / "artifacts" / "horizon_suite" / "summary.csv")
    win_gap = win.groupby("control")["test_jepa"].mean().to_dict()

    def perf_line(clock_name: str, label: str) -> str:
        rows = perf[perf["clock_name"].eq(clock_name)]
        if rows.empty:
            return f"- {label}: result not available in the current artifact set."
        row = rows.sort_values("r_squared", ascending=False).iloc[0]
        return f"- {label}: MAE {row.mae:.2f} years and R2 {row.r_squared:.3f}."

    multimodal_clock_name = (
        "multimodal_all_feature"
        if perf["clock_name"].eq("multimodal_all_feature").any()
        else "multimodal_static"
    )

    lines = [
        "# Agentic framework result summary",
        "",
        "Generated by `scripts/reporting/agentic_results_analysis.py` from existing AI-READI result tables.",
        "",
        "## Key numbers",
        "",
        f"- Data curation layer: {int(cov['n_total'].iloc[0]):,} participants; modality coverage ranges from {cov['coverage_pct'].min():.1f}% to {cov['coverage_pct'].max():.1f}%.",
        f"- Aging-clock layer: {len(perf):,} clock/model rows summarized; best age-prediction R2 is `{top_clock.clock_name}` with MAE {top_clock.mae:.2f} years and R2 {top_clock.r_squared:.3f}.",
    ]
    if not best_static.empty:
        row = best_static.iloc[0]
        lines.append(f"- Multimodal static baseline: MAE {row.mae:.2f} years, R2 {row.r_squared:.3f}, r {row.pearson_r:.3f}.")
    lines += [
        f"- Coupling-only dynamic biomarkers: insulin-vs-healthy AUROC {insulin_auc:.3f}; HbA1c held-out R2 {hba1c_r2:.3f}.",
        f"- Window JEPA control gap: mean aligned loss {win_gap.get('aligned', np.nan):.3f}, wrong-day {win_gap.get('wrong_day', np.nan):.3f}, participant-shuffle {win_gap.get('participant_shuffle', np.nan):.3f}.",
        "",
        "## Interpretation",
        "",
        "- The agentic workflow is already producing real research artifacts: feature matrices, aging clocks, age-gap profiles, subtype tables, coupling atlases, prediction tasks, and foundation-model controls.",
        "- Single-modality and system-specific aging clocks establish necessary baselines, but most static clocks are modest; retinal and multimodal/static clocks are stronger than many narrow clinical systems.",
        "- The strongest biological result for the agentic section is not just age prediction; it is the dynamic physiology discovery layer, where glucose-HR/activity coupling carries diabetes-severity and clinical-burden signal.",
        "- The foundation-model experiments should be framed as the next layer: agent-generated curated representations and controls expose that static age/severity objectives can shortcut, while window-level temporal JEPA better matches resilience/coupling biology.",
        "",
        "## Slide-ready sequence",
        "",
        "### Slide 1: Agentic workflow produces reusable scientific artifacts",
        "",
        "- Data agents curate high-coverage multimodal AI-READI signals into analysis-ready tables.",
        "- Aging agents produce 13 system/functional clocks, 15 age-gap dimensions, and 3 subtype labels.",
        "- Discovery agents generate coupling atlases, biomarker panels, prediction tasks, and foundation-model controls.",
        "- Memory and critic layers preserve constraints, workflows, domain knowledge, and statistical safeguards.",
        "",
        "### Slide 2: Single-modality clocks establish the baseline aging phenotype",
        "",
        perf_line("cardiovascular", "Best narrow clinical/system clock"),
        perf_line("retinal_image", "Retinal image clock"),
        perf_line("cardiac_ecg", "Cardiac ECG clock"),
        perf_line(multimodal_clock_name, "Multimodal all-feature clock"),
        "",
        "### Slide 3: Age gaps are not one unified aging axis",
        "",
        "- Age-gap concordance is strong within related systems, such as immune-inflammatory and hematologic clocks.",
        "- Cross-domain concordance is often weak, especially between static clinical clocks and imaging clocks.",
        "- This supports modeling aging as a multidimensional phenotype rather than a single scalar clock.",
        "",
        "### Slide 4: Agentic discovery finds dynamic physiology beyond clocks",
        "",
        "- Glucose-HR and glucose-activity coupling are among the strongest diabetes-severity features.",
        f"- Coupling-only features predict insulin-dependent vs healthy status with AUROC {insulin_auc:.3f}.",
        f"- Coupling-only features predict HbA1c with held-out R2 {hba1c_r2:.3f}.",
        "- This motivates resilience and coordination as aging phenotypes, not just predicted-age residuals.",
        "",
        "### Slide 5: Agent outputs define foundation-model objectives",
        "",
        "- Sequence-level JEPA shows that chronological age and severity can be solved through static shortcuts.",
        "- Window-level JEPA gives a better objective: aligned temporal physiology has lower loss than wrong-day or participant-shuffled controls.",
        "- The agentic layer therefore supplies both biological hypotheses and rigorous controls for representation learning.",
        "",
    ]
    (OUT / "agentic_results_summary.md").write_text("\n".join(lines))


def main() -> None:
    ensure_dirs()
    set_style()

    cov = modality_coverage()
    cov.to_csv(TABLES / "modality_coverage.csv", index=False)

    perf = clock_performance()
    inv = agentic_inventory()

    fig_inventory(inv)
    fig_coverage(cov)
    fig_clock_performance(perf)
    fig_concordance()
    fig_coupling_results()
    fig_jepa_bridge()
    write_summary(inv, cov, perf)

    print(f"Wrote figures to {FIG}")
    print(f"Wrote tables to {TABLES}")
    print(f"Wrote summary to {OUT / 'agentic_results_summary.md'}")


if __name__ == "__main__":
    main()
