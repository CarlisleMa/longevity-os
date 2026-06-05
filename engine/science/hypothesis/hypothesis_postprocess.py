"""
Postprocess hypothesis time-series features and run statistical tests.

Combines shards from hypothesis_timeseries.py and tests:
  H-NEW01: Frequency-band coupling vs diabetes severity
  H-NEW06: Nocturnal coupling → next-day glucose (population-level)
  H-NEW13: Sleep-wake reorganization speed vs diabetes severity
  H-NEW17: Diurnal coupling amplitude vs diabetes severity

Usage:
    python -m scripts.hypothesis.hypothesis_postprocess
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
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


def load_combined() -> pd.DataFrame:
    """Load and combine shards, merge with participant metadata."""
    shard_dir = RESULTS_DIR / "shards" / "hypothesis_timeseries"
    shards = sorted(shard_dir.glob("shard_*.parquet"))
    if not shards:
        raise FileNotFoundError(f"No shards in {shard_dir}")
    df = pd.concat([pd.read_parquet(s) for s in shards])
    df = df[~df.index.duplicated(keep="first")]

    pi = pd.read_parquet(result_path("participant_index.parquet"))
    fm = pd.read_parquet(result_path("feature_matrix.parquet"))
    cs = pd.read_parquet(result_path("clinical_scores.parquet"))

    df = df.join(pi[["age", "clinical_site", "study_group"]], how="left")
    df = df.join(fm[["hba1c", "bmi"]], how="left")
    df = df.join(cs[["frailty_index", "allostatic_load", "homeostatic_dysregulation"]], how="left")

    df = df[df["study_group"].isin(STUDY_GROUP_ORDER)]
    df["severity"] = df["study_group"].map({g: i for i, g in enumerate(STUDY_GROUP_ORDER)})

    print(f"Combined: {len(df)} participants")
    print(f"Groups: {df['study_group'].value_counts().to_dict()}")
    return df


def severity_test(df: pd.DataFrame, feature: str, label: str = "") -> dict:
    """Kruskal-Wallis + trend test + Cohen's d (healthy vs insulin)."""
    groups = [df.loc[df["study_group"] == g, feature].dropna() for g in STUDY_GROUP_ORDER]
    groups = [g for g in groups if len(g) > 5]
    if len(groups) < 3:
        return {"feature": label or feature, "n": 0}

    kw_stat, kw_p = stats.kruskal(*groups)
    valid = df[[feature, "severity"]].dropna()
    r, p_trend = stats.spearmanr(valid["severity"], valid[feature])

    # Cohen's d: healthy vs insulin
    h = df.loc[df["study_group"] == "healthy", feature].dropna()
    ins = df.loc[df["study_group"] == "insulin_dependent", feature].dropna()
    pooled_sd = np.sqrt((h.var() * (len(h) - 1) + ins.var() * (len(ins) - 1)) / (len(h) + len(ins) - 2))
    d = (ins.mean() - h.mean()) / pooled_sd if pooled_sd > 0 else 0

    medians = {GROUP_SHORT.get(g, g): df.loc[df["study_group"] == g, feature].median() for g in STUDY_GROUP_ORDER}

    return {
        "feature": label or feature,
        "n": int(valid[feature].notna().sum()),
        "kw_stat": kw_stat,
        "kw_p": kw_p,
        "trend_r": r,
        "trend_p": p_trend,
        "d_h_vs_id": d,
        **{f"med_{k}": v for k, v in medians.items()},
    }


def age_site_adjusted_test(df: pd.DataFrame, feature: str, label: str = "") -> dict:
    """OLS severity coefficient after adjusting for age + site."""
    from numpy.linalg import lstsq

    valid = df[[feature, "severity", "age", "clinical_site"]].dropna()
    if len(valid) < 50:
        return {"feature": label or feature, "n": 0}

    site_dum = pd.get_dummies(valid["clinical_site"], prefix="site", drop_first=True)
    X = np.column_stack([valid["severity"].values, valid["age"].values, site_dum.values, np.ones(len(valid))])
    y = valid[feature].values

    beta, residuals, rank, sv = lstsq(X, y, rcond=None)
    y_pred = X @ beta
    resid = y - y_pred
    n, p = X.shape
    mse = np.sum(resid ** 2) / (n - p)
    se = np.sqrt(mse * np.diag(np.linalg.inv(X.T @ X)))[0]
    t_stat = beta[0] / se
    p_val = 2 * stats.t.sf(abs(t_stat), n - p)

    return {
        "feature": label or feature,
        "n": len(valid),
        "severity_coef": beta[0],
        "severity_se": se,
        "severity_t": t_stat,
        "severity_p": p_val,
    }


def test_h_new01(df: pd.DataFrame) -> pd.DataFrame:
    """H-NEW01: Frequency-resolved coupling — which band shows largest severity gradient?"""
    print("\n" + "=" * 60)
    print("H-NEW01: FREQUENCY-RESOLVED COUPLING")
    print("=" * 60)

    band_cols = [c for c in df.columns if c.startswith("coherence_")]
    rows = []
    for col in band_cols:
        r = severity_test(df, col, label=col)
        r2 = age_site_adjusted_test(df, col, label=col)
        r.update({k: v for k, v in r2.items() if k not in r})
        rows.append(r)

    result = pd.DataFrame(rows)
    if len(result) > 0 and "kw_p" in result.columns:
        _, fdr, _, _ = multipletests(result["kw_p"].fillna(1), method="fdr_bh")
        result["fdr_p"] = fdr

    print(result.to_string(index=False, float_format="%.4f"))
    result.to_csv(result_path("h_new01_frequency_coupling.csv"), index=False)

    # Key test: is the 2-4h band d larger than broadband d?
    if "d_h_vs_id" in result.columns:
        bb = result.loc[result["feature"] == "coherence_broadband", "d_h_vs_id"]
        ultr = result.loc[result["feature"].isin(["coherence_1_2h", "coherence_2_4h"]), "d_h_vs_id"]
        if len(bb) and len(ultr):
            print(f"\nBroadband d = {bb.iloc[0]:.3f}")
            print(f"1-2h band d = {ultr.iloc[0]:.3f}")
            print(f"Timescale selectivity: {'SUPPORTED' if ultr.max() > bb.iloc[0] * 1.2 else 'NOT SUPPORTED'}")

    return result


def test_h_new17(df: pd.DataFrame) -> pd.DataFrame:
    """H-NEW17: Diurnal coupling rhythm flattening with severity."""
    print("\n" + "=" * 60)
    print("H-NEW17: DIURNAL COUPLING RHYTHM")
    print("=" * 60)

    diurnal_cols = ["diurnal_amplitude", "diurnal_range", "diurnal_sd", "diurnal_cosinor_r2", "diurnal_mesor"]
    diurnal_cols = [c for c in diurnal_cols if c in df.columns]
    block_cols = [c for c in df.columns if c.startswith("diurnal_r_") and not c.startswith("diurnal_r_act")]
    act_adj_cols = [c for c in df.columns if c.startswith("diurnal_r_act_adj_")]

    rows = []
    for col in diurnal_cols + block_cols:
        r = severity_test(df, col, label=col)
        r2 = age_site_adjusted_test(df, col, label=col)
        r.update({k: v for k, v in r2.items() if k not in r})
        rows.append(r)

    result = pd.DataFrame(rows)
    if len(result) > 0 and "kw_p" in result.columns:
        pvals = result["kw_p"].fillna(1)
        _, fdr, _, _ = multipletests(pvals, method="fdr_bh")
        result["fdr_p"] = fdr

    print(result.to_string(index=False, float_format="%.4f"))
    result.to_csv(result_path("h_new17_diurnal_coupling.csv"), index=False)

    # Key test: amplitude flattening
    amp_row = result.loc[result["feature"] == "diurnal_amplitude"]
    if len(amp_row):
        d = amp_row["d_h_vs_id"].iloc[0]
        print(f"\nDiurnal amplitude Cohen's d (H vs ID): {d:.3f}")
        print(f"Amplitude flattening: {'SUPPORTED' if d < -0.15 else 'NOT SUPPORTED (d > -0.15)'}")

    return result


def test_h_new06(df: pd.DataFrame) -> pd.DataFrame:
    """H-NEW06: Nocturnal coupling → next-day glycemia."""
    print("\n" + "=" * 60)
    print("H-NEW06: NOCTURNAL COUPLING → NEXT-DAY GLUCOSE")
    print("=" * 60)

    nocturnal_cols = [c for c in df.columns if c.startswith("nocturnal_")]
    rows = []
    for col in nocturnal_cols:
        r = severity_test(df, col, label=col)
        r2 = age_site_adjusted_test(df, col, label=col)
        r.update({k: v for k, v in r2.items() if k not in r})
        rows.append(r)

    result = pd.DataFrame(rows)
    if len(result) > 0 and "kw_p" in result.columns:
        pvals = result["kw_p"].fillna(1)
        _, fdr, _, _ = multipletests(pvals, method="fdr_bh")
        result["fdr_p"] = fdr

    print(result.to_string(index=False, float_format="%.4f"))
    result.to_csv(result_path("h_new06_nocturnal_coupling.csv"), index=False)

    # Key test: within-person nocturnal coupling → next-day glucose
    rho_col = "nocturnal_r_vs_day_glucose_mean_rho"
    if rho_col in df.columns:
        valid = df[rho_col].dropna()
        print(f"\nWithin-person nocturnal coupling → next-day glucose rho:")
        print(f"  N = {len(valid)}")
        print(f"  Mean rho = {valid.mean():.4f}")
        print(f"  % positive = {(valid > 0).mean():.1%}")
        t_stat, p_val = stats.ttest_1samp(valid, 0)
        print(f"  One-sample t-test vs 0: t={t_stat:.2f}, p={p_val:.2e}")
        print(f"  Prediction: {'SUPPORTED' if p_val < 0.05 and valid.mean() > 0 else 'NOT SUPPORTED'}")

    return result


def test_h_new13(df: pd.DataFrame) -> pd.DataFrame:
    """H-NEW13: Sleep-wake transition coupling reorganization."""
    print("\n" + "=" * 60)
    print("H-NEW13: SLEEP-WAKE COUPLING REORGANIZATION")
    print("=" * 60)

    transition_cols = [c for c in df.columns if any(c.startswith(p) for p in
                       ["pre_wake", "post_wake", "wake_coupling", "reorganization", "stable_coupling",
                        "coupling_change", "n_wake"])]

    rows = []
    for col in transition_cols:
        r = severity_test(df, col, label=col)
        r2 = age_site_adjusted_test(df, col, label=col)
        r.update({k: v for k, v in r2.items() if k not in r})
        rows.append(r)

    result = pd.DataFrame(rows)
    if len(result) > 0 and "kw_p" in result.columns:
        pvals = result["kw_p"].fillna(1)
        _, fdr, _, _ = multipletests(pvals, method="fdr_bh")
        result["fdr_p"] = fdr

    print(result.to_string(index=False, float_format="%.4f"))
    result.to_csv(result_path("h_new13_sleepwake_transition.csv"), index=False)

    # Key test: reorganization time
    reorg_col = "reorganization_time_min"
    if reorg_col in df.columns:
        for g in STUDY_GROUP_ORDER:
            vals = df.loc[df["study_group"] == g, reorg_col].dropna()
            print(f"  {GROUP_SHORT[g]}: median reorg time = {vals.median():.0f} min (N={len(vals)})")

    return result


def main():
    df = load_combined()
    df.to_parquet(result_path("hypothesis_timeseries_features.parquet"))

    r01 = test_h_new01(df)
    r17 = test_h_new17(df)
    r06 = test_h_new06(df)
    r13 = test_h_new13(df)

    # Combined summary
    print("\n" + "=" * 60)
    print("COMBINED SUMMARY")
    print("=" * 60)
    print(f"Total participants: {len(df)}")
    print(f"Features extracted: {len(df.columns) - 6}")  # subtract metadata cols

    for name, result_df in [("H-NEW01", r01), ("H-NEW17", r17), ("H-NEW06", r06), ("H-NEW13", r13)]:
        if "fdr_p" in result_df.columns:
            sig = (result_df["fdr_p"] < 0.05).sum()
            print(f"  {name}: {sig}/{len(result_df)} features FDR < 0.05")


if __name__ == "__main__":
    main()
