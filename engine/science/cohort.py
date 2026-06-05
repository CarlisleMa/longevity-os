"""Cohort comparison framework.

Stratified comparison of numeric features across study_group levels,
with age/site adjustment, effect sizes, and FDR correction.

Usage:
    from scripts.cohort import compare_groups, compare_all_features
    result = compare_groups(fm, "hba1c")
    summary = compare_all_features(fm)
"""

import numpy as np
import pandas as pd
from scipy import stats as sp_stats


def compare_groups(
    fm: pd.DataFrame,
    feature: str,
    group_col: str = "study_group",
    adjust_for: list[str] | None = None,
) -> dict:
    """Compare a feature across study groups.

    Args:
        fm: feature matrix (one row per person, indexed by person_id).
        feature: column name to compare.
        group_col: grouping column (default: study_group).
        adjust_for: covariates to adjust for (e.g., ["age"]). Uses OLS residuals.

    Returns dict with:
        group_stats: DataFrame with mean, std, median, n per group
        test: 'kruskal' or 'anova'
        statistic: test statistic
        pvalue: p-value
        effect_size: eta-squared (ANOVA) or epsilon-squared (Kruskal)
        pairwise: DataFrame of pairwise comparisons with Cohen's d
    """
    df = fm[[group_col, feature]].dropna()
    if adjust_for:
        for cov in adjust_for:
            if cov in fm.columns:
                cov_vals = fm.loc[df.index, cov]
                valid = cov_vals.notna()
                df = df[valid]
                cov_vals = cov_vals[valid]
                # Residualize: subtract OLS prediction from covariate
                slope, intercept = np.polyfit(cov_vals, df[feature], 1)
                df[feature] = df[feature] - (slope * cov_vals + intercept)

    groups = df[group_col].unique()
    group_data = {g: df[df[group_col] == g][feature].values for g in groups}

    # Group stats
    group_stats = df.groupby(group_col)[feature].agg(["mean", "std", "median", "count"])
    group_stats.columns = ["mean", "std", "median", "n"]

    # Normality check (Shapiro on each group, skip if n > 5000)
    normal = all(
        sp_stats.shapiro(v)[1] > 0.05 if len(v) < 5000 else False
        for v in group_data.values()
        if len(v) >= 3
    )

    # Omnibus test
    group_arrays = [v for v in group_data.values() if len(v) >= 2]
    if len(group_arrays) < 2:
        return {"group_stats": group_stats, "test": "insufficient_groups", "pvalue": np.nan}

    if normal:
        stat, pval = sp_stats.f_oneway(*group_arrays)
        test_name = "anova"
        # Eta-squared
        grand_mean = df[feature].mean()
        ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in group_arrays)
        ss_total = sum((df[feature] - grand_mean) ** 2)
        effect = ss_between / ss_total if ss_total > 0 else 0.0
    else:
        stat, pval = sp_stats.kruskal(*group_arrays)
        test_name = "kruskal"
        # Epsilon-squared for Kruskal-Wallis
        n = len(df)
        effect = (stat - len(group_arrays) + 1) / (n - len(group_arrays)) if n > len(group_arrays) else 0.0

    # Pairwise comparisons with Cohen's d
    pairwise_rows = []
    sorted_groups = sorted(groups)
    for i, g1 in enumerate(sorted_groups):
        for g2 in sorted_groups[i + 1:]:
            d1 = group_data[g1]
            d2 = group_data[g2]
            if len(d1) < 2 or len(d2) < 2:
                continue
            # Cohen's d (pooled SD)
            pooled_sd = np.sqrt(((len(d1) - 1) * d1.std() ** 2 + (len(d2) - 1) * d2.std() ** 2) / (len(d1) + len(d2) - 2))
            cohens_d = (d1.mean() - d2.mean()) / pooled_sd if pooled_sd > 0 else 0.0
            # Mann-Whitney U
            u_stat, u_pval = sp_stats.mannwhitneyu(d1, d2, alternative="two-sided")
            pairwise_rows.append({
                "group1": g1,
                "group2": g2,
                "cohens_d": round(cohens_d, 3),
                "mean_diff": round(d1.mean() - d2.mean(), 4),
                "u_stat": u_stat,
                "pvalue": u_pval,
            })

    pairwise = pd.DataFrame(pairwise_rows)

    return {
        "group_stats": group_stats,
        "test": test_name,
        "statistic": round(stat, 4),
        "pvalue": pval,
        "effect_size": round(effect, 4),
        "pairwise": pairwise,
    }


def compare_all_features(
    fm: pd.DataFrame,
    features: list[str] | None = None,
    group_col: str = "study_group",
    adjust_for: list[str] | None = None,
    fdr_alpha: float = 0.05,
) -> pd.DataFrame:
    """Compare all numeric features across groups with FDR correction.

    Args:
        fm: feature matrix.
        features: list of column names to compare. If None, uses all numeric columns
                  except demographics and booleans.
        group_col: grouping column.
        adjust_for: covariates for adjustment.
        fdr_alpha: FDR threshold for Benjamini-Hochberg correction.

    Returns DataFrame with one row per feature:
        feature, test, statistic, pvalue, pvalue_fdr, significant, effect_size,
        group means (one column per group)
    """
    if features is None:
        skip = {group_col, "clinical_site", "recommended_split", "study_visit_date"}
        features = [
            c for c in fm.select_dtypes(include=[np.number]).columns
            if c not in skip
        ]

    results = []
    for feat in features:
        res = compare_groups(fm, feat, group_col=group_col, adjust_for=adjust_for)
        if res.get("test") == "insufficient_groups":
            continue
        row = {
            "feature": feat,
            "test": res["test"],
            "statistic": res["statistic"],
            "pvalue": res["pvalue"],
            "effect_size": res["effect_size"],
        }
        # Add per-group means
        for g, stats in res["group_stats"].iterrows():
            short = _short_group_name(g)
            row[f"mean_{short}"] = round(stats["mean"], 3)
            row[f"n_{short}"] = int(stats["n"])
        results.append(row)

    df = pd.DataFrame(results)
    if df.empty:
        return df

    # Benjamini-Hochberg FDR
    pvals = df["pvalue"].values
    n = len(pvals)
    sorted_idx = np.argsort(pvals)
    sorted_pvals = pvals[sorted_idx]
    fdr_pvals = np.zeros(n)
    for i in range(n - 1, -1, -1):
        if i == n - 1:
            fdr_pvals[i] = sorted_pvals[i]
        else:
            fdr_pvals[i] = min(fdr_pvals[i + 1], sorted_pvals[i] * n / (i + 1))
    # Unsort
    fdr_result = np.zeros(n)
    fdr_result[sorted_idx] = fdr_pvals
    df["pvalue_fdr"] = fdr_result
    df["significant"] = df["pvalue_fdr"] < fdr_alpha

    df = df.sort_values("pvalue").reset_index(drop=True)
    return df


def _short_group_name(group: str) -> str:
    """Shorten study_group names for column headers."""
    mapping = {
        "healthy": "healthy",
        "pre_diabetes_lifestyle_controlled": "prediab",
        "oral_medication_and_or_non_insulin_injectable_medication_controlled": "oral_med",
        "insulin_dependent": "insulin",
    }
    return mapping.get(group, group[:10])


def site_bias_check(fm: pd.DataFrame, features: list[str] | None = None) -> pd.DataFrame:
    """Check for site bias: compare features across clinical_site."""
    return compare_all_features(fm, features=features, group_col="clinical_site")
