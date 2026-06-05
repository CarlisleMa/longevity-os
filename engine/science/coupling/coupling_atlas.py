"""
Group-level atlas for dynamic coupling features.

Consumes results/coupling/coupling_features.parquet and tests whether each coupling
feature changes across the diabetes severity gradient.

Outputs:
    results/coupling/coupling_atlas.csv
    results/figures/coupling_atlas_top_heatmap.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

try:
    import statsmodels.api as sm
except Exception:  # pragma: no cover
    sm = None

from scripts.config import RESULTS_DIR, result_path


GROUP_ORDER = [
    "healthy",
    "pre_diabetes_lifestyle_controlled",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled",
    "insulin_dependent",
]
GROUP_LABELS = {
    "healthy": "Healthy",
    "pre_diabetes_lifestyle_controlled": "PreDM",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": "Oral med",
    "insulin_dependent": "Insulin",
}
DEFAULT_INPUT = result_path("coupling_features.parquet")
DEFAULT_OUTPUT = result_path("coupling_atlas.csv")
DEFAULT_FIGURE = RESULTS_DIR / "figures" / "coupling_atlas_top_heatmap.png"


def _load_metadata() -> pd.DataFrame:
    paths = [
        result_path("feature_matrix.parquet"),
        result_path("participant_index.parquet"),
    ]
    frames = []
    for path in paths:
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        if "person_id" in frame.columns:
            frame = frame.set_index("person_id")
        frames.append(frame)

    if not frames:
        raise FileNotFoundError("Need feature_matrix.parquet or participant_index.parquet")

    meta = frames[0].copy()
    for frame in frames[1:]:
        add_cols = [c for c in frame.columns if c not in meta.columns]
        meta = meta.join(frame[add_cols], how="left")
    meta.index = meta.index.astype(str)
    return meta


def _candidate_features(df: pd.DataFrame) -> list[str]:
    numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    keep_terms = (
        "_r",
        "_xcorr",
        "_lag_min",
        "_entropy",
        "sleep_fraction",
    )
    drop_terms = (
        "_n",
        "n_aligned",
        "aligned_hours",
        "_mean",
        "_sd",
        "steps_proxy",
    )
    return [
        col
        for col in numeric
        if any(term in col for term in keep_terms)
        and not any(term in col for term in drop_terms)
    ]


def _fdr_bh(pvalues: pd.Series) -> pd.Series:
    p = pd.to_numeric(pvalues, errors="coerce")
    out = pd.Series(np.nan, index=p.index, dtype=float)
    valid = p.dropna()
    if valid.empty:
        return out
    order = np.argsort(valid.to_numpy())
    ranked = valid.to_numpy()[order]
    n = len(ranked)
    adjusted = ranked * n / (np.arange(n) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0, 1)
    out.loc[valid.index[order]] = adjusted
    return out


def _cohens_d(a: pd.Series, b: pd.Series) -> float:
    a = pd.to_numeric(a, errors="coerce").dropna()
    b = pd.to_numeric(b, errors="coerce").dropna()
    if len(a) < 3 or len(b) < 3:
        return np.nan
    pooled = np.sqrt(((len(a) - 1) * a.var() + (len(b) - 1) * b.var()) / (len(a) + len(b) - 2))
    if pooled == 0 or np.isnan(pooled):
        return np.nan
    return float((b.mean() - a.mean()) / pooled)


def _adjusted_ols(df: pd.DataFrame, feature: str) -> tuple[float, float]:
    cols = [feature, "study_group_ordinal"]
    if "age" in df.columns:
        cols.append("age")
    if "clinical_site" in df.columns:
        cols.append("clinical_site")

    sub = df[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(sub) < 50:
        return np.nan, np.nan

    if sm is None:
        rho = stats.spearmanr(sub["study_group_ordinal"], sub[feature], nan_policy="omit")
        return float(rho.statistic), float(rho.pvalue)

    x = pd.DataFrame({"study_group_ordinal": sub["study_group_ordinal"].astype(float)})
    if "age" in sub.columns:
        x["age"] = sub["age"].astype(float)
    if "clinical_site" in sub.columns:
        site = pd.get_dummies(sub["clinical_site"].astype(str), prefix="site", drop_first=True)
        x = pd.concat([x, site.astype(float)], axis=1)
    x = sm.add_constant(x, has_constant="add")
    model = sm.OLS(sub[feature].astype(float), x).fit()
    return (
        float(model.params.get("study_group_ordinal", np.nan)),
        float(model.pvalues.get("study_group_ordinal", np.nan)),
    )


def build_atlas(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> pd.DataFrame:
    coupling = pd.read_parquet(input_path)
    if "person_id" in coupling.columns:
        coupling = coupling.set_index("person_id")
    coupling.index = coupling.index.astype(str)

    meta = _load_metadata()
    needed_meta = [c for c in ["study_group", "age", "clinical_site"] if c in meta.columns]
    df = coupling.join(meta[needed_meta], how="left")
    df = df[df["study_group"].isin(GROUP_ORDER)].copy()
    df["study_group_ordinal"] = df["study_group"].map({g: i for i, g in enumerate(GROUP_ORDER)})

    rows = []
    for feature in _candidate_features(coupling):
        values_by_group = [
            pd.to_numeric(df.loc[df["study_group"] == group, feature], errors="coerce").dropna()
            for group in GROUP_ORDER
        ]
        if sum(len(v) for v in values_by_group) < 50 or any(len(v) < 5 for v in values_by_group):
            continue

        kw = stats.kruskal(*values_by_group)
        rho = stats.spearmanr(df["study_group_ordinal"], df[feature], nan_policy="omit")
        adj_coef, adj_p = _adjusted_ols(df, feature)
        row = {
            "feature": feature,
            "n": int(pd.to_numeric(df[feature], errors="coerce").notna().sum()),
            "kruskal_h": float(kw.statistic),
            "p_kruskal": float(kw.pvalue),
            "severity_spearman_rho": float(rho.statistic),
            "p_severity_spearman": float(rho.pvalue),
            "adjusted_severity_coef": adj_coef,
            "p_adjusted_severity": adj_p,
            "healthy_vs_insulin_d": _cohens_d(values_by_group[0], values_by_group[-1]),
        }
        for group, values in zip(GROUP_ORDER, values_by_group):
            label = GROUP_LABELS[group].lower().replace(" ", "_")
            row[f"{label}_median"] = float(values.median())
            row[f"{label}_iqr"] = float(values.quantile(0.75) - values.quantile(0.25))
        rows.append(row)

    atlas = pd.DataFrame(rows)
    if atlas.empty:
        raise RuntimeError("No coupling atlas rows could be computed.")
    atlas["p_kruskal_fdr"] = _fdr_bh(atlas["p_kruskal"])
    atlas["p_severity_spearman_fdr"] = _fdr_bh(atlas["p_severity_spearman"])
    atlas["p_adjusted_severity_fdr"] = _fdr_bh(atlas["p_adjusted_severity"])
    atlas = atlas.sort_values(["p_adjusted_severity_fdr", "p_kruskal_fdr", "feature"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    atlas.to_csv(output_path, index=False)
    print(f"Wrote {len(atlas)} feature tests to {output_path}")
    return atlas


def plot_top_heatmap(
    atlas: pd.DataFrame,
    input_path: Path = DEFAULT_INPUT,
    figure_path: Path = DEFAULT_FIGURE,
    top_n: int = 20,
) -> None:
    coupling = pd.read_parquet(input_path)
    if "person_id" in coupling.columns:
        coupling = coupling.set_index("person_id")
    coupling.index = coupling.index.astype(str)
    meta = _load_metadata()
    df = coupling.join(meta[["study_group"]], how="left")
    df = df[df["study_group"].isin(GROUP_ORDER)].copy()

    top = atlas.reindex(atlas["healthy_vs_insulin_d"].abs().sort_values(ascending=False).index)
    top_features = top["feature"].head(top_n).tolist()
    medians = pd.DataFrame(index=top_features, columns=[GROUP_LABELS[g] for g in GROUP_ORDER], dtype=float)
    for feature in top_features:
        for group in GROUP_ORDER:
            medians.loc[feature, GROUP_LABELS[group]] = pd.to_numeric(
                df.loc[df["study_group"] == group, feature], errors="coerce"
            ).median()

    z = medians.sub(medians.mean(axis=1), axis=0).div(medians.std(axis=1).replace(0, np.nan), axis=0)
    height = max(6, 0.32 * len(top_features) + 2)
    plt.figure(figsize=(8, height))
    sns.heatmap(z, cmap="vlag", center=0, linewidths=0.5, cbar_kws={"label": "Row z-score"})
    plt.title("Top Dynamic Coupling Features by Healthy vs Insulin Effect Size")
    plt.xlabel("")
    plt.ylabel("")
    plt.tight_layout()
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(figure_path, dpi=200)
    plt.close()
    print(f"Wrote heatmap to {figure_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--figure", type=Path, default=DEFAULT_FIGURE)
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args()

    atlas = build_atlas(args.input, args.output)
    plot_top_heatmap(atlas, args.input, args.figure, top_n=args.top_n)

    print("\nTop adjusted severity trends:")
    cols = [
        "feature",
        "n",
        "adjusted_severity_coef",
        "p_adjusted_severity_fdr",
        "healthy_vs_insulin_d",
    ]
    print(atlas[cols].head(15).to_string(index=False))


if __name__ == "__main__":
    main()
