"""Clinical composite aging scores for AI-READI.

Computes formula-based clinical composite aging scores for all 2,280 participants.
No ML training — these are direct formula applications using established methods.

Scores computed:
  1. KDM Biological Age (Klemera-Doubal Method)
  2. Homeostatic Dysregulation (Mahalanobis distance)
  3. Allostatic Load (binary risk flag sum)
  4. Frailty Index (deficit accumulation)
  5. HOMA-IR
  6. TyG Index
  7. QUICKI
  8. Pulse Pressure
  9. UACR (Urine Albumin-to-Creatinine Ratio)

References:
  - KDM: Klemera & Doubal 2006; Kwon & Belsky 2021 (BioAge R package)
  - HD: Cohen et al. 2014; Mahalanobis distance from healthy reference
  - AL: McEwen 1998; Seeman et al. 2001
  - FI: Rockwood & Mitnitski 2007; Searle et al. 2008
  - HOMA-IR: Matthews et al. 1985
  - TyG: Simental-Mendia et al. 2008
  - QUICKI: Katz et al. 2000
"""

import numpy as np
import pandas as pd
from scipy.spatial.distance import mahalanobis

from .config import RESULTS_DIR, result_path
from .features import load_feature_matrix

# ── Shared biomarker list for KDM and HD ─────────────────────────────────────
KDM_BIOMARKERS = [
    "albumin", "alk_phos", "bun", "creatinine", "crp",
    "hba1c", "total_cholesterol", "sbp",
]


# ── 1. KDM Biological Age ───────────────────────────────────────────────────

def compute_kdm(fm: pd.DataFrame, train_mask: pd.Series) -> pd.DataFrame:
    """Compute KDM Biological Age using the Klemera-Doubal method.

    Fits biomarker ~ age regressions on the training set, then applies the
    KDM formula to all participants.

    Parameters
    ----------
    fm : DataFrame
        Feature matrix (2280 rows), must contain KDM_BIOMARKERS + 'age'.
    train_mask : Series[bool]
        Boolean mask identifying training set rows.

    Returns
    -------
    DataFrame with columns: kdm_bio_age, kdm_age_accel
    """
    train = fm.loc[train_mask].copy()
    age = fm["age"].values
    age_train = train["age"].values

    # Variance of chronological age in training set
    age_var = np.var(age_train, ddof=1)

    slopes = []
    intercepts = []
    residual_vars = []

    for biomarker in KDM_BIOMARKERS:
        y_train = train[biomarker].values
        valid = np.isfinite(y_train) & np.isfinite(age_train)
        if valid.sum() < 10:
            # Not enough data — skip this biomarker
            slopes.append(np.nan)
            intercepts.append(np.nan)
            residual_vars.append(np.nan)
            continue

        x = age_train[valid]
        y = y_train[valid]

        # Simple linear regression: biomarker = intercept + slope * age
        slope, intercept = np.polyfit(x, y, 1)
        y_pred = intercept + slope * x
        residuals = y - y_pred
        resid_var = np.var(residuals, ddof=2)  # df = n - 2 for regression

        slopes.append(slope)
        intercepts.append(intercept)
        residual_vars.append(resid_var)

    slopes = np.array(slopes)
    intercepts = np.array(intercepts)
    residual_vars = np.array(residual_vars)

    # Apply KDM formula to all participants
    n = len(fm)
    kdm_ba = np.full(n, np.nan)

    for i in range(n):
        numerator = 0.0
        denominator = 0.0
        any_valid = False

        for k, biomarker in enumerate(KDM_BIOMARKERS):
            if np.isnan(slopes[k]) or np.isnan(residual_vars[k]):
                continue
            bk = fm[biomarker].iloc[i]
            if np.isnan(bk):
                continue

            any_valid = True
            sk = slopes[k]
            ik = intercepts[k]
            rv = residual_vars[k]

            numerator += sk * (bk - ik) / rv
            denominator += (sk ** 2) / rv

        if any_valid:
            # Add age term
            numerator += age[i] / age_var
            denominator += 1.0 / age_var
            kdm_ba[i] = numerator / denominator

    result = pd.DataFrame(index=fm.index)
    result["kdm_bio_age"] = kdm_ba
    result["kdm_age_accel"] = kdm_ba - age
    return result


# ── 2. Homeostatic Dysregulation ─────────────────────────────────────────────

def compute_homeostatic_dysregulation(
    fm: pd.DataFrame, train_mask: pd.Series
) -> pd.DataFrame:
    """Compute Homeostatic Dysregulation (HD) as log-Mahalanobis distance.

    Reference group: healthy study_group AND age 40-55 in the training set.
    Biomarkers: same as KDM.

    Parameters
    ----------
    fm : DataFrame
        Feature matrix.
    train_mask : Series[bool]
        Boolean mask for training set.

    Returns
    -------
    DataFrame with column: homeostatic_dysregulation
    """
    # Define reference group: healthy, age 40-55, training set
    ref_mask = (
        train_mask
        & (fm["study_group"] == "healthy")
        & (fm["age"] >= 40)
        & (fm["age"] <= 55)
    )
    ref = fm.loc[ref_mask, KDM_BIOMARKERS].dropna()

    if len(ref) < len(KDM_BIOMARKERS) + 1:
        raise ValueError(
            f"Reference group too small ({len(ref)}) for "
            f"{len(KDM_BIOMARKERS)} biomarkers"
        )

    # Compute reference mean and covariance
    ref_mean = ref.mean().values
    ref_cov = ref.cov().values.copy()  # copy to make writable

    # Regularize covariance to avoid singularity
    ref_cov += np.eye(ref_cov.shape[0]) * 1e-6

    # Invert covariance once
    cov_inv = np.linalg.inv(ref_cov)

    n = len(fm)
    hd = np.full(n, np.nan)

    for i in range(n):
        vals = fm[KDM_BIOMARKERS].iloc[i].values.astype(float)
        if np.any(np.isnan(vals)):
            continue
        hd[i] = mahalanobis(vals, ref_mean, cov_inv)

    # Log-transform for normality (add small epsilon to avoid log(0))
    hd_log = np.where(np.isfinite(hd), np.log(hd + 1e-8), np.nan)

    result = pd.DataFrame(index=fm.index)
    result["homeostatic_dysregulation"] = hd_log
    return result


# ── 3. Allostatic Load ──────────────────────────────────────────────────────

def compute_allostatic_load(fm: pd.DataFrame) -> pd.DataFrame:
    """Compute Allostatic Load as a count of binary risk flags (0-12).

    Thresholds based on established clinical cutoffs.
    """
    flags = pd.DataFrame(index=fm.index)

    def _risk_flag(column: str, op: str, threshold: float) -> pd.Series:
        values = pd.to_numeric(fm[column], errors="coerce")
        if op == "gt":
            flag = values > threshold
        elif op == "lt":
            flag = values < threshold
        else:
            raise ValueError(f"Unsupported risk comparison: {op}")
        return flag.astype(float).where(values.notna(), np.nan)

    flags["sbp_high"] = _risk_flag("sbp", "gt", 140)
    flags["dbp_high"] = _risk_flag("dbp", "gt", 90)
    flags["hr_high"] = _risk_flag("heart_rate", "gt", 80)
    flags["hba1c_high"] = _risk_flag("hba1c", "gt", 5.7)
    flags["tc_high"] = _risk_flag("total_cholesterol", "gt", 240)
    flags["hdl_low"] = _risk_flag("hdl", "lt", 40)
    flags["tg_high"] = _risk_flag("triglycerides", "gt", 150)
    flags["bmi_high"] = _risk_flag("bmi", "gt", 30)
    flags["whr_high"] = _risk_flag("whr", "gt", 0.90)
    flags["crp_high"] = _risk_flag("crp", "gt", 3.0)       # mg/L
    flags["creat_high"] = _risk_flag("creatinine", "gt", 1.2)  # mg/dL
    flags["albumin_low"] = _risk_flag("albumin", "lt", 3.5)    # g/dL

    # Count known risk flags; rows with no measured inputs stay NaN.
    result = pd.DataFrame(index=fm.index)
    result["allostatic_load"] = flags.sum(axis=1, skipna=True, min_count=1)

    return result


# ── 4. Frailty Index ────────────────────────────────────────────────────────

def compute_frailty_index(fm: pd.DataFrame) -> pd.DataFrame:
    """Compute Frailty Index as proportion of deficits present.

    Deficits include 30 condition booleans, abnormal lab thresholds,
    depression, cognitive impairment, neuropathy, and vision impairment.
    Score = count of deficits / total possible deficits (range 0-1).
    """
    # 30 condition boolean columns
    condition_cols = [c for c in fm.columns if c.startswith("has_")]

    # Build deficit DataFrame: True = deficit present, NaN = not assessable
    deficits = pd.DataFrame(index=fm.index)

    # Condition deficits (30)
    for col in condition_cols:
        deficits[col] = fm[col].astype(float)  # True=1, False=0

    # Abnormal lab deficits (8)
    deficits["def_hba1c"] = (fm["hba1c"] > 6.5).astype(float).where(fm["hba1c"].notna())
    deficits["def_creatinine"] = (fm["creatinine"] > 1.5).astype(float).where(fm["creatinine"].notna())
    deficits["def_albumin"] = (fm["albumin"] < 3.5).astype(float).where(fm["albumin"].notna())
    deficits["def_hemoglobin"] = (fm["hemoglobin"] < 12).astype(float).where(fm["hemoglobin"].notna())
    deficits["def_bmi"] = ((fm["bmi"] > 30) | (fm["bmi"] < 18.5)).astype(float).where(fm["bmi"].notna())
    deficits["def_sbp"] = (fm["sbp"] > 160).astype(float).where(fm["sbp"].notna())
    deficits["def_dbp"] = (fm["dbp"] > 100).astype(float).where(fm["dbp"].notna())
    deficits["def_hr"] = (fm["heart_rate"] > 100).astype(float).where(fm["heart_rate"].notna())

    # Depression deficit (1)
    deficits["def_depression"] = (fm["cesd_total"] >= 10).astype(float).where(fm["cesd_total"].notna())

    # Cognitive deficit (1)
    deficits["def_cognitive"] = (fm["moca_total"] < 26).astype(float).where(fm["moca_total"].notna())

    # Neuropathy deficit (1)
    mono_left = fm["monofilament_left_felt"] < 8
    mono_right = fm["monofilament_right_felt"] < 8
    neuropathy = (mono_left | mono_right)
    neuropathy_assessable = fm["monofilament_left_felt"].notna() | fm["monofilament_right_felt"].notna()
    deficits["def_neuropathy"] = neuropathy.astype(float).where(neuropathy_assessable)

    # Vision deficit (1)
    deficits["def_vision"] = (fm["logmar_photopic_od"] > 0.3).astype(float).where(fm["logmar_photopic_od"].notna())

    # Compute FI = deficits present / deficits assessable
    deficit_sum = deficits.sum(axis=1, skipna=True)
    deficit_count = deficits.notna().sum(axis=1)

    result = pd.DataFrame(index=fm.index)
    result["frailty_index"] = np.where(
        deficit_count > 0,
        deficit_sum / deficit_count,
        np.nan,
    )
    return result


# ── 5. Insulin Resistance Scores ────────────────────────────────────────────

def compute_insulin_resistance(fm: pd.DataFrame) -> pd.DataFrame:
    """Compute HOMA-IR, TyG Index, and QUICKI.

    Critical unit conversion: insulin is stored as ng/L in the feature matrix.
    Divide by 0.04034 to convert to uU/mL.
    """
    result = pd.DataFrame(index=fm.index)

    # Unit conversion: ng/L -> uU/mL
    insulin_uu_ml = fm["insulin"] / 0.04034
    glucose_mg_dl = fm["glucose"]

    # HOMA-IR = (insulin_uU_mL * glucose_mg_dL) / 405
    result["homa_ir"] = (insulin_uu_ml * glucose_mg_dl) / 405.0

    # TyG = ln((triglycerides_mg_dL * glucose_mg_dL) / 2)
    # This is the 8.x-scale convention used in most adult metabolic studies.
    tg_glucose_product = fm["triglycerides"] * glucose_mg_dl / 2.0
    # Guard against non-positive values before log
    result["tyg_index"] = np.where(
        (tg_glucose_product > 0) & tg_glucose_product.notna(),
        np.log(tg_glucose_product),
        np.nan,
    )

    # QUICKI = 1 / (log10(insulin_uU_mL) + log10(glucose_mg_dL))
    # Guard against non-positive values before log10
    log_ins = np.where(
        (insulin_uu_ml > 0) & insulin_uu_ml.notna(),
        np.log10(insulin_uu_ml),
        np.nan,
    )
    log_gluc = np.where(
        (glucose_mg_dl > 0) & glucose_mg_dl.notna(),
        np.log10(glucose_mg_dl),
        np.nan,
    )
    denom = log_ins + log_gluc
    result["quicki"] = np.where(
        np.isfinite(denom) & (denom != 0),
        1.0 / denom,
        np.nan,
    )

    return result


# ── 6. Vascular Scores ──────────────────────────────────────────────────────

def compute_vascular(fm: pd.DataFrame) -> pd.DataFrame:
    """Compute Pulse Pressure and UACR."""
    result = pd.DataFrame(index=fm.index)

    # Pulse Pressure = SBP - DBP
    result["pulse_pressure"] = fm["sbp"] - fm["dbp"]

    # UACR = urine_albumin / urine_creatinine
    result["uacr"] = np.where(
        (fm["urine_creatinine"] > 0) & fm["urine_creatinine"].notna() & fm["urine_albumin"].notna(),
        fm["urine_albumin"] / fm["urine_creatinine"],
        np.nan,
    )

    return result


# ── Main orchestrator ────────────────────────────────────────────────────────

def compute_all_scores(fm: pd.DataFrame | None = None) -> pd.DataFrame:
    """Compute all clinical composite aging scores.

    Parameters
    ----------
    fm : DataFrame, optional
        Feature matrix. If None, loads from disk/builds it.

    Returns
    -------
    DataFrame with one row per person_id and all score columns.
    """
    if fm is None:
        fm = load_feature_matrix()

    print(f"Feature matrix: {fm.shape[0]} participants x {fm.shape[1]} features")

    # Training mask: fit parameters only on training set
    train_mask = fm["recommended_split"] == "train"
    print(f"Training set: {train_mask.sum()} participants")

    # Compute each score block
    print("Computing KDM Biological Age...")
    kdm = compute_kdm(fm, train_mask)

    print("Computing Homeostatic Dysregulation...")
    hd = compute_homeostatic_dysregulation(fm, train_mask)

    print("Computing Allostatic Load...")
    al = compute_allostatic_load(fm)

    print("Computing Frailty Index...")
    fi = compute_frailty_index(fm)

    print("Computing Insulin Resistance scores (HOMA-IR, TyG, QUICKI)...")
    ir = compute_insulin_resistance(fm)

    print("Computing Vascular scores (Pulse Pressure, UACR)...")
    vasc = compute_vascular(fm)

    # Combine all scores
    scores = pd.concat([kdm, hd, al, fi, ir, vasc], axis=1)

    # Verify expected columns
    expected_cols = [
        "kdm_bio_age", "kdm_age_accel", "homeostatic_dysregulation",
        "allostatic_load", "frailty_index", "homa_ir", "tyg_index",
        "quicki", "pulse_pressure", "uacr",
    ]
    for col in expected_cols:
        assert col in scores.columns, f"Missing expected column: {col}"

    # Keep only score columns in specified order
    scores = scores[expected_cols]

    print(f"\nScores computed: {scores.shape[0]} rows x {scores.shape[1]} columns")
    print(f"Non-null counts per score:")
    for col in expected_cols:
        n_valid = scores[col].notna().sum()
        print(f"  {col}: {n_valid}/{len(scores)} ({scores[col].isna().sum()} missing)")

    return scores


if __name__ == "__main__":
    scores = compute_all_scores()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = result_path("clinical_scores.parquet")
    scores.to_parquet(out_path)
    print(f"\nSaved to {out_path}")

    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    print(scores.describe().to_string())
