"""
H-NEW05: Glucose complexity (multiscale entropy proxy) predicts allostatic load
and frailty index beyond HbA1c.

Uses EXISTING coupling_features.parquet (glucose_ms_entropy_s1..s72) and
clinical_scores.parquet. No new time-series computation needed.

Critic guidance:
  - Test existing Shannon entropy proxy FIRST
  - Report which specific scales carry the incremental prediction
  - Use cross-validated incremental R² (not in-sample)
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.preprocessing import StandardScaler

from scripts.config import RESULTS_DIR, result_path

warnings.filterwarnings("ignore")

STUDY_GROUP_ORDER = (
    "healthy",
    "pre_diabetes_lifestyle_controlled",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled",
    "insulin_dependent",
)

ENTROPY_COLS = [
    "glucose_ms_entropy_s1",   # 5 min
    "glucose_ms_entropy_s3",   # 15 min
    "glucose_ms_entropy_s12",  # 1 h
    "glucose_ms_entropy_s36",  # 3 h
    "glucose_ms_entropy_s72",  # 6 h
]

OUTCOMES = ["allostatic_load", "frailty_index", "homeostatic_dysregulation"]


def load_data():
    """Merge coupling features + clinical scores + participant index."""
    cf = pd.read_parquet(result_path("coupling_features.parquet"))
    cs = pd.read_parquet(result_path("clinical_scores.parquet"))
    pi = pd.read_parquet(result_path("participant_index.parquet"))
    fm = pd.read_parquet(result_path("feature_matrix.parquet"))

    # Merge
    df = cf[ENTROPY_COLS].join(cs[OUTCOMES], how="inner")
    df = df.join(pi[["age", "clinical_site", "study_group"]], how="inner")
    df = df.join(fm[["hba1c", "bmi"]], how="inner")
    return df.dropna(subset=ENTROPY_COLS + OUTCOMES + ["hba1c", "age"])


def severity_gradient(df: pd.DataFrame) -> pd.DataFrame:
    """Test each entropy feature for severity gradient (Kruskal-Wallis + trend)."""
    from statsmodels.stats.multitest import multipletests

    rows = []
    for col in ENTROPY_COLS:
        groups = [df.loc[df["study_group"] == g, col].dropna() for g in STUDY_GROUP_ORDER]
        groups = [g for g in groups if len(g) > 10]
        if len(groups) < 3:
            continue
        kw_stat, kw_p = stats.kruskal(*groups)
        # Ordinal trend
        ordinal = df["study_group"].map({g: i for i, g in enumerate(STUDY_GROUP_ORDER)})
        r, p_trend = stats.spearmanr(ordinal.dropna(), df.loc[ordinal.dropna().index, col])
        medians = {g: df.loc[df["study_group"] == g, col].median() for g in STUDY_GROUP_ORDER}
        rows.append({
            "feature": col,
            "kw_stat": kw_stat,
            "kw_p": kw_p,
            "trend_r": r,
            "trend_p": p_trend,
            **{f"median_{g[:8]}": v for g, v in medians.items()},
        })

    result = pd.DataFrame(rows)
    if len(result) > 0:
        _, fdr, _, _ = multipletests(result["kw_p"], method="fdr_bh")
        result["fdr_p"] = fdr
    return result


def incremental_prediction(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-validated incremental R² of entropy features beyond HbA1c + confounders."""
    results = []
    confounders = ["age", "hba1c", "bmi"]
    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True)
    X_base = pd.concat([df[confounders], site_dummies], axis=1).astype(float)

    # Drop rows with any NaN in base features or entropy features
    all_cols = list(X_base.columns) + ENTROPY_COLS + OUTCOMES
    valid_idx = df.dropna(subset=ENTROPY_COLS + OUTCOMES + confounders).index
    X_base = X_base.loc[valid_idx]
    df_valid = df.loc[valid_idx]

    ordinal = df_valid["study_group"].map({g: i for i, g in enumerate(STUDY_GROUP_ORDER)})
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    scaler_base = StandardScaler()
    X_base_scaled = scaler_base.fit_transform(X_base.fillna(0))

    for outcome in OUTCOMES:
        y = df_valid[outcome].values

        # Model A: confounders only
        pred_a = cross_val_predict(Ridge(alpha=1.0), X_base_scaled, y, cv=cv.split(X_base_scaled, ordinal))
        r2_a = 1 - np.sum((y - pred_a) ** 2) / np.sum((y - y.mean()) ** 2)

        # Model B: confounders + ALL entropy features
        X_full = np.column_stack([X_base_scaled, StandardScaler().fit_transform(df_valid[ENTROPY_COLS].values)])
        pred_b = cross_val_predict(Ridge(alpha=1.0), X_full, y, cv=cv.split(X_full, ordinal))
        r2_b = 1 - np.sum((y - pred_b) ** 2) / np.sum((y - y.mean()) ** 2)

        # Per-scale incremental: confounders + single entropy feature
        for ecol in ENTROPY_COLS:
            X_single = np.column_stack([X_base_scaled, StandardScaler().fit_transform(df_valid[[ecol]].values)])
            pred_s = cross_val_predict(Ridge(alpha=1.0), X_single, y, cv=cv.split(X_single, ordinal))
            r2_s = 1 - np.sum((y - pred_s) ** 2) / np.sum((y - y.mean()) ** 2)
            results.append({
                "outcome": outcome,
                "model": f"base+{ecol}",
                "r2_cv": r2_s,
                "delta_r2": r2_s - r2_a,
            })

        results.append({"outcome": outcome, "model": "base_only", "r2_cv": r2_a, "delta_r2": 0.0})
        results.append({"outcome": outcome, "model": "base+all_entropy", "r2_cv": r2_b, "delta_r2": r2_b - r2_a})

    return pd.DataFrame(results)


def partial_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """Partial correlation of each entropy feature with outcomes, adjusting for confounders."""
    from statsmodels.stats.multitest import multipletests

    confounders = ["age", "hba1c", "bmi"]
    site_dummies = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True)
    C_df = pd.concat([df[confounders], site_dummies], axis=1).astype(float)
    # Drop any rows with NaN/inf in confounders
    valid_mask = np.isfinite(C_df.values).all(axis=1)

    rows = []
    for ecol in ENTROPY_COLS:
        for outcome in OUTCOMES:
            mask = valid_mask & np.isfinite(df[ecol].values) & np.isfinite(df[outcome].values)
            if mask.sum() < 50:
                continue
            x = df.loc[mask, ecol].values.astype(float)
            y = df.loc[mask, outcome].values.astype(float)
            C = C_df.loc[mask].values
            # Use sklearn Ridge for residualization (numerically stable)
            lr = LinearRegression()
            lr.fit(C, x)
            rx = x - lr.predict(C)
            lr.fit(C, y)
            ry = y - lr.predict(C)
            r, p = stats.pearsonr(rx, ry)
            rows.append({
                "entropy_feature": ecol,
                "outcome": outcome,
                "partial_r": r,
                "p_value": p,
                "n": len(x),
            })

    result = pd.DataFrame(rows)
    _, fdr, _, _ = multipletests(result["p_value"], method="fdr_bh")
    result["fdr_p"] = fdr
    return result


def main():
    print("=" * 60)
    print("H-NEW05: Glucose Entropy → Clinical Burden Beyond HbA1c")
    print("=" * 60)

    df = load_data()
    print(f"N = {len(df)} participants with complete data")
    print(f"Study groups: {df['study_group'].value_counts().to_dict()}")
    print()

    # 1. Severity gradient
    print("--- Severity Gradient (Kruskal-Wallis + trend) ---")
    sg = severity_gradient(df)
    print(sg.to_string(index=False, float_format="%.4f"))
    sg.to_csv(result_path("h_new05_severity_gradient.csv"), index=False)
    print()

    # 2. Partial correlations
    print("--- Partial Correlations (adjusted for age, HbA1c, BMI, site) ---")
    pc = partial_correlation(df)
    print(pc.to_string(index=False, float_format="%.4f"))
    pc.to_csv(result_path("h_new05_partial_correlations.csv"), index=False)
    print()

    # 3. Incremental prediction
    print("--- Cross-Validated Incremental R² ---")
    ip = incremental_prediction(df)
    print(ip.to_string(index=False, float_format="%.4f"))
    ip.to_csv(result_path("h_new05_incremental_prediction.csv"), index=False)
    print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for outcome in OUTCOMES:
        base = ip.loc[(ip["outcome"] == outcome) & (ip["model"] == "base_only"), "r2_cv"].iloc[0]
        full = ip.loc[(ip["outcome"] == outcome) & (ip["model"] == "base+all_entropy"), "r2_cv"].iloc[0]
        delta = full - base
        print(f"{outcome}:")
        print(f"  Base (age+HbA1c+BMI+site) R²_cv = {base:.4f}")
        print(f"  + all entropy features    R²_cv = {full:.4f}")
        print(f"  Incremental R² = {delta:.4f} {'✓ > 0.03' if delta > 0.03 else '✗ < 0.03 threshold'}")
        # Best single scale
        best = ip.loc[(ip["outcome"] == outcome) & ip["model"].str.startswith("base+glucose"), "delta_r2"].max()
        best_name = ip.loc[(ip["outcome"] == outcome) & (ip["delta_r2"] == best) & ip["model"].str.startswith("base+glucose"), "model"].iloc[0] if best > 0 else "none"
        print(f"  Best single scale: {best_name} (ΔR² = {best:.4f})")
    print()


if __name__ == "__main__":
    main()
