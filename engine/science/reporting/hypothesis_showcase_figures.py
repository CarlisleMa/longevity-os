"""Generate slide-ready figures for the hypothesis discovery section.

The figures use the live hypothesis JSON workspace plus result CSVs in
``results/``. Outputs are saved as PNG, SVG, and PDF so they can be edited in
PowerPoint/Illustrator or dropped directly into slides.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from textwrap import fill

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd

from scripts.config import result_path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
HYPOTHESES = ROOT / "hypothesis_driven" / "hypotheses"
OUTDIR = RESULTS / "figures" / "hypothesis_showcase"
OUTDIR.mkdir(parents=True, exist_ok=True)

DPI = 320

COLORS = {
    "blue": "#0072B2",
    "sky": "#56B4E9",
    "amber": "#E69F00",
    "green": "#009E73",
    "vermillion": "#D55E00",
    "pink": "#CC79A7",
    "gray": "#999999",
    "dark": "#222222",
    "light": "#F5F5F5",
    "line": "#B8B8B8",
}

STATUS_COLORS = {
    "proposed": "#D9EAF7",
    "critiqued": COLORS["amber"],
    "validated": COLORS["sky"],
    "queued": "#7FCDBB",
    "executing": "#80B1D3",
    "completed": COLORS["blue"],
    "verified": "#4D9221",
    "supported": COLORS["green"],
    "inconclusive": COLORS["gray"],
    "refuted": COLORS["vermillion"],
    "rejected": "#B2182B",
}

GROUP_KEYS = [
    "healthy",
    "pre_diabetes_lifestyle_controlled",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled",
    "insulin_dependent",
]
GROUP_LABELS = ["Healthy", "Pre-DM", "Oral med", "Insulin"]
GROUP_SHORT = ["H", "PD", "OM", "ID"]
GROUP_COLORS = [COLORS["blue"], COLORS["sky"], COLORS["amber"], COLORS["vermillion"]]

CATEGORY_LABELS = {
    "temporal_coupling": "Temporal coupling",
    "structural_dynamic": "Structural-dynamic",
    "environmental_modulation": "Environment",
    "complexity_loss": "Complexity loss",
    "event_dynamics": "Event dynamics",
    "circadian_organization": "Circadian org.",
    "physiotype_discovery": "Physiotypes",
    "resilience": "Resilience",
    "frequency_coupling": "Frequency coupling",
    "causal_architecture": "Causal architecture",
}


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans", "Helvetica"],
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "axes.edgecolor": COLORS["dark"],
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )


def save_figure(fig: plt.Figure, name: str) -> None:
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(
            OUTDIR / f"{name}.{suffix}",
            dpi=DPI,
            bbox_inches="tight",
            pad_inches=0.12,
        )
    plt.close(fig)


def read_hypotheses() -> pd.DataFrame:
    rows: list[dict] = []
    for path in sorted(HYPOTHESES.glob("*.json")):
        with path.open() as f:
            data = json.load(f)
        if not isinstance(data, dict) or not data.get("id"):
            continue
        result = data.get("results") or {}
        verdict = data.get("critic_verdict") or {}
        rows.append(
            {
                "id": data.get("id"),
                "title": data.get("title", ""),
                "category": data.get("category", "unknown"),
                "status": data.get("status", "unknown"),
                "priority": float(data.get("priority", 0) or 0),
                "source": data.get("source", ""),
                "primary_metric": result.get("primary_metric", ""),
                "primary_value": result.get("primary_value", np.nan),
                "effect_size": result.get("effect_size", np.nan),
                "effect_size_type": result.get("effect_size_type", ""),
                "fdr_p_value": result.get("fdr_p_value", np.nan),
                "verdict": verdict.get("verdict", "pending"),
                "overall_score": verdict.get("overall_score", np.nan),
            }
        )
    return pd.DataFrame(rows)


def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


def row_by(df: pd.DataFrame, column: str, value: str) -> pd.Series:
    rows = df.loc[df[column] == value]
    if rows.empty:
        raise KeyError(f"Missing {value!r} in {column}")
    return rows.iloc[0]


def neglog10(p: float, cap: float = 30.0) -> float:
    if not np.isfinite(p) or p <= 0:
        return cap
    return min(-math.log10(max(p, 1e-300)), cap)


def draw_round_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    wh: tuple[float, float],
    title: str,
    subtitle: str,
    color: str,
    fill: str = "white",
    fontsize: int = 10,
) -> patches.FancyBboxPatch:
    x, y = xy
    w, h = wh
    box = patches.FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.018,rounding_size=0.045",
        linewidth=1.35,
        edgecolor=color,
        facecolor=fill,
        zorder=2,
    )
    ax.add_patch(box)
    ax.text(
        x + w / 2,
        y + h * 0.64,
        title,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        color=color,
        zorder=3,
    )
    ax.text(
        x + w / 2,
        y + h * 0.34,
        subtitle,
        ha="center",
        va="center",
        fontsize=fontsize - 2,
        color="#555555",
        linespacing=1.1,
        zorder=3,
    )
    return box


def arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = "#777777",
    lw: float = 1.2,
    ls: str = "-",
    rad: float = 0.0,
) -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(
            arrowstyle="-|>",
            lw=lw,
            color=color,
            linestyle=ls,
            mutation_scale=12,
            shrinkA=2,
            shrinkB=2,
            connectionstyle=f"arc3,rad={rad}",
        ),
        zorder=1,
    )


def fig_workflow() -> None:
    fig, ax = plt.subplots(figsize=(13.3, 6.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.02,
        0.96,
        "Hypothesis discovery: from pipeline surprise to verified experiment",
        fontsize=16,
        fontweight="bold",
        ha="left",
        va="top",
        color=COLORS["dark"],
    )

    # Upstream system sources.
    draw_round_box(
        ax,
        (0.03, 0.68),
        (0.19, 0.16),
        "Agentic system outputs",
        "aging clocks | coupling atlas\nprediction failures | nulls",
        COLORS["gray"],
        fill="#FAFAFA",
    )
    draw_round_box(
        ax,
        (0.03, 0.42),
        (0.19, 0.16),
        "Literature priors",
        "mechanism | direction\ntimescale | confounders",
        COLORS["blue"],
        fill="#FAFAFA",
    )

    draw_round_box(
        ax,
        (0.28, 0.69),
        (0.18, 0.13),
        "Data-driven seeds",
        "residuals, surprises,\nunexpected nulls",
        COLORS["amber"],
    )
    draw_round_box(
        ax,
        (0.28, 0.43),
        (0.18, 0.13),
        "Theory-driven seeds",
        "known physiology,\nclinical mechanisms",
        COLORS["blue"],
    )

    draw_round_box(
        ax,
        (0.52, 0.70),
        (0.14, 0.12),
        "Proposer",
        "structured\nhypothesis JSON",
        COLORS["blue"],
    )
    draw_round_box(
        ax,
        (0.70, 0.70),
        (0.14, 0.12),
        "Critic",
        "feasibility,\ncontrols, power",
        COLORS["amber"],
    )
    draw_round_box(
        ax,
        (0.50, 0.42),
        (0.37, 0.15),
        "Hypothesis workspace",
        "",
        COLORS["gray"],
        fill="#F7F7F7",
    )
    draw_round_box(
        ax,
        (0.52, 0.18),
        (0.14, 0.12),
        "Executor",
        "generate script\nrun analysis",
        COLORS["green"],
    )
    draw_round_box(
        ax,
        (0.70, 0.18),
        (0.14, 0.12),
        "Verifier",
        "robustness checks\ninterpretation",
        COLORS["pink"],
    )

    # Discovery state pills.
    states = [
        ("proposed", STATUS_COLORS["proposed"]),
        ("critiqued", STATUS_COLORS["critiqued"]),
        ("validated", STATUS_COLORS["validated"]),
        ("completed", STATUS_COLORS["completed"]),
        ("supported", STATUS_COLORS["supported"]),
        ("refuted", STATUS_COLORS["refuted"]),
    ]
    xs = np.linspace(0.54, 0.83, len(states))
    y0 = 0.445
    for i, (state, col) in enumerate(states):
        x = xs[i]
        ax.scatter(x, y0 + 0.032, s=160, color=col, edgecolor="white", linewidth=0.8, zorder=4)
        ax.text(
            x,
            y0,
            state,
            fontsize=6.5,
            ha="center",
            va="center",
            color="#333333",
            zorder=5,
        )

    arrow(ax, (0.22, 0.76), (0.28, 0.76), COLORS["amber"])
    arrow(ax, (0.22, 0.50), (0.28, 0.50), COLORS["blue"])
    arrow(ax, (0.46, 0.755), (0.52, 0.755), COLORS["amber"])
    arrow(ax, (0.46, 0.495), (0.52, 0.735), COLORS["blue"], rad=0.15)
    arrow(ax, (0.66, 0.76), (0.70, 0.76), COLORS["line"])
    arrow(ax, (0.77, 0.70), (0.72, 0.57), COLORS["line"])
    arrow(ax, (0.61, 0.42), (0.59, 0.30), COLORS["green"])
    arrow(ax, (0.66, 0.24), (0.70, 0.24), COLORS["line"])
    arrow(ax, (0.77, 0.30), (0.77, 0.42), COLORS["pink"])
    arrow(ax, (0.84, 0.24), (0.92, 0.74), COLORS["pink"], ls="--", rad=-0.35)
    arrow(ax, (0.92, 0.74), (0.46, 0.76), COLORS["pink"], ls="--", rad=0.08)
    ax.text(
        0.92,
        0.78,
        "discovery memory\nupdates priors",
        ha="center",
        va="bottom",
        fontsize=8,
        color=COLORS["pink"],
    )

    ax.text(
        0.03,
        0.12,
        "Design principle",
        fontsize=10,
        fontweight="bold",
        color=COLORS["dark"],
    )
    ax.text(
        0.03,
        0.07,
        "Every hypothesis must specify direction, timescale, refutation criterion, negative control, confounders, unique dataset enabler, and expected effect size before execution.",
        fontsize=9,
        color="#444444",
        ha="left",
        va="top",
        wrap=True,
    )

    save_figure(fig, "hypo_A_discovery_workflow")


def fig_lifecycle_matrix(hyp: pd.DataFrame) -> None:
    status_order = ["critiqued", "validated", "completed", "supported", "inconclusive", "refuted"]
    counts = (
        hyp.groupby(["category", "status"])
        .size()
        .reset_index(name="n")
        .pivot(index="category", columns="status", values="n")
        .fillna(0)
        .astype(int)
    )
    for status in status_order:
        if status not in counts.columns:
            counts[status] = 0
    counts = counts[status_order]
    row_order = hyp["category"].value_counts().index.tolist()
    counts = counts.reindex(row_order)

    fig, ax = plt.subplots(figsize=(11.0, 6.0))
    fig.text(0.08, 0.965, "Hypothesis workspace inventory", ha="left", va="top", fontsize=15, fontweight="bold")
    fig.text(
        0.08,
        0.91,
        f"N = {len(hyp)} hypotheses across {hyp['category'].nunique()} biological categories",
        ha="left",
        va="top",
        fontsize=10.5,
        color="#555555",
    )
    fig.subplots_adjust(top=0.82, left=0.18, right=0.98, bottom=0.13)

    n_rows, n_cols = counts.shape
    ax.set_xlim(-0.6, n_cols - 0.4)
    ax.set_ylim(-0.7, n_rows - 0.3)

    for i in range(n_rows):
        for j in range(n_cols):
            rect = patches.Rectangle(
                (j - 0.47, i - 0.42),
                0.94,
                0.84,
                facecolor="#FBFBFB",
                edgecolor="#E6E6E6",
                linewidth=0.8,
                zorder=0,
            )
            ax.add_patch(rect)
            val = int(counts.iloc[n_rows - 1 - i, j])
            if val > 0:
                status = counts.columns[j]
                size = 260 + val * 155
                ax.scatter(
                    j,
                    i,
                    s=size,
                    color=STATUS_COLORS[status],
                    edgecolor="white",
                    linewidth=1.0,
                    zorder=3,
                )
                ax.text(
                    j,
                    i,
                    str(val),
                    ha="center",
                    va="center",
                    fontsize=10,
                    fontweight="bold",
                    color="white" if status not in {"critiqued", "validated"} else COLORS["dark"],
                    zorder=4,
                )

    y_labels = [CATEGORY_LABELS.get(c, c) for c in counts.index.tolist()][::-1]
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(y_labels)
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels([s.capitalize() for s in status_order], rotation=0)
    ax.tick_params(axis="both", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Add a thin lifecycle arrow above the columns.
    ax.annotate(
        "",
        xy=(n_cols - 0.65, n_rows - 0.02),
        xytext=(0.05, n_rows - 0.02),
        arrowprops=dict(arrowstyle="-|>", color="#777777", lw=1.0),
        annotation_clip=False,
    )
    ax.text(
        n_cols - 0.65,
        n_rows + 0.12,
        "lifecycle progression",
        ha="right",
        va="bottom",
        fontsize=8,
        color="#777777",
    )

    save_figure(fig, "hypo_B_lifecycle_category_matrix")


def evidence_records() -> pd.DataFrame:
    atlas = csv("coupling_atlas.csv")
    damage = csv("coupling_damage.csv")
    freq = csv("h_new01_frequency_coupling.csv")
    exc = csv("h_new03_excursion_hr.csv")
    ent = csv("h_new05_partial_correlations.csv")
    noct = csv("h_new06_nocturnal_coupling.csv")
    sleep = csv("h_new13_sleepwake_transition.csv")
    diurnal = csv("h_new17_diurnal_coupling.csv")

    records: list[dict] = []

    def add(hid, short, metric_label, effect, fdr, status, kind):
        records.append(
            {
                "id": hid,
                "short": short,
                "metric_label": metric_label,
                "effect": float(effect),
                "fdr": float(fdr),
                "status": status,
                "kind": kind,
            }
        )

    r = row_by(atlas, "feature", "glucose_hr_awake_r")
    add("H-MIG01", "Glucose-HR awake coupling", f"d={r.healthy_vs_insulin_d:.2f}", r.healthy_vs_insulin_d, r.p_adjusted_severity_fdr, "supported", "d")

    r = row_by(atlas, "feature", "glucose_activity_spearman_r")
    add("H-MIG02", "Glucose-activity coupling", f"d={r.healthy_vs_insulin_d:.2f}", r.healthy_vs_insulin_d, r.p_adjusted_severity_fdr, "supported", "d")

    r = row_by(damage, "target", "frailty_index")
    r = damage[(damage["target"] == "frailty_index") & (damage["feature"] == "glucose_hr_awake_r")].iloc[0]
    add("H-MIG04", "Coupling to frailty burden", f"partial r={r.partial_r:.2f}", r.partial_r, r.p_fdr_by_target, "supported", "r")

    r = row_by(freq, "feature", "coherence_4_8h")
    add("H-NEW01", "4-8h coupling coherence", f"d={r.d_h_vs_id:.2f}", r.d_h_vs_id, r.fdr_p, "completed", "d")

    r = row_by(exc, "feature", "exc_hr_peak_mean")
    add("H-NEW03", "Post-excursion HR peak", f"d={r.d_h_vs_id:.2f}", r.d_h_vs_id, r.fdr_p, "completed_pending_db", "d")

    r = ent[(ent["entropy_feature"] == "glucose_ms_entropy_s1") & (ent["outcome"] == "allostatic_load")].iloc[0]
    add("H-NEW05", "Glucose entropy to allostatic load", f"partial r={r.partial_r:.2f}", r.partial_r, r.fdr_p, "completed", "r")

    r = row_by(diurnal, "feature", "diurnal_mesor")
    add("H-NEW17", "Diurnal coupling mesor", f"d={r.d_h_vs_id:.2f}", r.d_h_vs_id, r.fdr_p, "completed", "d")

    r = row_by(noct, "feature", "nocturnal_coupling_mean")
    add("H-NEW06", "Nocturnal coupling", f"d={r.d_h_vs_id:.2f}", r.d_h_vs_id, r.fdr_p, "inconclusive", "d")

    r = row_by(sleep, "feature", "reorganization_time_min")
    add("H-NEW13", "Sleep-wake reorganization", f"d={r.d_h_vs_id:.2f}", r.d_h_vs_id, r.fdr_p, "inconclusive", "d")

    add("H-MIG05", "Structural age acceleration link", "no FDR signal", 0.0, 1.0, "refuted", "r")

    df = pd.DataFrame(records)
    df["evidence"] = df["fdr"].apply(neglog10)
    return df


def fig_evidence_map() -> None:
    df = evidence_records().sort_values(["evidence", "effect"], ascending=[True, True]).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(10.6, 5.8))
    fig.text(0.10, 0.965, "Verified and executed hypotheses: evidence strength map", ha="left", va="top", fontsize=15, fontweight="bold")
    fig.text(
        0.10,
        0.915,
        "Dot position shows -log10(FDR); dot size encodes absolute primary effect size. Mixed metrics are annotated.",
        ha="left",
        va="top",
        fontsize=9.5,
        color="#555555",
    )
    fig.subplots_adjust(top=0.82, left=0.24, right=0.98, bottom=0.20)

    y = np.arange(len(df))
    color_lookup = {
        "supported": COLORS["green"],
        "completed": COLORS["blue"],
        "completed_pending_db": COLORS["amber"],
        "inconclusive": COLORS["gray"],
        "refuted": COLORS["vermillion"],
    }
    sizes = 140 + np.clip(np.abs(df["effect"].to_numpy()), 0, 0.85) * 760
    colors = [color_lookup[s] for s in df["status"]]
    ax.scatter(df["evidence"], y, s=sizes, c=colors, edgecolor="white", linewidth=1.0, zorder=3)

    for _, row in df.iterrows():
        label = f"{row['id']}  {row['metric_label']}"
        ax.text(
            min(row["evidence"] + 0.55, 30.3),
            row.name,
            label,
            va="center",
            ha="left",
            fontsize=8.5,
            color="#333333",
        )

    ax.axvline(-math.log10(0.05), color="#777777", lw=0.9, ls="--")
    ax.text(
        -math.log10(0.05) + 0.1,
        len(df) - 0.35,
        "FDR=0.05",
        fontsize=8,
        color="#777777",
        ha="left",
        va="top",
    )
    ax.set_yticks(y)
    ax.set_yticklabels([fill(x, 28) for x in df["short"]], fontsize=9)
    ax.set_xlabel("-log10(FDR-adjusted p)")
    ax.set_xlim(0, 32)
    ax.set_ylim(-0.6, len(df) - 0.4)
    ax.grid(axis="x", color="#E6E6E6", lw=0.7)

    handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["green"], markersize=8, label="supported"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["blue"], markersize=8, label="completed"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["amber"], markersize=8, label="executed; DB pending"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["gray"], markersize=8, label="inconclusive"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["vermillion"], markersize=8, label="refuted"),
    ]
    ax.legend(handles=handles, frameon=False, ncol=3, loc="lower right", bbox_to_anchor=(1.0, -0.22))

    save_figure(fig, "hypo_C_evidence_strength_map")


def fig_timescale_split() -> None:
    freq = csv("h_new01_frequency_coupling.csv")
    order = [
        ("coherence_30_60min", "30-60 min"),
        ("coherence_1_2h", "1-2 h"),
        ("coherence_2_4h", "2-4 h"),
        ("coherence_4_8h", "4-8 h"),
        ("coherence_broadband", "Broadband"),
    ]
    rows = [row_by(freq, "feature", f) for f, _ in order]
    d = np.array([r.d_h_vs_id for r in rows])
    fdr = np.array([r.fdr_p for r in rows])
    med = np.array([[r.med_H, r.med_PD, r.med_OM, r.med_ID] for r in rows])

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(11.8, 5.2),
        gridspec_kw={"width_ratios": [1.05, 1.35], "wspace": 0.28},
    )
    ax = axes[0]
    y = np.arange(len(order))[::-1]
    labels = [label for _, label in order]
    for yi, val, p in zip(y, d, fdr):
        col = COLORS["vermillion"] if val > 0.08 else COLORS["blue"] if val < -0.08 else COLORS["gray"]
        ax.plot([0, val], [yi, yi], color=col, lw=2.2, solid_capstyle="round")
        ax.scatter(val, yi, s=105, color=col, edgecolor="white", linewidth=1.0, zorder=3)
        ax.text(
            0.43,
            yi,
            f"d={val:+.2f}\nFDR={p:.1e}",
            ha="left",
            va="center",
            fontsize=7.8,
        )
    ax.axvline(0, color="#333333", lw=0.8)
    ax.axvspan(-0.08, 0.08, color="#EEEEEE", alpha=0.6, zorder=0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Cohen's d: healthy vs insulin")
    ax.set_title("Effect direction flips by timescale", loc="left", fontweight="bold")
    ax.set_xlim(-0.45, 0.70)

    ax2 = axes[1]
    im = ax2.imshow(
        med,
        aspect="auto",
        cmap="PuOr_r",
        norm=mcolors.TwoSlopeNorm(vmin=float(np.nanmin(med)), vcenter=float(np.nanmedian(med)), vmax=float(np.nanmax(med))),
    )
    ax2.set_yticks(np.arange(len(labels)))
    ax2.set_yticklabels(labels)
    ax2.set_xticks(np.arange(len(GROUP_SHORT)))
    ax2.set_xticklabels(GROUP_SHORT)
    for i in range(med.shape[0]):
        for j in range(med.shape[1]):
            ax2.text(j, i, f"{med[i, j]:.3f}", ha="center", va="center", fontsize=8, color="#222222")
    ax2.set_title("Median coupling by severity group", loc="left", fontweight="bold")
    cbar = fig.colorbar(im, ax=ax2, fraction=0.045, pad=0.02)
    cbar.set_label("Median coherence", fontsize=9)
    ax2.text(
        1.0,
        -0.18,
        "H=healthy, PD=pre-diabetes, OM=oral medication, ID=insulin-dependent",
        transform=ax2.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        color="#666666",
    )

    fig.subplots_adjust(top=0.82, bottom=0.16)
    fig.suptitle("H-NEW01: broadband coupling is weak, but scale-resolved coupling is structured", x=0.02, y=0.98, ha="left", fontweight="bold", fontsize=14)
    save_figure(fig, "hypo_D_timescale_coupling_split")


def fig_excursion_response() -> None:
    with (result_path("hero_excursion_profiles.json")).open() as f:
        profiles = json.load(f)
    exc = csv("h_new03_excursion_hr.csv")
    peak = row_by(exc, "feature", "exc_hr_peak_mean")
    auc = row_by(exc, "feature", "exc_hr_auc_mean")
    ctrl = row_by(exc, "feature", "ctrl_hr_auc_mean")

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.4), gridspec_kw={"width_ratios": [1.35, 1.0], "wspace": 0.28})
    ax = axes[0]
    n_t = len(profiles[GROUP_KEYS[0]]["mean"])
    time = np.arange(n_t) * 5 - 30
    for key, label, color in zip(GROUP_KEYS, GROUP_LABELS, GROUP_COLORS):
        prof = profiles[key]
        mean = np.asarray(prof["mean"], dtype=float)
        lo = np.asarray(prof["ci_lo"], dtype=float)
        hi = np.asarray(prof["ci_hi"], dtype=float)
        ax.plot(time, mean, color=color, lw=2.0, label=label)
        if key in {"healthy", "insulin_dependent"}:
            ax.fill_between(time, lo, hi, color=color, alpha=0.13, linewidth=0)
    ax.axvline(0, color="#555555", lw=0.8, ls="--")
    ax.axhline(0, color="#BBBBBB", lw=0.8)
    ax.set_xlabel("Minutes from glucose excursion")
    ax.set_ylabel("Baseline-subtracted HR")
    ax.set_title("Event-triggered HR response", loc="left", fontweight="bold")
    ax.legend(frameon=False, ncol=2, loc="upper left")
    ax.text(0.98, 0.04, "Event-aligned mean profiles", transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="#666666")

    ax = axes[1]
    x = np.arange(4)
    peak_vals = np.array([peak.med_H, peak.med_PD, peak.med_OM, peak.med_ID], dtype=float)
    auc_vals = np.array([auc.med_H, auc.med_PD, auc.med_OM, auc.med_ID], dtype=float)
    ctrl_vals = np.array([ctrl.med_H, ctrl.med_PD, ctrl.med_OM, ctrl.med_ID], dtype=float)

    ax.plot(x, peak_vals, marker="o", lw=2.2, color=COLORS["vermillion"], label="Excursion HR peak")
    for xi, yi, col in zip(x, peak_vals, GROUP_COLORS):
        ax.scatter(xi, yi, s=115, color=col, edgecolor="white", linewidth=1.0, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(GROUP_SHORT)
    ax.set_ylabel("Median HR peak")
    ax.set_title("Severity gradient", loc="left", fontweight="bold")
    ax.grid(axis="y", color="#E6E6E6", lw=0.7)
    ax.text(
        0.03,
        0.08,
        f"Peak: d={peak.d_h_vs_id:.2f}, FDR={peak.fdr_p:.1e}\nAUC: d={auc.d_h_vs_id:.2f}, FDR={auc.fdr_p:.1e}\nRandom-window AUC: FDR={ctrl.fdr_p:.2f}",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.5,
        color="#333333",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#DDDDDD", linewidth=0.8),
    )

    axr = ax.twinx()
    axr.plot(x, auc_vals, marker="s", lw=1.8, color=COLORS["blue"], label="Excursion HR AUC")
    axr.plot(x, ctrl_vals, marker="^", lw=1.3, color=COLORS["gray"], ls="--", label="Random-window AUC")
    axr.set_ylabel("Median HR AUC", color=COLORS["blue"])
    axr.tick_params(axis="y", labelcolor=COLORS["blue"])
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = axr.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, frameon=False, loc="upper right", fontsize=8)

    fig.subplots_adjust(top=0.82, bottom=0.14)
    fig.suptitle("H-NEW03: glucose excursions expose blunted autonomic response", x=0.02, y=0.98, ha="left", fontweight="bold", fontsize=14)
    save_figure(fig, "hypo_E_excursion_hr_response")


def fig_diurnal_signature() -> None:
    diurnal = csv("h_new17_diurnal_coupling.csv")
    bins = [
        ("diurnal_r_00_04", "00-04"),
        ("diurnal_r_04_08", "04-08"),
        ("diurnal_r_08_12", "08-12"),
        ("diurnal_r_12_16", "12-16"),
        ("diurnal_r_16_20", "16-20"),
        ("diurnal_r_20_24", "20-24"),
    ]
    med = []
    effects = []
    fdrs = []
    for feature, _ in bins:
        r = row_by(diurnal, "feature", feature)
        med.append([r.med_H, r.med_PD, r.med_OM, r.med_ID])
        effects.append(r.d_h_vs_id)
        fdrs.append(r.fdr_p)
    med_arr = np.array(med).T

    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.1), gridspec_kw={"width_ratios": [1.35, 1.0], "wspace": 0.30})
    ax = axes[0]
    vmax = float(np.nanmax(np.abs(med_arr)))
    norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    im = ax.imshow(med_arr, aspect="auto", cmap="RdBu_r", norm=norm)
    ax.set_xticks(range(len(bins)))
    ax.set_xticklabels([b for _, b in bins])
    ax.set_yticks(range(len(GROUP_LABELS)))
    ax.set_yticklabels(GROUP_LABELS)
    for i in range(med_arr.shape[0]):
        for j in range(med_arr.shape[1]):
            ax.text(j, i, f"{med_arr[i, j]:+.2f}", ha="center", va="center", fontsize=8)
    ax.set_xlabel("Clock time")
    ax.set_title("Median glucose-HR coupling by time of day", loc="left", fontweight="bold")
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    cbar.set_label("Median r", fontsize=9)

    ax = axes[1]
    x = np.arange(len(bins))
    colors = [COLORS["vermillion"] if v > 0 else COLORS["blue"] for v in effects]
    ax.axhline(0, color="#333333", lw=0.8)
    for xi, val, col, p in zip(x, effects, colors, fdrs):
        ax.plot([xi, xi], [0, val], color=col, lw=2.0)
        ax.scatter(xi, val, s=105, color=col, edgecolor="white", linewidth=1.0, zorder=3)
        ax.text(xi, val + 0.035, f"{val:+.2f}", ha="center", va="bottom", fontsize=8.3)
    ax.set_xticks(x)
    ax.set_xticklabels([b for _, b in bins], rotation=35, ha="right")
    ax.set_ylabel("Cohen's d")
    ax.set_title("Effect by time window", loc="left", fontweight="bold")
    ax.set_ylim(-0.09, 0.55)
    ax.grid(axis="y", color="#E6E6E6", lw=0.7)
    mesor = row_by(diurnal, "feature", "diurnal_mesor")
    ax.text(
        0.02,
        0.04,
        f"Diurnal mesor: d={mesor.d_h_vs_id:.2f}, FDR={mesor.fdr_p:.1e}",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.5,
        color="#333333",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#DDDDDD", linewidth=0.8),
    )

    fig.subplots_adjust(top=0.82, bottom=0.16)
    fig.suptitle("H-NEW17: diabetes elevates coupling in specific diurnal windows", x=0.02, y=0.98, ha="left", fontweight="bold", fontsize=14)
    save_figure(fig, "hypo_F_diurnal_coupling_signature")


def fig_complexity_burden() -> None:
    pc = csv("h_new05_partial_correlations.csv")
    inc = csv("h_new05_incremental_prediction.csv")

    features = [
        "glucose_ms_entropy_s1",
        "glucose_ms_entropy_s3",
        "glucose_ms_entropy_s12",
        "glucose_ms_entropy_s36",
        "glucose_ms_entropy_s72",
    ]
    feature_labels = ["s1", "s3", "s12", "s36", "s72"]
    outcomes = ["allostatic_load", "frailty_index", "homeostatic_dysregulation"]
    outcome_labels = ["Allostatic load", "Frailty index", "Homeostatic dysreg."]
    mat = np.full((len(outcomes), len(features)), np.nan)
    fdr = np.full_like(mat, np.nan, dtype=float)
    for i, outcome in enumerate(outcomes):
        for j, feat in enumerate(features):
            r = pc[(pc["entropy_feature"] == feat) & (pc["outcome"] == outcome)].iloc[0]
            mat[i, j] = r.partial_r
            fdr[i, j] = r.fdr_p

    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.9), gridspec_kw={"width_ratios": [1.25, 1.0], "wspace": 0.32})
    ax = axes[0]
    vmax = max(abs(np.nanmin(mat)), abs(np.nanmax(mat)), 0.13)
    im = ax.imshow(mat, aspect="auto", cmap="RdBu_r", norm=mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax))
    ax.set_xticks(range(len(features)))
    ax.set_xticklabels(feature_labels)
    ax.set_yticks(range(len(outcomes)))
    ax.set_yticklabels(outcome_labels)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            star = "*" if fdr[i, j] < 0.05 else ""
            ax.text(j, i, f"{mat[i, j]:+.2f}{star}", ha="center", va="center", fontsize=8.5)
    ax.set_title("Adjusted partial correlations", loc="left", fontweight="bold")
    ax.set_xlabel("Glucose entropy scale")
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    cbar.set_label("Partial r", fontsize=9)

    ax = axes[1]
    allostatic = inc[inc["outcome"] == "allostatic_load"].copy()
    models = [
        "base+glucose_ms_entropy_s1",
        "base+glucose_ms_entropy_s3",
        "base+glucose_ms_entropy_s12",
        "base+glucose_ms_entropy_s36",
        "base+glucose_ms_entropy_s72",
        "base+all_entropy",
    ]
    sub = allostatic.set_index("model").loc[models].reset_index()
    labels = ["s1", "s3", "s12", "s36", "s72", "all"]
    y = np.arange(len(sub))[::-1]
    ax.axvline(0, color="#333333", lw=0.8)
    for yi, delta, label in zip(y, sub["delta_r2"], labels):
        col = COLORS["green"] if delta > 0 else COLORS["gray"]
        ax.plot([0, delta], [yi, yi], color=col, lw=2.0)
        ax.scatter(delta, yi, s=90, color=col, edgecolor="white", linewidth=1.0, zorder=3)
        ax.text(delta + 0.00045, yi, f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}", va="center", ha="left", fontsize=8.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Delta cross-validated R2")
    ax.set_title("Increment over base model\n(allostatic load)", loc="left", fontweight="bold")
    ax.grid(axis="x", color="#E6E6E6", lw=0.7)

    fig.subplots_adjust(top=0.78, bottom=0.16)
    fig.suptitle("H-NEW05: glucose complexity tracks systemic burden modestly but consistently", x=0.02, y=0.98, ha="left", fontweight="bold", fontsize=14)
    save_figure(fig, "hypo_G_complexity_burden")


def fig_negative_learning() -> None:
    cards = [
        {
            "id": "H-MIG05",
            "title": "Structural age acceleration",
            "result": "No FDR-significant link to retinal/cardiac age acceleration or UACR.",
            "lesson": "Dynamic coupling appears functional before structural.",
            "color": COLORS["vermillion"],
        },
        {
            "id": "H-NEW06",
            "title": "Nocturnal coupling",
            "result": "Nocturnal coupling mean: d=-0.02, FDR=0.38.",
            "lesson": "Night-only windows do not explain next-day glycemia.",
            "color": COLORS["gray"],
        },
        {
            "id": "H-NEW13",
            "title": "Sleep-wake transition",
            "result": "Reorganization time: d=-0.06, FDR=0.61.",
            "lesson": "Transition metrics need stronger event definition.",
            "color": COLORS["gray"],
        },
        {
            "id": "H-MIG08",
            "title": "Static aging clocks",
            "result": "Unified clock AUROC=0.47 vs frailty AUROC=0.90.",
            "lesson": "Motivates dynamic, cross-system physiology.",
            "color": COLORS["amber"],
        },
    ]

    fig, ax = plt.subplots(figsize=(12.0, 5.4))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(
        0.02,
        0.94,
        "Negative learning: the agent stores nulls instead of hiding them",
        ha="left",
        va="top",
        fontsize=15,
        fontweight="bold",
        color=COLORS["dark"],
    )
    ax.text(
        0.02,
        0.88,
        "These results narrow the biology: the strongest signal is dynamic coordination, not every plausible cross-modal link.",
        ha="left",
        va="top",
        fontsize=10,
        color="#555555",
    )

    x_positions = [0.03, 0.275, 0.52, 0.765]
    for x, card in zip(x_positions, cards):
        box = patches.FancyBboxPatch(
            (x, 0.24),
            0.205,
            0.54,
            boxstyle="round,pad=0.02,rounding_size=0.035",
            facecolor="#FAFAFA",
            edgecolor=card["color"],
            linewidth=1.5,
        )
        ax.add_patch(box)
        ax.text(x + 0.018, 0.72, card["id"], ha="left", va="center", fontsize=9, fontweight="bold", color=card["color"])
        ax.text(x + 0.018, 0.66, fill(card["title"], 24), ha="left", va="top", fontsize=11, fontweight="bold", color=COLORS["dark"])
        ax.text(x + 0.018, 0.53, "Observed", ha="left", va="top", fontsize=8, fontweight="bold", color="#666666")
        ax.text(x + 0.018, 0.49, fill(card["result"], 30), ha="left", va="top", fontsize=8.4, color="#333333", linespacing=1.15)
        ax.text(x + 0.018, 0.36, "Stored lesson", ha="left", va="top", fontsize=8, fontweight="bold", color="#666666")
        ax.text(x + 0.018, 0.32, fill(card["lesson"], 30), ha="left", va="top", fontsize=8.4, color="#333333", linespacing=1.15)

    ax.annotate(
        "",
        xy=(0.94, 0.14),
        xytext=(0.06, 0.14),
        arrowprops=dict(arrowstyle="-|>", color=COLORS["pink"], lw=1.2, linestyle="--"),
    )
    ax.text(
        0.50,
        0.08,
        "archived rationale feeds the next proposal cycle",
        ha="center",
        va="center",
        fontsize=9,
        color=COLORS["pink"],
        fontstyle="italic",
    )

    save_figure(fig, "hypo_H_negative_learning_board")


def write_manifest(hyp: pd.DataFrame) -> None:
    evidence = evidence_records()
    lines = [
        "# Hypothesis Showcase Figures",
        "",
        "Generated from live hypothesis JSON and result CSVs.",
        "",
        f"- Hypotheses in workspace: {len(hyp)}",
        f"- Categories: {hyp['category'].nunique()}",
        f"- Status counts: {hyp['status'].value_counts().to_dict()}",
        "",
        "## Figure Files",
        "",
        "- `hypo_A_discovery_workflow`: workflow from pipeline/literature sources to proposer, critic, executor, verifier.",
        "- `hypo_B_lifecycle_category_matrix`: status-by-category hypothesis inventory, replacing the old status bar plot.",
        "- `hypo_C_evidence_strength_map`: mixed-metric evidence map using -log10(FDR), effect-size dot area, and status color.",
        "- `hypo_D_timescale_coupling_split`: H-NEW01 timescale-specific glucose-HR coupling.",
        "- `hypo_E_excursion_hr_response`: H-NEW03 event-triggered HR response and severity gradient.",
        "- `hypo_F_diurnal_coupling_signature`: H-NEW17 time-of-day coupling heatmap and effect profile.",
        "- `hypo_G_complexity_burden`: H-NEW05 entropy/complexity association with systemic burden.",
        "- `hypo_H_negative_learning_board`: null/refuted results as discovery memory.",
        "",
        "## Lead Numbers",
        "",
    ]
    for _, row in evidence.sort_values("evidence", ascending=False).iterrows():
        lines.append(
            f"- {row['id']}: {row['short']} ({row['metric_label']}, FDR={row['fdr']:.2e}, status={row['status']})"
        )
    (OUTDIR / "figure_manifest.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    configure_matplotlib()
    hyp = read_hypotheses()
    if hyp.empty:
        raise RuntimeError("No hypothesis JSON files found.")

    fig_workflow()
    fig_lifecycle_matrix(hyp)
    fig_evidence_map()
    fig_timescale_split()
    fig_excursion_response()
    fig_diurnal_signature()
    fig_complexity_burden()
    fig_negative_learning()
    write_manifest(hyp)
    print(f"Wrote figures to {OUTDIR}")


if __name__ == "__main__":
    main()
