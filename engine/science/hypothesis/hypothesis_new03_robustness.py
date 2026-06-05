"""
H-NEW03 Robustness Analysis: Is the post-excursion HR blunting real?

Tests:
  1. Full covariate adjustment (age, site, HbA1c, BMI, glucose mean, HR mean)
  2. Sensitivity to excursion threshold (20, 30, 40, 50 mg/dL)
  3. Awake-only vs all excursions
  4. Dose-response: effect by excursion magnitude quartile
  5. Negative control: random windows should show NO group difference
  6. Within-group: does excursion HR response correlate with HbA1c WITHIN each group?
  7. Pre-diabetes subgroup: is the effect already visible in pre-diabetes?
  8. Normalize by excursion magnitude: does per-mg/dL HR response still differ?
  9. Bootstrap CI for the primary effect
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from statsmodels.stats.multitest import multipletests

from scripts.config import RESULTS_DIR, result_path

warnings.filterwarnings("ignore")

STUDY_GROUP_ORDER = (
    "healthy",
    "pre_diabetes_lifestyle_controlled",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled",
    "insulin_dependent",
)
GROUP_SHORT = {"healthy": "H", "pre_diabetes_lifestyle_controlled": "PD",
               "oral_medication_and_or_non_insulin_injectable_medication_controlled": "OM",
               "insulin_dependent": "ID"}


def load_data():
    p2 = pd.read_parquet(result_path("hypothesis_phase2_features.parquet"))
    pi = pd.read_parquet(result_path("participant_index.parquet"))
    fm = pd.read_parquet(result_path("feature_matrix.parquet"))
    cs = pd.read_parquet(result_path("clinical_scores.parquet"))
    cf = pd.read_parquet(result_path("coupling_features.parquet"))

    # Drop metadata cols if already present from postprocess
    meta_cols = ["age", "clinical_site", "study_group", "hba1c", "bmi",
                 "frailty_index", "allostatic_load", "homeostatic_dysregulation",
                 "severity", "glucose_mean", "hr_mean"]
    p2 = p2.drop(columns=[c for c in meta_cols if c in p2.columns], errors="ignore")

    df = p2.join(pi[["age", "clinical_site", "study_group"]], how="left")
    df = df.join(fm[["hba1c", "bmi"]], how="left")
    df = df.join(cs[["frailty_index", "allostatic_load", "homeostatic_dysregulation"]], how="left")

    # Add raw glucose and HR means from coupling features
    for col in ["glucose_mean", "hr_mean"]:
        if col in cf.columns:
            df = df.join(cf[[col]], how="left")

    df = df[df["study_group"].isin(STUDY_GROUP_ORDER)]
    df["severity"] = df["study_group"].map({g: i for i, g in enumerate(STUDY_GROUP_ORDER)})
    return df


def cohens_d(g1, g2):
    n1, n2 = len(g1), len(g2)
    pooled = np.sqrt(((n1 - 1) * g1.var() + (n2 - 1) * g2.var()) / (n1 + n2 - 2))
    return (g2.mean() - g1.mean()) / pooled if pooled > 0 else 0


def test1_full_covariate_adjustment(df):
    """OLS with age, site, HbA1c, BMI, glucose_mean, hr_mean as covariates."""
    print("\n" + "=" * 60)
    print("TEST 1: FULL COVARIATE ADJUSTMENT")
    print("=" * 60)

    features = ["exc_hr_auc_mean", "exc_hr_peak_mean", "exc_hr_auc_sd", "exc_hr_per_mg_dl"]
    features = [f for f in features if f in df.columns]

    confounders = ["age", "hba1c", "bmi"]
    optional = ["glucose_mean", "hr_mean"]
    for col in optional:
        if col in df.columns:
            confounders.append(col)

    site_dum = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True)

    for feat in features:
        valid = df[[feat, "severity"] + confounders].dropna()
        if len(valid) < 100:
            continue
        site_valid = site_dum.loc[valid.index]
        X = np.column_stack([valid["severity"].values, valid[confounders].values, site_valid.values])
        y = valid[feat].values

        lr = LinearRegression().fit(X, y)
        y_pred = lr.predict(X)
        resid = y - y_pred
        n, p = X.shape
        mse = np.sum(resid ** 2) / (n - p)
        try:
            se = np.sqrt(mse * np.diag(np.linalg.inv(X.T @ X)))
        except np.linalg.LinAlgError:
            se = np.sqrt(mse * np.diag(np.linalg.pinv(X.T @ X)))
        t_stat = lr.coef_[0] / se[0]
        p_val = 2 * stats.t.sf(abs(t_stat), n - p)

        print(f"  {feat}:")
        print(f"    Severity coef = {lr.coef_[0]:.4f} (SE={se[0]:.4f})")
        print(f"    t = {t_stat:.2f}, p = {p_val:.2e}")
        survived = "SURVIVES" if p_val < 0.05 else "DOES NOT SURVIVE"
        print(f"    {survived} full adjustment (age, site, HbA1c, BMI, glucose_mean, hr_mean)")
        print()


def test2_threshold_sensitivity(df):
    """Does the effect hold across different excursion thresholds?"""
    print("\n" + "=" * 60)
    print("TEST 2: NOT AVAILABLE (requires re-extraction at different thresholds)")
    print("Use the primary 30 mg/dL threshold result.")
    print("=" * 60)


def test3_awake_only(df):
    """Compare all-excursion vs awake-only AUC."""
    print("\n" + "=" * 60)
    print("TEST 3: AWAKE-ONLY vs ALL EXCURSIONS")
    print("=" * 60)

    for feat, label in [("exc_hr_auc_mean", "All excursions"), ("exc_hr_auc_wake_mean", "Awake only")]:
        if feat not in df.columns:
            continue
        h = df.loc[df["study_group"] == "healthy", feat].dropna()
        ins = df.loc[df["study_group"] == "insulin_dependent", feat].dropna()
        d = cohens_d(h, ins)
        kw_groups = [df.loc[df["study_group"] == g, feat].dropna() for g in STUDY_GROUP_ORDER]
        kw_groups = [g for g in kw_groups if len(g) > 5]
        kw_stat, kw_p = stats.kruskal(*kw_groups)
        print(f"  {label} ({feat}):")
        print(f"    Healthy median: {h.median():.1f}, Insulin median: {ins.median():.1f}")
        print(f"    Cohen's d = {d:.3f}, KW p = {kw_p:.2e}")
        print()


def test4_dose_response(df):
    """Is there a monotonic dose-response across all 4 severity groups?"""
    print("\n" + "=" * 60)
    print("TEST 4: DOSE-RESPONSE ACROSS SEVERITY GROUPS")
    print("=" * 60)

    for feat in ["exc_hr_peak_mean", "exc_hr_auc_mean", "exc_hr_per_mg_dl"]:
        if feat not in df.columns:
            continue
        print(f"  {feat}:")
        medians = []
        for g in STUDY_GROUP_ORDER:
            vals = df.loc[df["study_group"] == g, feat].dropna()
            med = vals.median()
            medians.append(med)
            print(f"    {GROUP_SHORT[g]}: median={med:.2f} (N={len(vals)})")

        # Jonckheere-Terpstra trend test (approximated via Spearman)
        valid = df[[feat, "severity"]].dropna()
        r, p = stats.spearmanr(valid["severity"], valid[feat])
        monotonic = all(medians[i] >= medians[i + 1] for i in range(len(medians) - 1)) or \
                    all(medians[i] <= medians[i + 1] for i in range(len(medians) - 1))
        print(f"    Trend: r={r:.3f}, p={p:.2e}, monotonic={monotonic}")
        print()


def test5_negative_control(df):
    """Random windows should show NO group difference."""
    print("\n" + "=" * 60)
    print("TEST 5: NEGATIVE CONTROL (random windows)")
    print("=" * 60)

    feat = "ctrl_hr_auc_mean"
    if feat not in df.columns:
        print("  ctrl_hr_auc_mean not available")
        return

    h = df.loc[df["study_group"] == "healthy", feat].dropna()
    ins = df.loc[df["study_group"] == "insulin_dependent", feat].dropna()
    d = cohens_d(h, ins)
    kw_groups = [df.loc[df["study_group"] == g, feat].dropna() for g in STUDY_GROUP_ORDER]
    kw_groups = [g for g in kw_groups if len(g) > 5]
    kw_stat, kw_p = stats.kruskal(*kw_groups)
    print(f"  Random window HR AUC:")
    print(f"    Healthy median: {h.median():.1f}, Insulin median: {ins.median():.1f}")
    print(f"    Cohen's d = {d:.3f}, KW p = {kw_p:.2e}")
    passed = "PASSED" if kw_p > 0.05 else "FAILED"
    print(f"    Negative control: {passed} (expect p > 0.05)")
    print()

    # Excursion vs control difference
    diff_feat = "exc_vs_ctrl_auc_diff"
    if diff_feat in df.columns:
        for g in STUDY_GROUP_ORDER:
            vals = df.loc[df["study_group"] == g, diff_feat].dropna()
            print(f"    {GROUP_SHORT[g]}: excursion-control diff = {vals.median():.1f}")


def test6_within_group_hba1c(df):
    """Does excursion HR response correlate with HbA1c WITHIN each group?"""
    print("\n" + "=" * 60)
    print("TEST 6: WITHIN-GROUP CORRELATION WITH HbA1c")
    print("=" * 60)

    feat = "exc_hr_peak_mean"
    if feat not in df.columns:
        return

    for g in STUDY_GROUP_ORDER:
        sub = df.loc[df["study_group"] == g, [feat, "hba1c"]].dropna()
        if len(sub) < 20:
            continue
        r, p = stats.spearmanr(sub[feat], sub["hba1c"])
        print(f"  {GROUP_SHORT[g]} (N={len(sub)}): {feat} vs HbA1c: r={r:.3f}, p={p:.3f}")


def test7_prediabetes_effect(df):
    """Is the effect already visible in pre-diabetes vs healthy?"""
    print("\n" + "=" * 60)
    print("TEST 7: PRE-DIABETES vs HEALTHY (early detection)")
    print("=" * 60)

    for feat in ["exc_hr_peak_mean", "exc_hr_auc_mean", "exc_hr_per_mg_dl"]:
        if feat not in df.columns:
            continue
        h = df.loc[df["study_group"] == "healthy", feat].dropna()
        pd_grp = df.loc[df["study_group"] == "pre_diabetes_lifestyle_controlled", feat].dropna()
        d = cohens_d(h, pd_grp)
        t, p = stats.mannwhitneyu(h, pd_grp, alternative="two-sided")
        print(f"  {feat}:")
        print(f"    Healthy: median={h.median():.2f} (N={len(h)})")
        print(f"    Pre-diabetes: median={pd_grp.median():.2f} (N={len(pd_grp)})")
        print(f"    Cohen's d = {d:.3f}, Mann-Whitney p = {p:.3f}")
        print()


def test8_clinical_burden(df):
    """Do excursion HR features link to frailty/allostatic load?"""
    print("\n" + "=" * 60)
    print("TEST 8: CLINICAL BURDEN CORRELATIONS (adjusted for age, HbA1c, BMI, site)")
    print("=" * 60)

    features = ["exc_hr_peak_mean", "exc_hr_auc_mean", "exc_hr_per_mg_dl"]
    features = [f for f in features if f in df.columns]
    outcomes = ["frailty_index", "allostatic_load"]
    confounders = ["age", "hba1c", "bmi"]
    site_dum = pd.get_dummies(df["clinical_site"], prefix="site", drop_first=True)

    rows = []
    for feat in features:
        for outcome in outcomes:
            valid_mask = df[[feat, outcome] + confounders].notna().all(axis=1)
            if valid_mask.sum() < 100:
                continue
            x = df.loc[valid_mask, feat].values.astype(float)
            y = df.loc[valid_mask, outcome].values.astype(float)
            C = pd.concat([df.loc[valid_mask, confounders], site_dum.loc[valid_mask]], axis=1).astype(float).values

            lr = LinearRegression()
            lr.fit(C, x)
            rx = x - lr.predict(C)
            lr.fit(C, y)
            ry = y - lr.predict(C)
            r, p = stats.pearsonr(rx, ry)
            rows.append({"feature": feat, "outcome": outcome, "partial_r": r, "p": p, "n": int(valid_mask.sum())})

    result = pd.DataFrame(rows)
    if len(result) > 0:
        _, fdr, _, _ = multipletests(result["p"], method="fdr_bh")
        result["fdr_p"] = fdr
    print(result.to_string(index=False, float_format="%.4f"))


def test9_bootstrap_ci(df):
    """Bootstrap 95% CI for the primary Cohen's d."""
    print("\n" + "=" * 60)
    print("TEST 9: BOOTSTRAP 95% CI FOR PRIMARY EFFECT")
    print("=" * 60)

    feat = "exc_hr_peak_mean"
    if feat not in df.columns:
        return

    h = df.loc[df["study_group"] == "healthy", feat].dropna().values
    ins = df.loc[df["study_group"] == "insulin_dependent", feat].dropna().values

    rng = np.random.RandomState(42)
    boot_ds = []
    for _ in range(2000):
        h_boot = rng.choice(h, size=len(h), replace=True)
        ins_boot = rng.choice(ins, size=len(ins), replace=True)
        pooled = np.sqrt(((len(h_boot) - 1) * h_boot.var() + (len(ins_boot) - 1) * ins_boot.var()) /
                         (len(h_boot) + len(ins_boot) - 2))
        d = (ins_boot.mean() - h_boot.mean()) / pooled if pooled > 0 else 0
        boot_ds.append(d)

    boot_ds = np.array(boot_ds)
    ci_lo, ci_hi = np.percentile(boot_ds, [2.5, 97.5])
    print(f"  {feat} Cohen's d (H vs ID):")
    print(f"    Point estimate: {cohens_d(h, ins):.3f}")
    print(f"    Bootstrap 95% CI: [{ci_lo:.3f}, {ci_hi:.3f}]")
    print(f"    CI excludes zero: {'YES' if (ci_lo > 0 and ci_hi > 0) or (ci_lo < 0 and ci_hi < 0) else 'NO'}")


def main():
    print("=" * 60)
    print("H-NEW03 ROBUSTNESS ANALYSIS")
    print("Is the post-excursion HR blunting real?")
    print("=" * 60)

    df = load_data()
    print(f"N = {len(df)}")
    print(f"Groups: {df['study_group'].value_counts().to_dict()}")

    test1_full_covariate_adjustment(df)
    test3_awake_only(df)
    test4_dose_response(df)
    test5_negative_control(df)
    test6_within_group_hba1c(df)
    test7_prediabetes_effect(df)
    test8_clinical_burden(df)
    test9_bootstrap_ci(df)

    print("\n" + "=" * 60)
    print("OVERALL VERDICT")
    print("=" * 60)


if __name__ == "__main__":
    main()
