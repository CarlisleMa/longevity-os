"""Cross-dimensional analysis of multi-system aging.

Phase 3 of the aging clock study: concordance analysis, aging subtypes,
diabetes severity gradients, and predictive hierarchy across organ, functional,
and imaging aging clocks.

Usage:
    python -m scripts.cross_dimensional
"""

import sys
import warnings

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats as sp_stats
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests

from .config import RESULTS_DIR, result_path

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Constants ────────────────────────────────────────────────────────────────

FIGURES_DIR = RESULTS_DIR / "figures"

SYSTEM_CLOCKS = [
    "immune_inflammatory_age_accel",
    "metabolic_age_accel",
    "renal_age_accel",
    "hepatic_age_accel",
    "cardiovascular_age_accel",
    "hematologic_age_accel",
    "cognitive_age_accel",
]

FUNCTIONAL_CLOCKS = [
    "circadian_age_accel",
    "cgm_metabolic_age_accel",
    "autonomic_age_accel",
    "sleep_age_accel",
    "physical_age_accel",
    "environmental_age_accel",
]

IMAGING_CLOCKS = [
    "retinal_age_accel",
    "cardiac_age_accel",
]

ALL_CLOCKS = SYSTEM_CLOCKS + FUNCTIONAL_CLOCKS + IMAGING_CLOCKS

# Ordinal ordering of study groups (increasing diabetes severity)
GROUP_ORDER = [
    "healthy",
    "pre_diabetes_lifestyle_controlled",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled",
    "insulin_dependent",
]

GROUP_LABELS = {
    "healthy": "Healthy",
    "pre_diabetes_lifestyle_controlled": "Pre-diabetes",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": "Oral med",
    "insulin_dependent": "Insulin",
}


def _short_name(col: str) -> str:
    """Strip _age_accel suffix for display."""
    return col.replace("_age_accel", "")


def _available_clocks(df: pd.DataFrame) -> list[str]:
    """Return the subset of ALL_CLOCKS actually present in df."""
    return [c for c in ALL_CLOCKS if c in df.columns]


def _fdr_correct(pvals: np.ndarray, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Benjamini-Hochberg FDR correction.

    Returns (rejected, pvals_corrected).
    """
    mask = np.isfinite(pvals)
    corrected = np.full_like(pvals, np.nan)
    rejected = np.full(len(pvals), False)
    if mask.sum() == 0:
        return rejected, corrected
    rej, pval_c, _, _ = multipletests(pvals[mask], alpha=alpha, method="fdr_bh")
    corrected[mask] = pval_c
    rejected[mask] = rej
    return rejected, corrected


def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d with pooled standard deviation."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return np.nan
    pooled_sd = np.sqrt(((na - 1) * a.std(ddof=1) ** 2 + (nb - 1) * b.std(ddof=1) ** 2)
                        / (na + nb - 2))
    if pooled_sd == 0:
        return 0.0
    return (a.mean() - b.mean()) / pooled_sd


# ── 3a. Concordance Matrix ───────────────────────────────────────────────────

def concordance_matrix(age_accel_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Spearman correlation matrix of all AgeAccel dimensions.

    Returns (rho_matrix, pval_matrix), both indexed/columned by clock names.
    Saves results/clocks/concordance_matrix.csv and results/figures/concordance_heatmap.png.
    """
    clocks = _available_clocks(age_accel_df)
    data = age_accel_df[clocks].dropna()
    n = len(clocks)

    rho = pd.DataFrame(np.ones((n, n)), index=clocks, columns=clocks)
    pval = pd.DataFrame(np.zeros((n, n)), index=clocks, columns=clocks)

    for i in range(n):
        for j in range(i + 1, n):
            r, p = sp_stats.spearmanr(data[clocks[i]], data[clocks[j]])
            rho.iloc[i, j] = rho.iloc[j, i] = r
            pval.iloc[i, j] = pval.iloc[j, i] = p

    # Save correlation matrix
    rho_out = rho.copy()
    rho_out.index = [_short_name(c) for c in rho_out.index]
    rho_out.columns = [_short_name(c) for c in rho_out.columns]
    rho_out.to_csv(result_path("concordance_matrix.csv"), float_format="%.4f")

    # Clustermap visualization
    fig_path = FIGURES_DIR / "concordance_heatmap.png"
    mask = np.triu(np.ones_like(rho, dtype=bool), k=1)

    display_rho = rho.copy()
    display_rho.index = [_short_name(c) for c in display_rho.index]
    display_rho.columns = [_short_name(c) for c in display_rho.columns]

    g = sns.clustermap(
        display_rho,
        method="average",
        metric="euclidean",
        cmap="RdBu_r",
        center=0,
        vmin=-1,
        vmax=1,
        annot=True,
        fmt=".2f",
        figsize=(10, 9),
        linewidths=0.5,
        dendrogram_ratio=(0.12, 0.12),
        cbar_kws={"label": "Spearman rho", "shrink": 0.8},
    )
    g.ax_heatmap.set_xlabel("")
    g.ax_heatmap.set_ylabel("")
    g.fig.suptitle("Cross-Dimensional AgeAccel Concordance", y=1.02, fontsize=14)
    g.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close("all")

    print(f"  Concordance matrix saved: {RESULTS_DIR / 'concordance_matrix.csv'}")
    print(f"  Heatmap saved: {fig_path}")

    # Summary stats
    upper_vals = rho.values[np.triu_indices(n, k=1)]
    print(f"  Mean pairwise rho = {upper_vals.mean():.3f} "
          f"(range {upper_vals.min():.3f} to {upper_vals.max():.3f})")

    return rho, pval


# ── 3b. Per-Person Concordance Score ─────────────────────────────────────────

def person_concordance(
    age_accel_df: pd.DataFrame,
    study_group: pd.Series | None = None,
) -> pd.Series:
    """Per-person concordance = SD of their AgeAccels across all dimensions.

    Low SD  = concordant aging (all organs aging at similar rate).
    High SD = discordant aging (some fast, some slow).

    Returns Series indexed by person_id.
    """
    clocks = _available_clocks(age_accel_df)
    concordance = age_accel_df[clocks].std(axis=1)
    concordance.name = "concordance_sd"

    print(f"  Concordance SD: mean={concordance.mean():.3f}, "
          f"median={concordance.median():.3f}, "
          f"IQR=[{concordance.quantile(0.25):.3f}, {concordance.quantile(0.75):.3f}]")

    # Compare across study groups if available
    if study_group is not None:
        aligned = pd.DataFrame({"concordance_sd": concordance, "study_group": study_group}).dropna()
        groups = [
            aligned.loc[aligned["study_group"] == g, "concordance_sd"].values
            for g in GROUP_ORDER
            if g in aligned["study_group"].values
        ]
        present_labels = [
            GROUP_LABELS[g] for g in GROUP_ORDER
            if g in aligned["study_group"].values
        ]
        if len(groups) >= 2:
            h_stat, kw_p = sp_stats.kruskal(*groups)
            n_total = sum(len(g) for g in groups)
            k = len(groups)
            eps_sq = (h_stat - k + 1) / (n_total - k) if n_total > k else 0.0
            print(f"  Kruskal-Wallis across groups: H={h_stat:.2f}, p={kw_p:.4g}, "
                  f"eps^2={eps_sq:.4f}")
            for label, g in zip(present_labels, groups):
                print(f"    {label}: mean={g.mean():.3f}, n={len(g)}")

    return concordance


# ── 3c. Aging Subtypes via Clustering ────────────────────────────────────────

def aging_subtypes(
    age_accel_df: pd.DataFrame,
    study_group: pd.Series | None = None,
    feature_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Cluster participants by multi-dimensional AgeAccel profile.

    Returns DataFrame with columns: cluster, plus one column per clock.
    Saves results/clocks/aging_subtypes.csv and results/figures/aging_subtypes_umap.png.
    """
    clocks = _available_clocks(age_accel_df)
    data = age_accel_df[clocks].dropna()
    person_ids = data.index

    # Winsorize extreme outliers using robust IQR-based clipping before clustering.
    # This prevents a single extreme value from dominating the SD and clustering.
    for c in clocks:
        col = data[c]
        q1, q3 = col.quantile(0.25), col.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 5 * iqr
        upper = q3 + 5 * iqr
        n_clipped = ((col < lower) | (col > upper)).sum()
        if n_clipped > 0:
            print(f"    Winsorized {n_clipped} outlier(s) in {_short_name(c)}")
        data[c] = col.clip(lower, upper)

    # Standardize
    scaler = StandardScaler()
    X = scaler.fit_transform(data.values)

    # Try k=3..6, pick best silhouette
    k_range = range(3, 7)
    silhouettes = {}
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=20, random_state=42)
        labels = km.fit_predict(X)
        sil = silhouette_score(X, labels)
        silhouettes[k] = sil
        print(f"    k={k}: silhouette={sil:.3f}")

    best_k = max(silhouettes, key=silhouettes.get)
    print(f"  Best k={best_k} (silhouette={silhouettes[best_k]:.3f})")

    # Fit final model
    km_final = KMeans(n_clusters=best_k, n_init=20, random_state=42)
    labels_final = km_final.fit_predict(X)

    # Build output
    subtypes = pd.DataFrame({"cluster": labels_final}, index=person_ids)
    for c in clocks:
        subtypes[c] = data[c]

    # Characterize each cluster
    print(f"\n  Cluster characterization ({best_k} clusters):")
    cluster_profiles = []
    for cl in range(best_k):
        mask = subtypes["cluster"] == cl
        n_cl = mask.sum()
        profile = {"cluster": cl, "n": n_cl}
        for c in clocks:
            profile[f"mean_{_short_name(c)}"] = subtypes.loc[mask, c].mean()
        cluster_profiles.append(profile)

        # Identify top accelerated and decelerated dimensions
        means = {_short_name(c): subtypes.loc[mask, c].mean() for c in clocks}
        sorted_dims = sorted(means.items(), key=lambda x: x[1], reverse=True)
        top_high = sorted_dims[0]
        top_low = sorted_dims[-1]
        print(f"    Cluster {cl} (n={n_cl}): "
              f"highest={top_high[0]} ({top_high[1]:+.2f}), "
              f"lowest={top_low[0]} ({top_low[1]:+.2f})")

    profiles_df = pd.DataFrame(cluster_profiles)

    # Chi-squared: do clusters align with study_group?
    if study_group is not None:
        aligned = subtypes[["cluster"]].join(study_group, how="inner")
        if not aligned.empty:
            ct = pd.crosstab(aligned["cluster"], aligned["study_group"])
            chi2, chi_p, dof, _ = sp_stats.chi2_contingency(ct)
            cramers_v = np.sqrt(chi2 / (ct.sum().sum() * (min(ct.shape) - 1)))
            print(f"\n  Chi-squared (cluster x study_group): "
                  f"chi2={chi2:.2f}, p={chi_p:.4g}, Cramer's V={cramers_v:.3f}")
            # Print cross-tabulation with percentages
            ct_pct = ct.div(ct.sum(axis=1), axis=0) * 100
            ct_pct.columns = [GROUP_LABELS.get(c, c) for c in ct_pct.columns]
            print("  Study group distribution per cluster (%):")
            for line in ct_pct.round(1).to_string().split("\n"):
                print(f"    {line}")

    # Demographics per cluster if feature_df is available
    if feature_df is not None and "age" in feature_df.columns:
        age_by_cluster = subtypes[["cluster"]].join(feature_df[["age"]], how="inner")
        for cl in range(best_k):
            m = age_by_cluster.loc[age_by_cluster["cluster"] == cl, "age"]
            print(f"    Cluster {cl} age: mean={m.mean():.1f}, sd={m.std():.1f}")

    # 2D embedding for visualization (UMAP > t-SNE > PCA fallback)
    embed_label = "PCA"
    try:
        import umap  # noqa: F401
        reducer = umap.UMAP(n_components=2, random_state=42, n_neighbors=30, min_dist=0.3)
        embedding = reducer.fit_transform(X)
        embed_label = "UMAP"
    except ImportError:
        from sklearn.manifold import TSNE
        if len(X) > 500:
            tsne = TSNE(n_components=2, random_state=42, perplexity=30, max_iter=1000)
            embedding = tsne.fit_transform(X)
            embed_label = "t-SNE"
        else:
            from sklearn.decomposition import PCA
            pca = PCA(n_components=2, random_state=42)
            embedding = pca.fit_transform(X)
            embed_label = f"PCA (var={pca.explained_variance_ratio_.sum():.1%})"

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Panel 1: colored by cluster
    palette_cluster = sns.color_palette("Set2", best_k)
    for cl in range(best_k):
        mask = labels_final == cl
        axes[0].scatter(embedding[mask, 0], embedding[mask, 1],
                        c=[palette_cluster[cl]], label=f"Cluster {cl}",
                        alpha=0.6, s=12, edgecolors="none")
    axes[0].legend(fontsize=9, markerscale=2)
    axes[0].set_title(f"Aging Subtypes ({embed_label})")
    axes[0].set_xlabel(f"{embed_label.split()[0]} 1")
    axes[0].set_ylabel(f"{embed_label.split()[0]} 2")

    # Panel 2: colored by study group
    if study_group is not None:
        aligned_sg = study_group.reindex(person_ids).dropna()
        palette_sg = sns.color_palette("viridis", len(GROUP_ORDER))
        for i, g in enumerate(GROUP_ORDER):
            mask = (aligned_sg == g).reindex(person_ids, fill_value=False).values
            if mask.sum() > 0:
                axes[1].scatter(embedding[mask, 0], embedding[mask, 1],
                                c=[palette_sg[i]], label=GROUP_LABELS[g],
                                alpha=0.5, s=12, edgecolors="none")
        axes[1].legend(fontsize=9, markerscale=2)
        axes[1].set_title(f"Study Group ({embed_label})")
        axes[1].set_xlabel(f"{embed_label.split()[0]} 1")
        axes[1].set_ylabel(f"{embed_label.split()[0]} 2")
    else:
        axes[1].set_visible(False)

    fig.tight_layout()
    fig_path = FIGURES_DIR / "aging_subtypes_umap.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close("all")

    # Save cluster assignments
    out_path = result_path("aging_subtypes.csv")
    subtypes.to_csv(out_path)

    print(f"\n  Subtypes saved: {out_path}")
    print(f"  Visualization saved: {fig_path}")

    return subtypes


# ── 3d. Diabetes Severity Gradient ───────────────────────────────────────────

def _jonckheere_terpstra(groups: list[np.ndarray]) -> tuple[float, float]:
    """Jonckheere-Terpstra trend test for ordered groups.

    H0: no trend across groups.
    Returns (J statistic, two-sided p-value).
    """
    k = len(groups)
    J = 0.0
    for i in range(k - 1):
        for j in range(i + 1, k):
            for xi in groups[i]:
                for xj in groups[j]:
                    if xj > xi:
                        J += 1
                    elif xj == xi:
                        J += 0.5

    # Expected value and variance under H0
    ns = [len(g) for g in groups]
    N = sum(ns)
    E_J = (N ** 2 - sum(n ** 2 for n in ns)) / 4

    # Variance (no-ties formula)
    sum_n2 = sum(n ** 2 for n in ns)
    sum_n3 = sum(n ** 3 for n in ns)
    var_num = (N ** 2 * (2 * N + 3) - sum(n ** 2 * (2 * n + 3) for n in ns))
    V_J = var_num / 72

    if V_J <= 0:
        return J, 1.0

    Z = (J - E_J) / np.sqrt(V_J)
    p = 2 * sp_stats.norm.sf(abs(Z))
    return float(Z), float(p)


def diabetes_gradient(
    age_accel_df: pd.DataFrame,
    study_group: pd.Series,
) -> pd.DataFrame:
    """For each AgeAccel dimension, test gradient across 4 study groups.

    Saves results/clocks/diabetes_gradient.csv and results/figures/diabetes_gradient_forest.png.
    """
    clocks = _available_clocks(age_accel_df)
    aligned = age_accel_df[clocks].join(study_group, how="inner").dropna(subset=["study_group"])

    results = []
    for clock in clocks:
        sub = aligned[[clock, "study_group"]].dropna()
        groups = [
            sub.loc[sub["study_group"] == g, clock].values
            for g in GROUP_ORDER
            if g in sub["study_group"].values
        ]
        present_groups = [
            g for g in GROUP_ORDER
            if g in sub["study_group"].values
        ]

        if len(groups) < 2:
            continue

        # Kruskal-Wallis
        h_stat, kw_p = sp_stats.kruskal(*groups)
        n_total = sum(len(g) for g in groups)
        k = len(groups)
        eps_sq = (h_stat - k + 1) / (n_total - k) if n_total > k else 0.0

        # Jonckheere-Terpstra trend test
        jt_z, jt_p = _jonckheere_terpstra(groups)

        # Group means
        group_means = {GROUP_LABELS[g]: grp.mean() for g, grp in zip(present_groups, groups)}

        # Pairwise Cohen's d between adjacent groups
        adjacent_d = {}
        for i in range(len(groups) - 1):
            pair = f"{GROUP_LABELS[present_groups[i]]} vs {GROUP_LABELS[present_groups[i+1]]}"
            adjacent_d[pair] = _cohens_d(groups[i], groups[i + 1])

        # Overall gradient: Cohen's d from first to last group
        overall_d = _cohens_d(groups[0], groups[-1])

        row = {
            "clock": _short_name(clock),
            "kruskal_H": round(h_stat, 2),
            "kruskal_p": kw_p,
            "epsilon_sq": round(eps_sq, 4),
            "jt_Z": round(jt_z, 2),
            "jt_p": jt_p,
            "overall_d": round(overall_d, 3),
        }
        for label, mean_val in group_means.items():
            row[f"mean_{label}"] = round(mean_val, 3)
        for pair, d in adjacent_d.items():
            row[f"d_{pair}"] = round(d, 3) if np.isfinite(d) else np.nan

        results.append(row)

    df = pd.DataFrame(results)
    if df.empty:
        print("  No gradient results (insufficient data).")
        return df

    # FDR correction on Kruskal-Wallis p-values
    rejected_kw, fdr_kw = _fdr_correct(df["kruskal_p"].values)
    df["kruskal_p_fdr"] = fdr_kw
    df["kw_significant"] = rejected_kw

    # FDR correction on JT p-values
    rejected_jt, fdr_jt = _fdr_correct(df["jt_p"].values)
    df["jt_p_fdr"] = fdr_jt
    df["jt_significant"] = rejected_jt

    # Rank by gradient steepness (absolute overall Cohen's d)
    df = df.sort_values("overall_d", key=abs, ascending=False).reset_index(drop=True)

    # Identify dimensions orthogonal to diabetes
    orthogonal = df[~df["kw_significant"]]
    if not orthogonal.empty:
        print(f"\n  Dimensions ORTHOGONAL to diabetes (non-significant gradient):")
        for _, r in orthogonal.iterrows():
            print(f"    {r['clock']}: H={r['kruskal_H']}, p_fdr={r['kruskal_p_fdr']:.3f}")
    else:
        print(f"\n  All dimensions show significant diabetes gradient (FDR < 0.05)")

    # Save
    out_path = result_path("diabetes_gradient.csv")
    df.to_csv(out_path, index=False, float_format="%.4f")

    # Forest plot
    _plot_diabetes_forest(df)

    print(f"\n  Gradient analysis saved: {out_path}")
    return df


def _plot_diabetes_forest(df: pd.DataFrame) -> None:
    """Forest plot of diabetes gradient effect sizes."""
    fig, ax = plt.subplots(figsize=(10, max(6, len(df) * 0.5 + 1)))

    # Sort by overall_d for display
    plot_df = df.sort_values("overall_d").reset_index(drop=True)
    y_pos = range(len(plot_df))

    colors = ["#d62728" if sig else "#7f7f7f" for sig in plot_df["jt_significant"]]
    ax.barh(y_pos, plot_df["overall_d"], color=colors, height=0.6, alpha=0.8)
    ax.axvline(0, color="black", linewidth=0.8, linestyle="-")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(plot_df["clock"])
    ax.set_xlabel("Cohen's d (Healthy vs Insulin-dependent)")
    ax.set_title("Diabetes Severity Gradient by Aging Dimension")

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#d62728", alpha=0.8, label="Significant trend (JT, FDR < 0.05)"),
        Patch(facecolor="#7f7f7f", alpha=0.8, label="Non-significant"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9)

    fig.tight_layout()
    fig_path = FIGURES_DIR / "diabetes_gradient_forest.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close("all")
    print(f"  Forest plot saved: {fig_path}")


# ── 3e. Predictive Hierarchy ─────────────────────────────────────────────────

def predictive_hierarchy(
    age_accel_df: pd.DataFrame,
    study_group: pd.Series,
    allostatic_load: pd.Series | None = None,
    concordance_scores: pd.Series | None = None,
) -> pd.DataFrame:
    """Which AgeAccel dimensions best predict clinical outcomes?

    Saves results/clocks/predictive_hierarchy.csv.
    """
    from statsmodels.miscmodels.ordinal_model import OrderedModel
    import statsmodels.api as sm

    clocks = _available_clocks(age_accel_df)
    rows = []

    # Merge everything into a single frame
    merged = age_accel_df[clocks].copy()
    merged["study_group"] = study_group

    # Encode study_group as ordinal integer
    group_map = {g: i for i, g in enumerate(GROUP_ORDER)}
    merged["group_ordinal"] = merged["study_group"].map(group_map)

    # Add age from feature_matrix if we can find it
    fm_path = result_path("feature_matrix.parquet")
    if fm_path.exists():
        fm = pd.read_parquet(fm_path, columns=["age"])
        merged = merged.join(fm[["age"]], how="left")
    else:
        merged["age"] = np.nan

    if allostatic_load is not None:
        merged["allostatic_load"] = allostatic_load
    if concordance_scores is not None:
        merged["concordance_sd"] = concordance_scores

    has_age = merged["age"].notna().sum() > 100

    # ── 1. Ordinal regression: study_group ~ each AgeAccel (+ age) ──
    print("\n  1. Ordinal regression: study_group ~ AgeAccel (+age)")
    for clock in clocks:
        cols = [clock]
        if has_age:
            cols.append("age")
        sub = merged[cols + ["group_ordinal"]].dropna()
        if len(sub) < 50:
            continue

        y = sub["group_ordinal"]
        X = sub[cols]

        try:
            model = OrderedModel(y, X, distr="logit")
            res = model.fit(method="bfgs", disp=False, maxiter=500)
            # Pseudo-R^2 (McFadden)
            pseudo_r2 = 1 - (res.llf / res.llnull) if res.llnull != 0 else np.nan
            # Coefficient and p-value for the clock
            coef = res.params[clock]
            pval = res.pvalues[clock]
        except Exception:
            pseudo_r2 = np.nan
            coef = np.nan
            pval = np.nan

        rows.append({
            "clock": _short_name(clock),
            "outcome": "study_group_ordinal",
            "model": "ordinal_logit",
            "coefficient": round(coef, 4) if np.isfinite(coef) else np.nan,
            "pvalue": pval,
            "pseudo_r2": round(pseudo_r2, 4) if np.isfinite(pseudo_r2) else np.nan,
        })

    # ── 2. Linear regression: allostatic_load ~ each AgeAccel (+ age) ──
    if allostatic_load is not None and merged["allostatic_load"].notna().sum() > 50:
        print("  2. Linear regression: allostatic_load ~ AgeAccel (+age)")
        for clock in clocks:
            cols = [clock]
            if has_age:
                cols.append("age")
            sub = merged[cols + ["allostatic_load"]].dropna()
            if len(sub) < 50:
                continue

            y = sub["allostatic_load"]
            X = sm.add_constant(sub[cols])

            try:
                res = sm.OLS(y, X).fit()
                rows.append({
                    "clock": _short_name(clock),
                    "outcome": "allostatic_load",
                    "model": "OLS",
                    "coefficient": round(res.params[clock], 4),
                    "pvalue": res.pvalues[clock],
                    "pseudo_r2": round(res.rsquared, 4),
                })
            except Exception:
                pass
    else:
        print("  2. Skipping allostatic_load regression (data unavailable)")

    # ── 3. Linear regression: concordance_sd ~ each AgeAccel (+ age) ──
    if concordance_scores is not None and merged["concordance_sd"].notna().sum() > 50:
        print("  3. Linear regression: concordance_sd ~ AgeAccel (+age)")
        for clock in clocks:
            cols = [clock]
            if has_age:
                cols.append("age")
            sub = merged[cols + ["concordance_sd"]].dropna()
            if len(sub) < 50:
                continue

            y = sub["concordance_sd"]
            X = sm.add_constant(sub[cols])

            try:
                res = sm.OLS(y, X).fit()
                rows.append({
                    "clock": _short_name(clock),
                    "outcome": "concordance_sd",
                    "model": "OLS",
                    "coefficient": round(res.params[clock], 4),
                    "pvalue": res.pvalues[clock],
                    "pseudo_r2": round(res.rsquared, 4),
                })
            except Exception:
                pass
    else:
        print("  3. Skipping concordance_sd regression (data unavailable)")

    # ── 4. Multivariate ordinal: study_group ~ ALL AgeAccels (+ age) ──
    print("  4. Multivariate ordinal: study_group ~ ALL AgeAccels (+age)")
    mv_cols = clocks.copy()
    if has_age:
        mv_cols.append("age")
    sub = merged[mv_cols + ["group_ordinal"]].dropna()
    if len(sub) >= 50:
        y = sub["group_ordinal"]
        X = sub[mv_cols]

        try:
            model = OrderedModel(y, X, distr="logit")
            res = model.fit(method="bfgs", disp=False, maxiter=500)
            pseudo_r2 = 1 - (res.llf / res.llnull) if res.llnull != 0 else np.nan

            for clock in clocks:
                coef = res.params.get(clock, np.nan)
                pval = res.pvalues.get(clock, np.nan)
                rows.append({
                    "clock": _short_name(clock),
                    "outcome": "study_group_multivariate",
                    "model": "ordinal_logit_full",
                    "coefficient": round(coef, 4) if np.isfinite(coef) else np.nan,
                    "pvalue": pval,
                    "pseudo_r2": round(pseudo_r2, 4) if np.isfinite(pseudo_r2) else np.nan,
                })
            print(f"    Full model pseudo-R^2 = {pseudo_r2:.4f}")
        except Exception as e:
            print(f"    Multivariate model failed: {e}")

    # Build output DataFrame
    df = pd.DataFrame(rows)
    if df.empty:
        print("  No predictive hierarchy results.")
        return df

    # FDR correction within each outcome
    for outcome in df["outcome"].unique():
        mask = df["outcome"] == outcome
        pvals = df.loc[mask, "pvalue"].values
        rejected, corrected = _fdr_correct(pvals)
        df.loc[mask, "pvalue_fdr"] = corrected
        df.loc[mask, "significant"] = rejected

    # Rank by pseudo_r2 within each outcome
    df = df.sort_values(["outcome", "pseudo_r2"], ascending=[True, False]).reset_index(drop=True)

    out_path = result_path("predictive_hierarchy.csv")
    df.to_csv(out_path, index=False, float_format="%.4f")
    print(f"\n  Predictive hierarchy saved: {out_path}")

    # Print top predictor per outcome
    for outcome in df["outcome"].unique():
        sub = df[df["outcome"] == outcome]
        if not sub.empty:
            best = sub.iloc[0]
            print(f"    Best for {outcome}: {best['clock']} "
                  f"(R^2={best['pseudo_r2']}, coef={best['coefficient']}, "
                  f"p_fdr={best.get('pvalue_fdr', 'N/A')})")

    return df


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    """Run all cross-dimensional analyses."""
    print("=" * 70)
    print("Phase 3: Cross-Dimensional Analysis of Multi-System Aging")
    print("=" * 70)

    # ── Load inputs ──────────────────────────────────────────────────────
    accel_path = result_path("age_accel.parquet")
    if not accel_path.exists():
        print(f"\nERROR: {accel_path} does not exist.")
        print("Phase 2 must complete first to generate age acceleration residuals.")
        print("Expected columns: " + ", ".join(ALL_CLOCKS))
        sys.exit(1)

    age_accel_df = pd.read_parquet(accel_path)

    # Load imaging clocks and join only their age-acceleration columns.
    for label, fname in [("retinal", "retinal_age_accel.parquet"),
                         ("cardiac", "cardiac_age_accel.parquet")]:
        p = RESULTS_DIR / fname
        if p.exists():
            img_df = pd.read_parquet(p)
            new_cols = [
                c for c in img_df.columns
                if c in IMAGING_CLOCKS and c not in age_accel_df.columns
            ]
            if new_cols:
                age_accel_df = age_accel_df.join(img_df[new_cols], how="left")
                print(f"  Joined {label} clock: {new_cols}")

    clocks = _available_clocks(age_accel_df)
    system_present = [c for c in SYSTEM_CLOCKS if c in clocks]
    functional_present = [c for c in FUNCTIONAL_CLOCKS if c in clocks]
    imaging_present = [c for c in IMAGING_CLOCKS if c in clocks]
    print(f"\nLoaded age acceleration data: {age_accel_df.shape[0]} participants, "
          f"{len(clocks)} clocks")
    print(f"  System clocks ({len(system_present)}): "
          + ", ".join(_short_name(c) for c in system_present))
    print(f"  Functional clocks ({len(functional_present)}): "
          + ", ".join(_short_name(c) for c in functional_present))
    print(f"  Imaging clocks ({len(imaging_present)}): "
          + ", ".join(_short_name(c) for c in imaging_present))

    if len(clocks) < 2:
        print("\nERROR: Need at least 2 age acceleration dimensions for cross-dimensional analysis.")
        sys.exit(1)

    # Load feature matrix for study_group and age
    fm_path = result_path("feature_matrix.parquet")
    study_group = None
    feature_df = None
    if fm_path.exists():
        feature_df = pd.read_parquet(fm_path)
        study_group = feature_df["study_group"]
        print(f"Loaded feature matrix: {feature_df.shape}")
    else:
        print("WARNING: feature_matrix.parquet not found. "
              "Analyses requiring study_group will be skipped.")

    # Load allostatic load if available
    allostatic_load = None
    clinical_path = result_path("clinical_scores.parquet")
    if clinical_path.exists():
        clinical = pd.read_parquet(clinical_path)
        if "allostatic_load" in clinical.columns:
            allostatic_load = clinical["allostatic_load"]
            print(f"Loaded allostatic load: {allostatic_load.notna().sum()} values")
    else:
        print("INFO: clinical_scores.parquet not found. "
              "Allostatic load analysis will be skipped.")

    # Create figures directory
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # ── 3a. Concordance Matrix ───────────────────────────────────────────
    print("\n" + "-" * 70)
    print("3a. Concordance Matrix")
    print("-" * 70)
    rho, pval_mat = concordance_matrix(age_accel_df)

    # ── 3b. Per-Person Concordance ───────────────────────────────────────
    print("\n" + "-" * 70)
    print("3b. Per-Person Concordance Score")
    print("-" * 70)
    concordance_scores = person_concordance(age_accel_df, study_group=study_group)

    # ── 3c. Aging Subtypes ───────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("3c. Aging Subtypes via Clustering")
    print("-" * 70)
    subtypes = aging_subtypes(age_accel_df, study_group=study_group, feature_df=feature_df)

    # ── 3d. Diabetes Severity Gradient ───────────────────────────────────
    if study_group is not None:
        print("\n" + "-" * 70)
        print("3d. Diabetes Severity Gradient")
        print("-" * 70)
        gradient_df = diabetes_gradient(age_accel_df, study_group)
    else:
        print("\n  Skipping 3d (no study_group data)")
        gradient_df = pd.DataFrame()

    # ── 3e. Predictive Hierarchy ─────────────────────────────────────────
    if study_group is not None:
        print("\n" + "-" * 70)
        print("3e. Predictive Hierarchy")
        print("-" * 70)
        hierarchy_df = predictive_hierarchy(
            age_accel_df, study_group,
            allostatic_load=allostatic_load,
            concordance_scores=concordance_scores,
        )
    else:
        print("\n  Skipping 3e (no study_group data)")
        hierarchy_df = pd.DataFrame()

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Phase 3 Summary")
    print("=" * 70)

    outputs = {
        "concordance_matrix.csv": result_path("concordance_matrix.csv"),
        "aging_subtypes.csv": result_path("aging_subtypes.csv"),
        "diabetes_gradient.csv": result_path("diabetes_gradient.csv"),
        "predictive_hierarchy.csv": result_path("predictive_hierarchy.csv"),
        "concordance_heatmap.png": FIGURES_DIR / "concordance_heatmap.png",
        "aging_subtypes_umap.png": FIGURES_DIR / "aging_subtypes_umap.png",
        "diabetes_gradient_forest.png": FIGURES_DIR / "diabetes_gradient_forest.png",
    }

    print("\nOutput files:")
    for name, path in outputs.items():
        status = "OK" if path.exists() else "not created"
        print(f"  {name}: {status}")

    print("\nDone.")


if __name__ == "__main__":
    main()
