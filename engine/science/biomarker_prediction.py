"""Phase 6 — Digital biomarker prediction from wearable/CGM to clinical outcomes.

Analyses
--------
6a  Wearable features --> HbA1c  (ElasticNet regression + binary AUC)
6b  Circadian disruption --> insulin resistance  (partial correlations)
6c  CGM variability --> visual acuity  (Spearman / partial correlations)
6d  Comprehensive panel: all multimodal --> each clinical target

Usage
-----
    python -m scripts.biomarker_prediction
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from sklearn.linear_model import ElasticNetCV
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
    roc_auc_score,
    root_mean_squared_error,
)
from sklearn.preprocessing import StandardScaler
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.multitest import multipletests
import statsmodels.api as sm

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "/oak/stanford/scg/lab_twc/mazijian/aireadi")
from scripts.config import RESULTS_DIR, result_path  # noqa: E402
from scripts.features import load_feature_matrix  # noqa: E402

# ── Constants ─────────────────────────────────────────────────────────────────

FIGURES_DIR = RESULTS_DIR / "figures"

# Multimodal feature groups (matching multimodal_features.parquet column names)
WEARABLE_CIRC = [
    "wear_is", "wear_iv", "wear_m10", "wear_l5", "wear_ra",
    "wear_cosinor_amplitude", "wear_cosinor_acrophase", "wear_cosinor_mesor",
]
WEARABLE_SLEEP = [
    "wear_mean_tst", "wear_mean_se", "wear_mean_waso",
    "wear_mean_rem_pct", "wear_mean_deep_pct", "wear_sleep_regularity",
]
WEARABLE_HR = ["wear_resting_hr", "wear_nocturnal_hr", "wear_diurnal_hr",
               "wear_nocturnal_dip_pct"]
WEARABLE_ACTIVITY = ["wear_mean_daily_steps", "wear_mean_active_calories"]
ALL_WEARABLE = WEARABLE_CIRC + WEARABLE_SLEEP + WEARABLE_HR + WEARABLE_ACTIVITY

CGM_FEATURES = [
    "cgm_mean_glucose", "cgm_cv_glucose", "cgm_tir", "cgm_mage", "cgm_gri",
    "cgm_dawn_phenomenon", "cgm_nocturnal_mean", "cgm_nocturnal_cv",
    "cgm_lbgi", "cgm_hbgi", "cgm_gmi",
]
ENV_FEATURES = [
    "env_mean_pm25", "env_bright_light_hours", "env_evening_light_exposure",
    "env_mean_temp", "env_temp_range",
]
ALL_MULTIMODAL = ALL_WEARABLE + CGM_FEATURES + ENV_FEATURES

INSULIN_NG_TO_UU = 1.0 / 0.04034  # multiply ng/L by this to get µU/mL

STUDY_GROUP_SHORT = {
    "healthy": "Healthy",
    "pre_diabetes_lifestyle_controlled": "PreDM",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": "T2DM-oral",
    "insulin_dependent": "T2DM-insulin",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Helper utilities
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def _available_cols(df: pd.DataFrame, wanted: list[str]) -> list[str]:
    """Return the subset of *wanted* columns that actually exist in *df*."""
    return [c for c in wanted if c in df.columns]


def _split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split a dataframe by recommended_split column."""
    train = df[df["recommended_split"] == "train"]
    val = df[df["recommended_split"] == "val"]
    test = df[df["recommended_split"] == "test"]
    return train, val, test


def _compute_homa_ir(df: pd.DataFrame) -> pd.Series:
    """Compute HOMA-IR from insulin (ng/L) and glucose (mg/dL) columns."""
    insulin_uu = df["insulin"] * INSULIN_NG_TO_UU
    homa_ir = (insulin_uu * df["glucose"]) / 405.0
    return homa_ir


def _partial_corr(
    df: pd.DataFrame, x: str, y: str, covars: list[str], method: str = "pearson",
) -> dict:
    """Partial correlation between x and y controlling for covars.

    Uses OLS residualization:  regress x ~ covars, regress y ~ covars,
    then correlate the residuals.
    """
    cols = [x, y] + covars
    sub = df[cols].dropna()
    if len(sub) < len(cols) + 5:
        return {"r": np.nan, "p": np.nan, "n": len(sub)}

    C = sm.add_constant(sub[covars])
    resid_x = OLS(sub[x].values, C).fit().resid
    resid_y = OLS(sub[y].values, C).fit().resid

    if method == "spearman":
        r, p = sp_stats.spearmanr(resid_x, resid_y)
    else:
        r, p = sp_stats.pearsonr(resid_x, resid_y)
    return {"r": r, "p": p, "n": len(sub)}


def _fit_elasticnet(
    X_train: np.ndarray,
    y_train: np.ndarray,
    l1_ratios: list[float] | None = None,
    cv: int = 5,
) -> ElasticNetCV:
    """Fit an ElasticNetCV model with StandardScaler-like preprocessing already applied."""
    if l1_ratios is None:
        l1_ratios = [0.1, 0.5, 0.7, 0.9, 0.95, 0.99]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = ElasticNetCV(
            l1_ratio=l1_ratios, cv=cv, max_iter=20_000, random_state=42,
        )
        model.fit(X_train, y_train)
    return model


def _regression_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    label: str,
) -> dict:
    """Compute regression metrics and print a summary line."""
    r2 = r2_score(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = root_mean_squared_error(y_true, y_pred)
    print(f"  {label:30s}  R²={r2:+.4f}  MAE={mae:.4f}  RMSE={rmse:.4f}  n={len(y_true)}")
    return {"label": label, "r2": r2, "mae": mae, "rmse": rmse, "n": len(y_true)}


# ═══════════════════════════════════════════════════════════════════════════════
# 6a  Wearable --> HbA1c
# ═══════════════════════════════════════════════════════════════════════════════

def wearable_hba1c_prediction(
    features_df: pd.DataFrame,
    multimodal_df: pd.DataFrame | None,
) -> dict | None:
    """Predict HbA1c from wearable features alone."""
    if multimodal_df is None:
        print("\n[6a] SKIP — multimodal_features.parquet not available.")
        return None

    wearable_cols = _available_cols(multimodal_df, ALL_WEARABLE)
    if len(wearable_cols) < 2:
        print(f"\n[6a] SKIP — only {len(wearable_cols)} wearable columns found.")
        return None

    # Merge wearable features with HbA1c + split info
    merged = features_df[["hba1c", "recommended_split"]].join(
        multimodal_df[wearable_cols], how="inner",
    )
    merged = merged.dropna(subset=["hba1c"] + wearable_cols)
    train, _val, test = _split(merged)

    if len(train) < 30 or len(test) < 10:
        print(f"\n[6a] SKIP — insufficient data (train={len(train)}, test={len(test)}).")
        return None

    print(f"\n{'='*72}")
    print("[6a] Wearable --> HbA1c Prediction")
    print(f"{'='*72}")
    print(f"  Features: {len(wearable_cols)} wearable columns")
    print(f"  Train n={len(train)}, Test n={len(test)}")

    # Scale
    scaler = StandardScaler()
    X_train = scaler.fit_transform(train[wearable_cols])
    X_test = scaler.transform(test[wearable_cols])
    y_train = train["hba1c"].values
    y_test = test["hba1c"].values

    # Fit
    model = _fit_elasticnet(X_train, y_train)
    y_pred = model.predict(X_test)
    metrics = _regression_report(y_test, y_pred, "Wearable -> HbA1c (test)")
    print(f"  Best l1_ratio={model.l1_ratio_:.2f}, alpha={model.alpha_:.6f}")

    # Binary AUC: HbA1c >= 6.5
    y_binary = (y_test >= 6.5).astype(int)
    if y_binary.sum() > 0 and y_binary.sum() < len(y_binary):
        auc = roc_auc_score(y_binary, y_pred)
        print(f"  Binary AUROC (HbA1c>=6.5): {auc:.4f}")
        metrics["auroc_6.5"] = auc
    else:
        print("  Binary AUROC: cannot compute (single class in test set)")
        metrics["auroc_6.5"] = np.nan

    # Feature importance
    coefs = pd.Series(model.coef_, index=wearable_cols)
    top = coefs.abs().sort_values(ascending=False).head(10)
    print("\n  Top features by |coefficient|:")
    for feat in top.index:
        print(f"    {feat:35s}  coef={coefs[feat]:+.5f}")

    # Save predictions
    pred_df = pd.DataFrame({
        "person_id": test.index,
        "hba1c_true": y_test,
        "hba1c_pred": y_pred,
    })
    pred_df.to_csv(result_path("biomarker_wearable_hba1c.csv"), index=False)

    # Scatter plot
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(y_test, y_pred, alpha=0.4, s=20, edgecolors="none")
    lo, hi = min(y_test.min(), y_pred.min()) - 0.2, max(y_test.max(), y_pred.max()) + 0.2
    ax.plot([lo, hi], [lo, hi], "k--", linewidth=0.8)
    ax.set_xlabel("Observed HbA1c (%)")
    ax.set_ylabel("Predicted HbA1c (%)")
    ax.set_title(f"Wearable -> HbA1c  (R$^2$={metrics['r2']:.3f}, MAE={metrics['mae']:.3f})")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "wearable_hba1c_scatter.png", dpi=150)
    plt.close(fig)
    print(f"  Saved: {RESULTS_DIR / 'biomarker_wearable_hba1c.csv'}")
    print(f"  Saved: {FIGURES_DIR / 'wearable_hba1c_scatter.png'}")

    return metrics


# ═══════════════════════════════════════════════════════════════════════════════
# 6b  Circadian disruption --> Insulin resistance
# ═══════════════════════════════════════════════════════════════════════════════

def circadian_insulin_resistance(
    features_df: pd.DataFrame,
    multimodal_df: pd.DataFrame | None,
    scores_df: pd.DataFrame | None = None,
) -> dict:
    """Association between circadian disruption and insulin resistance.

    Works in two modes:
    - Full: uses multimodal wearable circadian features (IS/IV/M10/L5/RA/cosinor)
    - Fallback: uses only feature_matrix (computes HOMA-IR, uses heart_rate as
      the sole circadian-adjacent proxy) to demonstrate the pipeline.
    """
    print(f"\n{'='*72}")
    print("[6b] Circadian Disruption --> Insulin Resistance")
    print(f"{'='*72}")

    # ── Compute HOMA-IR ──────────────────────────────────────────────────────
    df = features_df.copy()
    if scores_df is not None and "homa_ir" in scores_df.columns:
        df = df.join(scores_df[["homa_ir"]], how="left")
        print("  HOMA-IR source: clinical_scores.parquet")
    else:
        df["homa_ir"] = _compute_homa_ir(df)
        print("  HOMA-IR source: computed from insulin (ng/L) and glucose (mg/dL)")

    n_valid = df["homa_ir"].notna().sum()
    print(f"  HOMA-IR available: n={n_valid}")
    print(f"  HOMA-IR median={df['homa_ir'].median():.2f}, "
          f"IQR=[{df['homa_ir'].quantile(0.25):.2f}, {df['homa_ir'].quantile(0.75):.2f}]")

    # Log-transform HOMA-IR for better normality
    df["log_homa_ir"] = np.log1p(df["homa_ir"].clip(lower=0))

    # ── Determine circadian features available ───────────────────────────────
    circ_targets = WEARABLE_CIRC
    use_full = False
    if multimodal_df is not None:
        available_circ = _available_cols(multimodal_df, circ_targets)
        if len(available_circ) >= 2:
            df = df.join(multimodal_df[available_circ], how="left")
            use_full = True
            print(f"  Circadian features: {available_circ} (from multimodal)")
        else:
            print(f"  Only {len(available_circ)} circadian cols in multimodal; using fallback.")

    if not use_full:
        # Fallback: use heart_rate and resting HR-related proxies from feature_matrix
        available_circ = _available_cols(df, ["heart_rate"])
        print("  Circadian features: fallback to heart_rate (proxy) from feature_matrix")

    # ── 1-3. Partial correlations: each circadian feature vs HOMA-IR ─────────
    covars = ["age", "bmi"]
    results_rows = []

    print(f"\n  Partial correlations (adjusting for {covars}):")
    print(f"  {'Feature':30s} {'r':>8s} {'p':>10s} {'n':>6s}")
    print(f"  {'-'*56}")

    for feat in available_circ:
        res = _partial_corr(df, feat, "log_homa_ir", covars)
        results_rows.append({"feature": feat, "target": "log_homa_ir", **res, "covars": "+".join(covars)})
        print(f"  {feat:30s} {res['r']:+8.4f} {res['p']:10.2e} {res['n']:6d}")

    # FDR correction
    if len(results_rows) > 1:
        pvals = [r["p"] for r in results_rows if not np.isnan(r["p"])]
        if pvals:
            _reject, pvals_fdr, _a, _b = multipletests(pvals, method="fdr_bh")
            idx = 0
            for r in results_rows:
                if not np.isnan(r["p"]):
                    r["p_fdr"] = pvals_fdr[idx]
                    idx += 1
                else:
                    r["p_fdr"] = np.nan
            print(f"\n  FDR-corrected p-values:")
            for r in results_rows:
                print(f"    {r['feature']:30s} p_fdr={r['p_fdr']:.2e}")

    # ── 4. Stratify by study_group ───────────────────────────────────────────
    print(f"\n  Stratified partial correlations by study_group:")
    strat_rows = []
    for grp, grp_label in STUDY_GROUP_SHORT.items():
        mask = df["study_group"] == grp
        sub = df[mask]
        for feat in available_circ:
            res = _partial_corr(sub, feat, "log_homa_ir", covars)
            strat_rows.append({
                "study_group": grp_label, "feature": feat,
                "target": "log_homa_ir", **res,
            })
            print(f"    {grp_label:15s} {feat:25s} r={res['r']:+.4f}  p={res['p']:.2e}  n={res['n']}")

    # ── 5. Multiple regression ───────────────────────────────────────────────
    reg_features = available_circ + ["age", "bmi"]
    reg_df = df[reg_features + ["log_homa_ir"]].dropna()

    if len(reg_df) >= len(reg_features) + 10:
        print(f"\n  Multiple regression: log(HOMA-IR) ~ {' + '.join(available_circ)} + age + BMI")
        X = sm.add_constant(reg_df[reg_features])
        model = OLS(reg_df["log_homa_ir"], X).fit()
        print(f"  R² = {model.rsquared:.4f}, Adj-R² = {model.rsquared_adj:.4f}, n = {len(reg_df)}")
        print(f"  {'Variable':30s} {'coef':>10s} {'SE':>10s} {'t':>8s} {'p':>10s}")
        print(f"  {'-'*70}")
        for var in reg_features:
            coef = model.params[var]
            se = model.bse[var]
            t = model.tvalues[var]
            p = model.pvalues[var]
            sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))
            print(f"  {var:30s} {coef:+10.5f} {se:10.5f} {t:+8.3f} {p:10.2e} {sig}")
        reg_summary = {
            "r2": model.rsquared, "adj_r2": model.rsquared_adj,
            "n": len(reg_df), "f_pvalue": model.f_pvalue,
        }
    else:
        print(f"\n  Multiple regression: SKIP (n={len(reg_df)} too small)")
        reg_summary = {}

    # ── Save results ─────────────────────────────────────────────────────────
    all_rows = results_rows + strat_rows
    out_df = pd.DataFrame(all_rows)
    out_df.to_csv(result_path("biomarker_circadian_ir.csv"), index=False)
    print(f"\n  Saved: {RESULTS_DIR / 'biomarker_circadian_ir.csv'}")

    # ── Scatter plot: best circadian feature vs log(HOMA-IR) ─────────────────
    best_feat = available_circ[0]  # first available
    plot_df = df[[best_feat, "log_homa_ir", "study_group"]].dropna()
    if len(plot_df) > 10:
        fig, ax = plt.subplots(figsize=(7, 5))
        for grp, label in STUDY_GROUP_SHORT.items():
            mask = plot_df["study_group"] == grp
            ax.scatter(
                plot_df.loc[mask, best_feat],
                plot_df.loc[mask, "log_homa_ir"],
                alpha=0.35, s=18, label=label, edgecolors="none",
            )
        ax.set_xlabel(best_feat)
        ax.set_ylabel("log(1 + HOMA-IR)")
        ax.set_title(f"{best_feat} vs Insulin Resistance (n={len(plot_df)})")
        ax.legend(fontsize=8, frameon=False)
        fig.tight_layout()
        fig.savefig(FIGURES_DIR / "circadian_ir_scatter.png", dpi=150)
        plt.close(fig)
        print(f"  Saved: {FIGURES_DIR / 'circadian_ir_scatter.png'}")

    return {"partial_corr": results_rows, "stratified": strat_rows, "regression": reg_summary}


# ═══════════════════════════════════════════════════════════════════════════════
# 6c  CGM variability --> Visual acuity
# ═══════════════════════════════════════════════════════════════════════════════

def cgm_visual_acuity(
    features_df: pd.DataFrame,
    multimodal_df: pd.DataFrame | None,
) -> dict | None:
    """Association between glucose variability and visual function."""
    if multimodal_df is None:
        print("\n[6c] SKIP — multimodal_features.parquet not available.")
        return None

    cgm_cols = _available_cols(multimodal_df, ["cgm_cv_glucose", "cgm_mage", "cgm_gri", "cgm_hbgi"])
    if not cgm_cols:
        print("\n[6c] SKIP — no CGM variability columns found.")
        return None

    print(f"\n{'='*72}")
    print("[6c] CGM Variability --> Visual Acuity")
    print(f"{'='*72}")

    # Average logMAR across both eyes (or use OD if OS missing)
    df = features_df[["logmar_photopic_od", "logmar_photopic_os",
                       "hba1c", "age", "study_group", "recommended_split"]].copy()
    df["logmar_avg"] = df[["logmar_photopic_od", "logmar_photopic_os"]].mean(axis=1)
    df = df.join(multimodal_df[cgm_cols], how="inner")
    print(f"  CGM features: {cgm_cols}")
    print(f"  Visual acuity: logMAR average of OD+OS (higher = worse)")
    print(f"  Merged n={len(df)}, with complete logMAR: {df['logmar_avg'].notna().sum()}")

    results_rows = []

    # ── 1-2. Spearman correlations adjusting for age ─────────────────────────
    print(f"\n  Spearman partial correlations (adjusting for age):")
    print(f"  {'CGM feature':25s} {'rho':>8s} {'p':>10s} {'n':>6s}")
    print(f"  {'-'*52}")

    for feat in cgm_cols:
        res = _partial_corr(df, feat, "logmar_avg", ["age"], method="spearman")
        results_rows.append({"cgm_feature": feat, "target": "logmar_avg",
                             "covars": "age", **res})
        print(f"  {feat:25s} {res['r']:+8.4f} {res['p']:10.2e} {res['n']:6d}")

    # ── 3. Partial correlation adjusting for age + HbA1c ─────────────────────
    print(f"\n  Adjusting for age + HbA1c (independence from mean glycemia):")
    print(f"  {'CGM feature':25s} {'rho':>8s} {'p':>10s} {'n':>6s}")
    print(f"  {'-'*52}")

    for feat in cgm_cols:
        res = _partial_corr(df, feat, "logmar_avg", ["age", "hba1c"], method="spearman")
        results_rows.append({"cgm_feature": feat, "target": "logmar_avg",
                             "covars": "age+hba1c", **res})
        print(f"  {feat:25s} {res['r']:+8.4f} {res['p']:10.2e} {res['n']:6d}")

    # FDR across all tests
    pvals = [r["p"] for r in results_rows if not np.isnan(r["p"])]
    if len(pvals) > 1:
        _reject, pvals_fdr, _a, _b = multipletests(pvals, method="fdr_bh")
        idx = 0
        for r in results_rows:
            if not np.isnan(r["p"]):
                r["p_fdr"] = pvals_fdr[idx]
                idx += 1
            else:
                r["p_fdr"] = np.nan

    # ── 4. Stratify by study_group ───────────────────────────────────────────
    strat_rows = []
    print(f"\n  Stratified by study_group (adjusting for age):")
    for grp, label in STUDY_GROUP_SHORT.items():
        mask = df["study_group"] == grp
        sub = df[mask]
        for feat in cgm_cols:
            res = _partial_corr(sub, feat, "logmar_avg", ["age"], method="spearman")
            strat_rows.append({"study_group": label, "cgm_feature": feat, **res})
            print(f"    {label:15s} {feat:20s} rho={res['r']:+.4f}  p={res['p']:.2e}  n={res['n']}")

    # ── Save ─────────────────────────────────────────────────────────────────
    out_df = pd.DataFrame(results_rows + strat_rows)
    out_df.to_csv(result_path("biomarker_cgm_vision.csv"), index=False)
    print(f"\n  Saved: {RESULTS_DIR / 'biomarker_cgm_vision.csv'}")

    return {"correlations": results_rows, "stratified": strat_rows}


# ═══════════════════════════════════════════════════════════════════════════════
# 6d  Comprehensive digital biomarker panel
# ═══════════════════════════════════════════════════════════════════════════════

def comprehensive_panel(
    features_df: pd.DataFrame,
    multimodal_df: pd.DataFrame | None,
) -> dict | None:
    """Which wearable/CGM features predict which clinical outcomes?"""
    if multimodal_df is None:
        print("\n[6d] SKIP — multimodal_features.parquet not available.")
        return None

    mm_cols = _available_cols(multimodal_df, ALL_MULTIMODAL)
    if len(mm_cols) < 3:
        print(f"\n[6d] SKIP — only {len(mm_cols)} multimodal features found.")
        return None

    targets = ["hba1c", "sbp", "dbp", "bmi", "total_cholesterol", "hdl", "triglycerides"]
    targets = [t for t in targets if t in features_df.columns]

    print(f"\n{'='*72}")
    print("[6d] Comprehensive Digital Biomarker Panel")
    print(f"{'='*72}")
    print(f"  Multimodal features: {len(mm_cols)}")
    print(f"  Targets: {targets}")

    panel_rows = []

    for target in targets:
        merged = features_df[[target, "recommended_split"]].join(
            multimodal_df[mm_cols], how="inner",
        )
        merged = merged.dropna(subset=[target] + mm_cols)
        train, _val, test = _split(merged)

        if len(train) < 30 or len(test) < 10:
            print(f"\n  {target}: SKIP (train={len(train)}, test={len(test)})")
            continue

        # Clean inf/extreme outliers before scaling
        for col in mm_cols:
            for df in [train, test]:
                s = df[col]
                s = s.replace([np.inf, -np.inf], np.nan)
                valid = s.dropna()
                if len(valid) > 10:
                    q1, q3 = valid.quantile([0.25, 0.75])
                    iqr = q3 - q1
                    lo, hi = q1 - 5 * iqr, q3 + 5 * iqr
                    s = s.clip(lo, hi)
                df[col] = s
        train = train.dropna(subset=mm_cols)
        test = test.dropna(subset=mm_cols)
        if len(train) < 30 or len(test) < 10:
            print(f"\n  {target}: SKIP after cleaning (train={len(train)}, test={len(test)})")
            continue

        scaler = StandardScaler()
        X_train = scaler.fit_transform(train[mm_cols])
        X_test = scaler.transform(test[mm_cols])
        y_train = train[target].values
        y_test = test[target].values

        model = _fit_elasticnet(X_train, y_train)
        y_pred = model.predict(X_test)
        metrics = _regression_report(y_test, y_pred, f"Multimodal -> {target}")

        # Top 5 features
        coefs = pd.Series(model.coef_, index=mm_cols)
        top5 = coefs.abs().sort_values(ascending=False).head(5)
        top_feats = "; ".join(
            f"{f}({coefs[f]:+.4f})" for f in top5.index
        )
        metrics["target"] = target
        metrics["top5_features"] = top_feats
        metrics["l1_ratio"] = model.l1_ratio_
        metrics["alpha"] = model.alpha_
        panel_rows.append(metrics)
        print(f"    Top 5: {top_feats}")

    if panel_rows:
        panel_df = pd.DataFrame(panel_rows)
        panel_df.to_csv(result_path("biomarker_panel.csv"), index=False)
        print(f"\n  Saved: {RESULTS_DIR / 'biomarker_panel.csv'}")

    return {"panel": panel_rows}


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    _ensure_dirs()

    print("Loading feature matrix...")
    fm = load_feature_matrix()
    print(f"  Shape: {fm.shape}")

    # Try to load multimodal features
    mf_path = result_path("multimodal_features.parquet")
    if mf_path.exists():
        mf = pd.read_parquet(mf_path)
        print(f"  Multimodal features loaded: {mf.shape}")
    else:
        mf = None
        print("  WARNING: multimodal_features.parquet not found.")
        print("  Analyses 6a, 6c, 6d require it — run Phase 1b first.")
        print("  Analysis 6b will proceed with feature_matrix fallback.\n")

    # Try to load clinical scores
    cs_path = result_path("clinical_scores.parquet")
    cs = pd.read_parquet(cs_path) if cs_path.exists() else None

    # ── Run analyses ─────────────────────────────────────────────────────────
    results = {}

    results["6a"] = wearable_hba1c_prediction(fm, mf)
    results["6b"] = circadian_insulin_resistance(fm, mf, cs)
    results["6c"] = cgm_visual_acuity(fm, mf)
    results["6d"] = comprehensive_panel(fm, mf)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print("Phase 6 — Digital Biomarker Prediction: COMPLETE")
    print(f"{'='*72}")
    completed = [k for k, v in results.items() if v is not None]
    skipped = [k for k, v in results.items() if v is None]
    print(f"  Completed: {', '.join(completed) if completed else 'none'}")
    if skipped:
        print(f"  Skipped (need multimodal_features): {', '.join(skipped)}")


if __name__ == "__main__":
    main()
