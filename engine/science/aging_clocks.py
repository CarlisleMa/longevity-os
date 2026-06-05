"""Train system-specific and functional aging clocks via Ridge regression.

Phase 2: Trains 7 system-specific clocks from clinical labs/vitals/cognition
and 6 functional clocks from multimodal wearable/CGM/environment features.
Computes AgeAccel (age acceleration) for all 2,280 participants.

Usage:
    python -m scripts.aging_clocks
"""

import warnings
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.preprocessing import StandardScaler

from .config import RESULTS_DIR, result_path, result_variant_path
from .splits import require_split_column

# ── Clock definitions ────────────────────────────────────────────────────────
# Each maps clock name -> list of feature column names.

SYSTEM_CLOCKS = {
    "immune_inflammatory": [
        "crp", "wbc", "rbc", "hemoglobin", "platelets", "rdw",
    ],
    "metabolic": [
        "hba1c", "glucose", "triglycerides", "hdl", "ldl", "total_cholesterol",
        # Extended if clinical_scores available:
        "homa_ir", "tyg_index",
    ],
    "renal": [
        "creatinine", "bun", "bun_cr_ratio", "urine_albumin",
        "urine_creatinine", "sodium", "potassium", "chloride", "co2", "calcium",
    ],
    "hepatic": [
        "alt", "ast", "alk_phos", "bilirubin_total", "albumin", "globulin",
        "total_protein", "ag_ratio",
    ],
    "cardiovascular": [
        "sbp", "dbp", "heart_rate", "troponin_t", "nt_probnp",
        # Extended if clinical_scores available:
        "pulse_pressure",
    ],
    "hematologic": [
        "rdw", "mcv", "mch", "mchc", "hemoglobin", "hematocrit",
        "rbc", "wbc", "platelets",
    ],
    "cognitive": [
        "moca_total", "moca_abstraction", "moca_clock", "moca_cube",
        "moca_delayed_recall", "moca_digitspan", "moca_fluency",
        "moca_lettera", "moca_naming", "moca_orientation",
        "moca_repetition", "moca_subtraction", "moca_trails",
        "moca_memory1", "moca_memory2", "moca_combined_mis",
    ],
}

FUNCTIONAL_CLOCKS = {
    "circadian": [
        "wear_is", "wear_iv", "wear_m10", "wear_l5", "wear_ra",
        "wear_cosinor_amplitude", "wear_cosinor_acrophase", "wear_cosinor_mesor",
    ],
    "cgm_metabolic": [
        "cgm_mean_glucose", "cgm_cv_glucose", "cgm_tir", "cgm_mage",
        "cgm_gri", "cgm_dawn_phenomenon", "cgm_nocturnal_mean",
        "cgm_nocturnal_cv",
    ],
    "autonomic": [
        "wear_resting_hr", "wear_nocturnal_hr", "wear_diurnal_hr",
        "wear_nocturnal_dip_pct",
    ],
    "sleep": [
        "wear_mean_tst", "wear_mean_se", "wear_mean_waso",
        "wear_mean_rem_pct", "wear_mean_deep_pct", "wear_sleep_regularity",
    ],
    "physical": [
        "wear_mean_daily_steps", "wear_mean_active_calories",
    ],
    "environmental": [
        "env_mean_pm25", "env_bright_light_hours",
        "env_evening_light_exposure", "env_mean_temp", "env_temp_range",
    ],
}

ALL_CLOCKS = {**SYSTEM_CLOCKS, **FUNCTIONAL_CLOCKS}

# Features that come from clinical_scores.parquet (optional)
_CLINICAL_SCORE_FEATURES = {"homa_ir", "tyg_index", "pulse_pressure"}

# ── Paths ─────────────────────────────────────────────────────────────────────
FEATURE_MATRIX_PATH = result_path("feature_matrix.parquet")
CLINICAL_SCORES_PATH = result_path("clinical_scores.parquet")
MULTIMODAL_FEATURES_PATH = result_path("multimodal_features.parquet")
AGE_ACCEL_PATH = result_path("age_accel.parquet")
CLOCK_PERF_PATH = result_path("clock_performance.csv")

MISSING_THRESHOLD = 0.30  # drop features with >30% missing


def validate_split_column(fm: pd.DataFrame, split_column: str) -> dict[str, int]:
    """Validate the fixed train/validation/test split before clock training."""
    if split_column not in fm.columns:
        raise ValueError(f"feature_matrix is missing {split_column}")
    if "age" not in fm.columns:
        raise ValueError("feature_matrix is missing age")
    if not fm.index.is_unique:
        raise ValueError("feature_matrix index must be unique person_id values")

    splits = fm[split_column].astype(str)
    counts = splits.value_counts().to_dict()
    missing = {"train", "val", "test"} - set(counts)
    if missing:
        raise ValueError(f"{split_column} missing required split(s): {sorted(missing)}")
    extra = set(counts) - {"train", "val", "test"}
    if extra:
        raise ValueError(f"{split_column} contains unexpected value(s): {sorted(extra)}")
    if fm["age"].isna().any():
        raise ValueError("feature_matrix age column contains missing values")
    if counts["train"] < 50 or counts["val"] < 20 or counts["test"] < 20:
        raise ValueError(f"{split_column} counts look too small: {counts}")
    return {k: int(counts[k]) for k in ["train", "val", "test"]}


def residualize_age_accel(
    predicted_age: np.ndarray, actual_age: np.ndarray, fit_mask: np.ndarray
) -> np.ndarray:
    """Remove trivial age correlation from AgeAccel.

    Fit the residualization model on the training rows only, then apply it to
    all rows. Fitting this correction on all participants leaks test ages into
    the derived AgeAccel target.
    """
    raw_accel = predicted_age - actual_age
    fit_mask = np.asarray(fit_mask, dtype=bool)
    valid_fit = fit_mask & np.isfinite(actual_age) & np.isfinite(raw_accel)
    valid_all = np.isfinite(actual_age) & np.isfinite(raw_accel)
    residuals = np.full_like(raw_accel, np.nan, dtype=np.float64)
    if valid_fit.sum() < 2:
        residuals[valid_all] = raw_accel[valid_all]
        return residuals

    lr = LinearRegression()
    lr.fit(actual_age[valid_fit].reshape(-1, 1), raw_accel[valid_fit])
    expected = lr.predict(actual_age[valid_all].reshape(-1, 1))
    residuals[valid_all] = raw_accel[valid_all] - expected
    return residuals


def train_clock(
    features_df: pd.DataFrame,
    age: np.ndarray,
    train_mask: np.ndarray,
    test_mask: np.ndarray,
    clock_name: str,
    feature_cols: list[str],
    split_column: str,
) -> tuple[np.ndarray, np.ndarray, dict] | None:
    """Train one aging clock via RidgeCV.

    Parameters
    ----------
    features_df : DataFrame with all candidate features (2280 rows).
    age : 1-D array of chronological ages (length 2280).
    train_mask : boolean mask for training rows.
    test_mask : boolean mask for test rows.
    clock_name : human-readable name of this clock.
    feature_cols : candidate feature columns for this clock.

    Returns
    -------
    (predicted_ages, age_accel, metrics_dict)  or  None if the clock
    cannot be trained (too few features).
    """
    # -- 1. Select available features -------------------------------------------
    available = [c for c in feature_cols if c in features_df.columns]
    missing_cols = [c for c in feature_cols if c not in features_df.columns]
    if missing_cols:
        print(f"  [{clock_name}] Missing columns (skipped): {missing_cols}")

    if len(available) == 0:
        print(f"  [{clock_name}] No features available -- skipping clock.")
        return None

    X_all = features_df[available].values.astype(np.float64)
    y_all = age.astype(np.float64)

    # -- 1b. Replace inf with NaN and clip extreme outliers --------------------
    X_all[~np.isfinite(X_all)] = np.nan
    for col_idx in range(X_all.shape[1]):
        col = X_all[:, col_idx]
        train_col = col[train_mask]
        valid = train_col[np.isfinite(train_col)]
        if len(valid) > 10:
            q1, q3 = np.nanpercentile(valid, [25, 75])
            iqr = q3 - q1
            lo, hi = q1 - 5 * iqr, q3 + 5 * iqr
            col[(col < lo) | (col > hi)] = np.nan
            X_all[:, col_idx] = col

    # -- 2. Drop features with >30% missing in the training split --------------
    miss_frac = np.isnan(X_all[train_mask]).mean(axis=0)
    keep_mask = miss_frac <= MISSING_THRESHOLD
    kept_names = [available[i] for i in range(len(available)) if keep_mask[i]]
    dropped = [available[i] for i in range(len(available)) if not keep_mask[i]]
    if dropped:
        print(f"  [{clock_name}] Dropped (>{MISSING_THRESHOLD*100:.0f}% missing): {dropped}")

    if len(kept_names) == 0:
        print(f"  [{clock_name}] All features exceed missing threshold -- skipping.")
        return None

    X_all = X_all[:, keep_mask]

    # -- 3. Split ---------------------------------------------------------------
    X_train, y_train = X_all[train_mask], y_all[train_mask]
    X_test, y_test = X_all[test_mask], y_all[test_mask]

    # -- 4. Median imputation (fit on train) ------------------------------------
    imputer = SimpleImputer(strategy="median")
    X_train = imputer.fit_transform(X_train)
    X_test = imputer.transform(X_test)
    X_all_imp = imputer.transform(X_all)

    # -- 5. Scale (fit on imputed train only) -----------------------------------
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    X_all_scaled = scaler.transform(X_all_imp)

    # -- 6. RidgeCV -------------------------------------------------------------
    alphas = [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]
    ridge = RidgeCV(alphas=alphas, cv=5)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ridge.fit(X_train, y_train)

    # -- 7. Predict on all 2,280 -----------------------------------------------
    predicted = ridge.predict(X_all_scaled)
    pred_test = ridge.predict(X_test)

    # -- 8-9. AgeAccel (residualized) ------------------------------------------
    age_accel = residualize_age_accel(predicted, y_all, train_mask)

    # -- 10. Metrics on test set ------------------------------------------------
    mae = np.mean(np.abs(pred_test - y_test))
    ss_res = np.sum((pred_test - y_test) ** 2)
    ss_tot = np.sum((y_test - y_test.mean()) ** 2)
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    r_val, _ = pearsonr(pred_test, y_test)

    metrics = {
        "clock_name": clock_name,
        "n_features": len(kept_names),
        "features_used": ", ".join(kept_names),
        "n_train": int(train_mask.sum()),
        "n_test": int(test_mask.sum()),
        "split_column": split_column,
        "mae": round(mae, 3),
        "r_squared": round(r_squared, 4),
        "pearson_r": round(r_val, 4),
        "best_alpha": ridge.alpha_,
    }

    return predicted, age_accel, metrics


def train_all_clocks(
    split_column: str = "recommended_split",
    output_suffix: str | None = None,
) -> None:
    """Train all aging clocks and save outputs."""
    print("=" * 72)
    print("Phase 2: Training Aging Clocks")
    print("=" * 72)

    # ── Load feature matrix ───────────────────────────────────────────────
    if not FEATURE_MATRIX_PATH.exists():
        raise FileNotFoundError(
            f"Feature matrix not found at {FEATURE_MATRIX_PATH}. "
            "Run Phase 1 first (scripts.features)."
        )

    fm = pd.read_parquet(FEATURE_MATRIX_PATH)
    print(f"Loaded feature matrix: {fm.shape[0]} participants x {fm.shape[1]} columns")

    # ── Merge optional clinical scores ────────────────────────────────────
    if CLINICAL_SCORES_PATH.exists():
        cs = pd.read_parquet(CLINICAL_SCORES_PATH)
        merge_cols = [c for c in _CLINICAL_SCORE_FEATURES if c in cs.columns]
        if merge_cols:
            # Only bring in columns not already present
            new_cols = [c for c in merge_cols if c not in fm.columns]
            if new_cols:
                fm = fm.join(cs[new_cols], how="left")
                print(f"Merged clinical scores: {new_cols}")
            else:
                print("Clinical scores columns already present in feature matrix.")
        else:
            print("Warning: clinical_scores.parquet exists but has no expected columns.")
    else:
        print("Note: clinical_scores.parquet not found -- metabolic/cardiovascular "
              "clocks will use base features only.")

    # ── Merge optional multimodal features ────────────────────────────────
    has_multimodal = False
    if MULTIMODAL_FEATURES_PATH.exists():
        mf = pd.read_parquet(MULTIMODAL_FEATURES_PATH)
        new_cols = [c for c in mf.columns if c not in fm.columns]
        if new_cols:
            fm = fm.join(mf[new_cols], how="left")
            print(f"Merged multimodal features: {len(new_cols)} columns")
            has_multimodal = True
        else:
            print("Multimodal columns already present.")
            has_multimodal = True
    else:
        print("Warning: multimodal_features.parquet not found -- "
              "functional clocks (circadian, CGM, autonomic, sleep, physical, "
              "environmental) will be SKIPPED.")

    # ── Determine which clocks to train ───────────────────────────────────
    clocks_to_train = dict(SYSTEM_CLOCKS)
    if has_multimodal:
        clocks_to_train.update(FUNCTIONAL_CLOCKS)
    else:
        print(f"\nSkipping {len(FUNCTIONAL_CLOCKS)} functional clocks "
              f"(no multimodal data).")

    # ── Prepare arrays ────────────────────────────────────────────────────
    fm = require_split_column(fm, split_column)
    split_counts = validate_split_column(fm, split_column)
    age = fm["age"].values.astype(np.float64)
    split = fm[split_column].astype(str)
    train_mask = split.eq("train").values
    val_mask = split.eq("val").values
    test_mask = split.eq("test").values

    print(f"\nTrain: {train_mask.sum()}, Val: {val_mask.sum()}, Test: {test_mask.sum()}, "
          f"Total: {len(fm)}")
    print(f"Validated split column {split_column}: {split_counts}")
    print("-" * 72)

    # ── Train each clock ──────────────────────────────────────────────────
    results_df = pd.DataFrame(index=fm.index)
    results_df["age"] = age
    perf_rows = []

    for clock_name, feature_cols in clocks_to_train.items():
        print(f"\nTraining: {clock_name}")
        result = train_clock(
            features_df=fm,
            age=age,
            train_mask=train_mask,
            test_mask=test_mask,
            clock_name=clock_name,
            feature_cols=feature_cols,
            split_column=split_column,
        )
        if result is None:
            continue

        predicted, age_accel, metrics = result
        results_df[f"{clock_name}_predicted_age"] = predicted
        results_df[f"{clock_name}_age_accel"] = age_accel
        perf_rows.append(metrics)

        print(f"  -> MAE={metrics['mae']:.2f}  R2={metrics['r_squared']:.3f}  "
              f"r={metrics['pearson_r']:.3f}  alpha={metrics['best_alpha']}  "
              f"({metrics['n_features']} features)")

    if not perf_rows:
        print("\nNo clocks were successfully trained.")
        return

    # ── Save outputs ──────────────────────────────────────────────────────
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    variant = output_suffix
    if variant is None and split_column != "recommended_split":
        variant = split_column
    age_accel_path = result_variant_path("age_accel.parquet", variant)
    clock_perf_path = result_variant_path("clock_performance.csv", variant)

    results_df.to_parquet(age_accel_path)
    print(f"\nSaved age acceleration data: {age_accel_path}")
    print(f"  Shape: {results_df.shape}")

    perf_df = pd.DataFrame(perf_rows)
    perf_df.to_csv(clock_perf_path, index=False)
    print(f"Saved clock performance: {clock_perf_path}")

    # ── Summary table ─────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("Clock Performance Summary")
    print("=" * 72)
    summary_cols = ["clock_name", "n_features", "mae", "r_squared", "pearson_r", "best_alpha"]
    print(perf_df[summary_cols].to_string(index=False))
    print("=" * 72)

    n_system = sum(1 for r in perf_rows if r["clock_name"] in SYSTEM_CLOCKS)
    n_functional = sum(1 for r in perf_rows if r["clock_name"] in FUNCTIONAL_CLOCKS)
    print(f"\nTrained {n_system} system clocks + {n_functional} functional clocks "
          f"= {len(perf_rows)} total")
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train system and functional aging clocks")
    parser.add_argument("--split-column", default="recommended_split",
                        help="Split column to use, e.g. recommended_split or balanced_split_v1")
    parser.add_argument("--output-suffix", default=None,
                        help="Optional artifact suffix. Defaults to split column for non-recommended splits.")
    args = parser.parse_args()
    train_all_clocks(split_column=args.split_column, output_suffix=args.output_suffix)
