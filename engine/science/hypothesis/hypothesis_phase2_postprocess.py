"""
Postprocess Phase 2 hypothesis features and run statistical tests.
  H-NEW03: Post-excursion HR response dynamics
  H-NEW10: Activity-glucose coupling reversal
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


def load_combined():
    shard_dir = RESULTS_DIR / "shards" / "hypothesis_phase2"
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
    df = df.join(cs[["frailty_index", "allostatic_load"]], how="left")
    df = df[df["study_group"].isin(STUDY_GROUP_ORDER)]
    df["severity"] = df["study_group"].map({g: i for i, g in enumerate(STUDY_GROUP_ORDER)})

    print(f"Combined: {len(df)} participants")
    print(f"Groups: {df['study_group'].value_counts().to_dict()}")
    return df


def severity_test(df, feature, label=""):
    groups = [df.loc[df["study_group"] == g, feature].dropna() for g in STUDY_GROUP_ORDER]
    groups = [g for g in groups if len(g) > 5]
    if len(groups) < 3:
        return {"feature": label or feature, "n": 0}
    kw_stat, kw_p = stats.kruskal(*groups)
    valid = df[[feature, "severity"]].dropna()
    r, p_trend = stats.spearmanr(valid["severity"], valid[feature])
    h = df.loc[df["study_group"] == "healthy", feature].dropna()
    ins = df.loc[df["study_group"] == "insulin_dependent", feature].dropna()
    pooled_sd = np.sqrt((h.var() * (len(h) - 1) + ins.var() * (len(ins) - 1)) / (len(h) + len(ins) - 2))
    d = (ins.mean() - h.mean()) / pooled_sd if pooled_sd > 0 else 0
    medians = {GROUP_SHORT.get(g, g): df.loc[df["study_group"] == g, feature].median() for g in STUDY_GROUP_ORDER}
    return {"feature": label or feature, "n": int(valid[feature].notna().sum()),
            "kw_stat": kw_stat, "kw_p": kw_p, "trend_r": r, "trend_p": p_trend,
            "d_h_vs_id": d, **{f"med_{k}": v for k, v in medians.items()}}


def test_hypothesis(df, cols, name):
    print(f"\n{'=' * 60}")
    print(f"{name}")
    print("=" * 60)
    cols = [c for c in cols if c in df.columns]
    rows = [severity_test(df, col) for col in cols]
    result = pd.DataFrame(rows)
    if len(result) > 0 and "kw_p" in result.columns:
        _, fdr, _, _ = multipletests(result["kw_p"].fillna(1), method="fdr_bh")
        result["fdr_p"] = fdr
    print(result.to_string(index=False, float_format="%.4f"))
    return result


def main():
    df = load_combined()
    df.to_parquet(result_path("hypothesis_phase2_features.parquet"))

    exc_cols = [c for c in df.columns if c.startswith("exc_") or c.startswith("ctrl_") or c == "n_excursions"]
    act_cols = [c for c in df.columns if c.startswith("exercise_") or c.startswith("recovery_") or c.startswith("glucose_phase") or c == "n_activity_bouts"]

    r03 = test_hypothesis(df, exc_cols, "H-NEW03: POST-EXCURSION HR RESPONSE")
    r03.to_csv(result_path("h_new03_excursion_hr.csv"), index=False)

    r10 = test_hypothesis(df, act_cols, "H-NEW10: ACTIVITY-GLUCOSE REVERSAL")
    r10.to_csv(result_path("h_new10_activity_glucose.csv"), index=False)

    # Negative control check for H-NEW03
    if "exc_hr_auc_mean" in df.columns and "ctrl_hr_auc_mean" in df.columns:
        print("\nH-NEW03 Negative Control:")
        exc_auc = df["exc_hr_auc_mean"].dropna()
        ctrl_auc = df["ctrl_hr_auc_mean"].dropna()
        print(f"  Excursion AUC mean: {exc_auc.mean():.1f}")
        print(f"  Control AUC mean: {ctrl_auc.mean():.1f}")
        t, p = stats.ttest_rel(
            df.loc[df[["exc_hr_auc_mean", "ctrl_hr_auc_mean"]].dropna().index, "exc_hr_auc_mean"],
            df.loc[df[["exc_hr_auc_mean", "ctrl_hr_auc_mean"]].dropna().index, "ctrl_hr_auc_mean"]
        )
        print(f"  Paired t-test: t={t:.2f}, p={p:.2e}")

    print("\n" + "=" * 60)
    print("COMBINED SUMMARY")
    print("=" * 60)
    for name, rdf in [("H-NEW03", r03), ("H-NEW10", r10)]:
        if "fdr_p" in rdf.columns:
            sig = (rdf["fdr_p"] < 0.05).sum()
            print(f"  {name}: {sig}/{len(rdf)} features FDR < 0.05")


if __name__ == "__main__":
    main()
