"""All-feature multimodal aging clock and paper figure generation.

Phase 7: Trains a multimodal chronological-age clock from raw feature tables and
frozen embeddings, then produces publication-quality figures and summary tables.

Usage:
    python -m scripts.unified_clock
"""

import json
import sys
import warnings
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr, spearmanr, mannwhitneyu
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, "/oak/stanford/scg/lab_twc/mazijian/aireadi")

from scripts.config import RESULTS_DIR, result_path, result_variant_path
from scripts.features import load_feature_matrix
from scripts.splits import require_split_column

# ── Constants ─────────────────────────────────────────────────────────────────

FIGURES_DIR = RESULTS_DIR / "figures"

# Ordered by diabetes severity for consistent plotting
STUDY_GROUP_ORDER = [
    "healthy",
    "pre_diabetes_lifestyle_controlled",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled",
    "insulin_dependent",
]

STUDY_GROUP_LABELS = {
    "healthy": "Healthy",
    "pre_diabetes_lifestyle_controlled": "Pre-diabetes",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": "Oral/Non-insulin Meds",
    "insulin_dependent": "Insulin-dependent",
}

# Sequential blue palette for diabetes severity gradient
SEVERITY_COLORS = ["#c6dbef", "#6baed6", "#2171b5", "#08306b"]

# Categorical palette for aging subtypes
SUBTYPE_PALETTE = sns.color_palette("Set2", 8)

# System clock names (from Phase 2)
SYSTEM_CLOCK_NAMES = [
    "immune_inflammatory", "metabolic", "renal", "hepatic",
    "cardiovascular", "hematologic", "cognitive",
]

# Functional clock names (from Phase 2)
FUNCTIONAL_CLOCK_NAMES = [
    "circadian", "cgm_metabolic", "autonomic", "sleep",
    "physical", "environmental",
]

# Imaging clock names (from Phase 4)
IMAGING_CLOCK_NAMES = ["retinal", "cardiac"]


# ── Plotting setup ────────────────────────────────────────────────────────────

def _setup_plot_style():
    """Set publication-quality matplotlib defaults."""
    sns.set_style("whitegrid")
    plt.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
        "font.family": "sans-serif",
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


# ── Data loading ──────────────────────────────────────────────────────────────

def load_all_results() -> dict:
    """Load all available results from earlier phases."""
    print("Loading results from earlier phases...")
    results = {}

    fm = load_feature_matrix()
    results["feature_matrix"] = fm
    print(f"  Loaded feature_matrix: {fm.shape}")

    file_map = [
        ("clinical_scores", "clinical_scores.parquet"),
        ("multimodal_features", "multimodal_features.parquet"),
        ("retinal_embeddings", "retinal_embeddings.parquet"),
        ("cardiac_embeddings", "cardiac_embeddings.parquet"),
        ("age_accel", "age_accel.parquet"),
        ("retinal_age", "retinal_age_accel.parquet"),
        ("cardiac_age", "cardiac_age_accel.parquet"),
        ("subtypes", "aging_subtypes.csv"),
        ("clock_performance", "clock_performance.csv"),
        ("table1", "table1_by_study_group.csv"),
        ("pairwise_effect", "pairwise_effect_sizes.csv"),
        ("all_features_sg", "all_features_by_study_group.csv"),
        ("all_features_sg_adj", "all_features_by_study_group_age_adjusted.csv"),
    ]

    for name, filename in file_map:
        path = result_path(filename)
        if path.exists():
            if filename.endswith(".parquet"):
                results[name] = pd.read_parquet(path)
            else:
                results[name] = pd.read_csv(path)
            print(f"  Loaded {name}: {results[name].shape}")
        else:
            print(f"  {name} not found at {path}")

    return results


def _get_age_accel_columns(results: dict) -> tuple[pd.DataFrame, list[str]]:
    """Collect all available AgeAccel columns into a single DataFrame.

    Merges system + functional (from age_accel.parquet) and imaging
    (from retinal/cardiac parquets) AgeAccel values.

    Returns (combined_df, accel_col_names).
    """
    frames = []
    accel_cols = []

    # System + functional clocks from age_accel.parquet
    if "age_accel" in results:
        aa = _as_person_index(results["age_accel"])
        aa_cols = [c for c in aa.columns if c.endswith("_age_accel")]
        if aa_cols:
            frames.append(aa[aa_cols])
            accel_cols.extend(aa_cols)

    # Retinal AgeAccel
    if "retinal_age" in results:
        ra = _as_person_index(results["retinal_age"])
        ra_cols = [c for c in ra.columns if "age_accel" in c.lower()]
        if ra_cols:
            frames.append(ra[ra_cols])
            accel_cols.extend(ra_cols)

    # Cardiac AgeAccel
    if "cardiac_age" in results:
        ca = _as_person_index(results["cardiac_age"])
        ca_cols = [c for c in ca.columns if "age_accel" in c.lower()]
        if ca_cols:
            frames.append(ca[ca_cols])
            accel_cols.extend(ca_cols)

    if not frames:
        return pd.DataFrame(), []

    combined = pd.concat(frames, axis=1)
    return combined, accel_cols


def _residualize_age_accel(
    predicted: np.ndarray, actual: np.ndarray, fit_mask: np.ndarray
) -> np.ndarray:
    """Residualize predicted-actual against age using only fit rows."""
    raw = predicted - actual
    fit_mask = np.asarray(fit_mask, dtype=bool)
    valid_fit = fit_mask & np.isfinite(actual) & np.isfinite(raw)
    valid_all = np.isfinite(actual) & np.isfinite(raw)
    residuals = np.full_like(raw, np.nan, dtype=np.float64)
    if valid_fit.sum() < 2:
        residuals[valid_all] = raw[valid_all]
        return residuals

    lr = LinearRegression()
    lr.fit(actual[valid_fit].reshape(-1, 1), raw[valid_fit])
    expected = lr.predict(actual[valid_all].reshape(-1, 1))
    residuals[valid_all] = raw[valid_all] - expected
    return residuals


# ── 7a. Unified Multimodal Clock ─────────────────────────────────────────────

META_COLUMNS = {
    "age", "recommended_split", "study_group", "clinical_site",
    "study_visit_date", "person_id",
}
LEAKY_CLOCK_COLUMNS = {
    "kdm_bio_age", "kdm_age_accel",
}


def _as_person_index(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy indexed by string person_id."""
    out = df.copy()
    if "person_id" in out.columns:
        out["person_id"] = out["person_id"].astype(str)
        out = out.set_index("person_id")
    out.index = out.index.astype(str)
    return out


def _numeric_feature_block(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Select non-leaky numeric predictors and prefix columns by source."""
    df = _as_person_index(df)
    excluded: set[str] = set()
    for col in df.columns:
        lower = str(col).lower()
        if col in META_COLUMNS or col in LEAKY_CLOCK_COLUMNS:
            excluded.add(col)
        elif lower.endswith("_age_accel") or lower.endswith("_predicted_age"):
            excluded.add(col)
        elif lower in {"split", "clock_name", "features_used"}:
            excluded.add(col)

    numeric = df.drop(columns=[c for c in excluded if c in df.columns], errors="ignore")
    numeric = numeric.select_dtypes(include=[np.number]).copy()
    numeric.columns = [f"{prefix}__{c}" for c in numeric.columns]
    return numeric


def _build_multimodal_feature_table(results: dict) -> tuple[pd.DataFrame, list[str]]:
    """Build the all-feature predictor matrix for the multimodal clock.

    This intentionally uses raw feature tables and frozen embedding features,
    not AgeAccel residuals or other clock outputs.
    """
    blocks = [
        _numeric_feature_block(results["feature_matrix"], "clinical"),
    ]
    optional_blocks = [
        ("clinical_scores", "clinical_score"),
        ("multimodal_features", "multimodal"),
        ("retinal_embeddings", "retinal"),
        ("cardiac_embeddings", "cardiac"),
    ]
    for key, prefix in optional_blocks:
        if key in results and not results[key].empty:
            block = _numeric_feature_block(results[key], prefix)
            if not block.empty:
                blocks.append(block)

    features = pd.concat(blocks, axis=1)
    features = features.loc[:, ~features.columns.duplicated()]
    features = features.reindex(results["feature_matrix"].index.astype(str))
    return features, features.columns.tolist()


def _validate_splits(fm: pd.DataFrame, split_column: str) -> None:
    """Fail early if the selected split is missing or malformed."""
    if split_column not in fm.columns:
        raise ValueError(f"feature_matrix is missing {split_column}")
    splits = fm[split_column].astype(str)
    counts = splits.value_counts().to_dict()
    missing = {"train", "val", "test"} - set(counts)
    if missing:
        raise ValueError(f"{split_column} missing required split(s): {sorted(missing)}")
    if not fm.index.is_unique:
        raise ValueError("feature_matrix index must be unique person_id values")
    if counts["train"] < 50 or counts["val"] < 20 or counts["test"] < 20:
        raise ValueError(f"{split_column} counts look too small: {counts}")


def _fit_preprocess(
    X: np.ndarray,
    fit_mask: np.ndarray,
    missing_threshold: float = 0.50,
    clip_quantiles: tuple[float, float] | None = None,
) -> tuple[np.ndarray, np.ndarray, SimpleImputer, StandardScaler]:
    """Drop high-missing columns, optionally clip, impute, and scale with fit rows only."""
    X = X.astype(np.float64, copy=True)
    X[~np.isfinite(X)] = np.nan
    miss_frac = np.isnan(X[fit_mask]).mean(axis=0)
    keep = miss_frac <= missing_threshold
    if keep.sum() == 0:
        raise ValueError("All multimodal features exceed missingness threshold")

    X = X[:, keep]
    if clip_quantiles is not None:
        for col_idx in range(X.shape[1]):
            fit_values = X[fit_mask, col_idx]
            fit_values = fit_values[np.isfinite(fit_values)]
            if fit_values.size > 20:
                lo, hi = np.nanpercentile(fit_values, clip_quantiles)
                if np.isfinite(lo) and np.isfinite(hi) and lo < hi:
                    X[:, col_idx] = np.clip(X[:, col_idx], lo, hi)

    imputer = SimpleImputer(strategy="median")
    X_imp = imputer.fit_transform(X[fit_mask])
    scaler = StandardScaler()
    scaler.fit(X_imp)

    X_all_imp = imputer.transform(X)
    X_all_scaled = scaler.transform(X_all_imp)
    return X_all_scaled, keep, imputer, scaler


def _regression_metrics(pred: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    mae = mean_absolute_error(y, pred)
    r2 = r2_score(y, pred)
    r = pearsonr(pred, y)[0] if len(y) > 2 else np.nan
    return float(mae), float(r2), float(r)


def _select_ridge_alpha(
    X: np.ndarray,
    age: np.ndarray,
    train_mask: np.ndarray,
    val_mask: np.ndarray,
    alphas: np.ndarray,
) -> tuple[float, float, float, float]:
    """Select Ridge regularization by validation MAE without touching test rows."""
    records = []
    for alpha in alphas:
        model = Ridge(alpha=float(alpha))
        model.fit(X[train_mask], age[train_mask])
        pred = model.predict(X[val_mask])
        mae, r2, r = _regression_metrics(pred, age[val_mask])
        records.append((mae, r2, r, float(alpha)))
    val_mae, val_r2, val_r, selected_alpha = min(records, key=lambda x: x[0])
    return selected_alpha, val_mae, val_r2, val_r


def unified_clock(
    results: dict,
    split_column: str = "recommended_split",
    output_suffix: str | None = None,
    clip_outliers: bool = False,
) -> dict:
    """Train the multimodal/unified clock from raw features and embeddings.

    The previous implementation trained from AgeAccel residual dimensions.
    That is useful for phenotype summaries, but it is the wrong inductive bias
    for a multimodal age clock. This model trains directly on non-leaky numeric
    clinical, CGM, wearable, environment, retinal-embedding, and ECG-embedding
    features. Test rows are held out until the final evaluation.
    """
    fm = _as_person_index(results["feature_matrix"])
    fm = require_split_column(fm, split_column)
    _validate_splits(fm, split_column)
    results["feature_matrix"] = fm

    features, all_feature_names = _build_multimodal_feature_table(results)
    age = fm["age"].astype(float).to_numpy()
    split = fm[split_column].astype(str)
    train_mask = split.eq("train").to_numpy()
    val_mask = split.eq("val").to_numpy()
    test_mask = split.eq("test").to_numpy()
    trainval_mask = train_mask | val_mask

    print(f"\n{'=' * 72}")
    print("7a. Multimodal All-Feature Aging Clock")
    print(f"{'=' * 72}")
    print(
        f"Candidate raw features: {features.shape[1]} "
        f"(train={train_mask.sum()}, val={val_mask.sum()}, test={test_mask.sum()})"
    )

    X = features.to_numpy(dtype=np.float64)

    # Model selection preprocessing is fit on train only.
    clip_quantiles = (0.5, 99.5) if clip_outliers else None
    X_select, keep_select, _, _ = _fit_preprocess(
        X, train_mask, clip_quantiles=clip_quantiles,
    )
    kept_select_names = [name for name, keep in zip(all_feature_names, keep_select) if keep]
    print(f"Kept after train-missingness filter: {len(kept_select_names)}")

    alphas = np.logspace(-2, 8, 61)
    selected_alpha, val_mae, val_r2, val_r = _select_ridge_alpha(
        X_select, age, train_mask, val_mask, alphas,
    )
    print(
        f"Validation-selected Ridge alpha={selected_alpha:.4g}; "
        f"validation MAE={val_mae:.2f}, R2={val_r2:.3f}, r={val_r:.3f}"
    )

    # Final preprocessing and model are fit on train+val only. Test is untouched.
    X_final, keep_final, _, _ = _fit_preprocess(
        X, trainval_mask, clip_quantiles=clip_quantiles,
    )
    kept_names = [name for name, keep in zip(all_feature_names, keep_final) if keep]
    final_model = Ridge(alpha=selected_alpha)
    final_model.fit(X_final[trainval_mask], age[trainval_mask])

    test_pred = final_model.predict(X_final[test_mask])
    test_mae, test_r2, test_r = _regression_metrics(test_pred, age[test_mask])
    print(f"Final test MAE={test_mae:.2f}, R2={test_r2:.3f}, r={test_r:.3f}")

    pred_all = final_model.predict(X_final)
    age_accel = _residualize_age_accel(pred_all, age, trainval_mask)

    multimodal_df = pd.DataFrame(index=fm.index)
    multimodal_df["age"] = age
    multimodal_df["multi_predicted_age"] = pred_all
    multimodal_df["multi_age_accel"] = age_accel
    variant = output_suffix
    if variant is None and split_column != "recommended_split":
        variant = split_column
    multimodal_path = result_variant_path("multimodal_clock_age_accel.parquet", variant)
    unified_path = result_variant_path("unified_age_accel.parquet", variant)
    importance_path = result_variant_path("multimodal_clock_feature_importance.csv", variant)
    multimodal_perf_path = result_variant_path("multimodal_clock_performance.csv", variant)
    unified_perf_path = result_variant_path("unified_clock_performance.csv", variant)
    multimodal_df.to_parquet(multimodal_path)

    unified_df = pd.DataFrame(index=fm.index)
    unified_df["unified_predicted_age"] = pred_all
    unified_df["unified_age_accel"] = age_accel
    unified_df.to_parquet(unified_path)

    importance = np.abs(final_model.coef_)
    importance_df = pd.DataFrame({
        "dimension": kept_names,
        "importance": importance,
    }).sort_values("importance", ascending=False)
    denom = importance_df["importance"].sum()
    importance_df["importance_pct"] = (
        100.0 * importance_df["importance"] / denom if denom > 0 else 0.0
    )
    importance_df.to_csv(importance_path, index=False)

    perf_df = pd.DataFrame([
        {
            "model": "Ridge validation-selected all-feature",
            "split_column": split_column,
            "clip_outliers": bool(clip_outliers),
            "n_candidate_features": len(all_feature_names),
            "n_features": len(kept_names),
            "n_train": int(train_mask.sum()),
            "n_val": int(val_mask.sum()),
            "n_test": int(test_mask.sum()),
            "selected_alpha": selected_alpha,
            "val_mae": round(val_mae, 3),
            "val_r_squared": round(val_r2, 4),
            "val_pearson_r": round(val_r, 4),
            "test_mae": round(test_mae, 3),
            "test_r_squared": round(test_r2, 4),
            "test_pearson_r": round(test_r, 4),
        }
    ])
    perf_df.to_csv(multimodal_perf_path, index=False)
    perf_df.to_csv(unified_perf_path, index=False)

    print(f"Saved: {multimodal_path}")
    print(f"Saved: {unified_path}")
    print(f"Saved: {multimodal_perf_path}")

    print("\nTop multimodal clock features:")
    for _, row in importance_df.head(20).iterrows():
        print(f"  {row['dimension']:55s} {row['importance_pct']:6.2f}%")

    comparison = _compare_age_measures(fm, unified_df, results)

    return {
        "unified_df": unified_df,
        "importance_df": importance_df,
        "best_model_name": "Ridge validation-selected all-feature",
        "best_test_mae": test_mae,
        "best_r2": test_r2,
        "best_r": test_r,
        "comparison": comparison,
        "feature_cols": kept_names,
        "accel_cols": [],
        "split_column": split_column,
        "clip_outliers": bool(clip_outliers),
    }


def _compare_age_measures(
    fm: pd.DataFrame, unified_df: pd.DataFrame, results: dict,
) -> dict:
    """Compare Unified AgeAccel vs KDM vs allostatic_load for study_group
    discrimination (healthy vs insulin-dependent, Mann-Whitney U AUC)."""
    comparison = {}

    measures = {}
    measures["Unified_AgeAccel"] = unified_df["unified_age_accel"]

    if "clinical_scores" in results:
        cs = _as_person_index(results["clinical_scores"]).reindex(fm.index)
        if "kdm_age_accel" in cs.columns:
            measures["KDM_AgeAccel"] = cs["kdm_age_accel"]
        if "allostatic_load" in cs.columns:
            measures["Allostatic_Load"] = cs["allostatic_load"]
        if "frailty_index" in cs.columns:
            measures["Frailty_Index"] = cs["frailty_index"]

    # Binary comparison: healthy vs insulin-dependent
    sg = fm["study_group"]
    healthy_mask = sg == "healthy"
    insulin_mask = sg == "insulin_dependent"

    print("\nStudy group discrimination (healthy vs insulin-dependent):")
    for name, series in measures.items():
        valid = series.dropna()
        h_vals = valid.loc[valid.index.intersection(sg[healthy_mask].index)]
        i_vals = valid.loc[valid.index.intersection(sg[insulin_mask].index)]

        if len(h_vals) < 10 or len(i_vals) < 10:
            print(f"  {name}: insufficient data")
            continue

        # Effect size (Cohen's d)
        pooled_std = np.sqrt(
            ((len(h_vals) - 1) * h_vals.std()**2 + (len(i_vals) - 1) * i_vals.std()**2)
            / (len(h_vals) + len(i_vals) - 2)
        )
        cohens_d = (i_vals.mean() - h_vals.mean()) / pooled_std if pooled_std > 0 else np.nan

        # AUC (treat insulin_dependent as positive)
        labels = np.concatenate([np.zeros(len(h_vals)), np.ones(len(i_vals))])
        scores = np.concatenate([h_vals.values, i_vals.values])
        valid_auc = np.isfinite(scores)
        if valid_auc.sum() > 10:
            auc = roc_auc_score(labels[valid_auc], scores[valid_auc])
        else:
            auc = np.nan

        comparison[name] = {
            "cohens_d": round(cohens_d, 3),
            "auc": round(auc, 4),
            "n_healthy": len(h_vals),
            "n_insulin": len(i_vals),
        }
        print(f"  {name:25s}: Cohen's d = {cohens_d:+.3f}, AUC = {auc:.4f}")

    return comparison


# ── 7b. Paper Figure Generation ──────────────────────────────────────────────

def generate_figures(results: dict, unified_results: dict | None = None):
    """Generate all paper-quality figures from available data."""
    _setup_plot_style()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 72}")
    print("7b. Paper Figure Generation")
    print(f"{'=' * 72}")

    fig_table1(results)
    fig_concordance(results)
    fig_subtypes(results)
    fig_gradient(results)
    fig_unified(results, unified_results)
    fig_radar(results)


def fig_table1(results: dict):
    """Table 1: Enhanced cohort demographics with aging scores."""
    if "table1" not in results:
        print("[fig_table1] table1_by_study_group.csv not found -- skipping.")
        return

    print("\nGenerating Table 1 (enhanced)...")
    t1 = results["table1"].copy()

    # Augment with clinical scores if available
    if "clinical_scores" in results and "feature_matrix" in results:
        fm = results["feature_matrix"]
        cs = results["clinical_scores"]
        score_cols = ["kdm_age_accel", "allostatic_load", "frailty_index"]
        available_scores = [c for c in score_cols if c in cs.columns]

        if available_scores:
            merged = fm[["study_group"]].join(cs[available_scores])
            extra_rows = []
            for score in available_scores:
                row = {"feature": score, "column": score}
                for sg, label in STUDY_GROUP_LABELS.items():
                    sg_data = merged.loc[merged["study_group"] == sg, score].dropna()
                    row[f"mean_{label}"] = round(sg_data.mean(), 3)
                    row[f"std_{label}"] = round(sg_data.std(), 3)
                    row[f"n_{label}"] = len(sg_data)
                extra_rows.append(row)

            extra_df = pd.DataFrame(extra_rows)
            # Keep only columns present in both
            shared_cols = [c for c in t1.columns if c in extra_df.columns]
            t1 = pd.concat([t1[shared_cols], extra_df[shared_cols]], ignore_index=True)

    out_path = FIGURES_DIR / "table1_enhanced.csv"
    t1.to_csv(out_path, index=False)
    print(f"  Saved: {out_path}")


def fig_concordance(results: dict):
    """Fig 2: Cross-organ AgeAccel correlation heatmap."""
    accel_df, accel_cols = _get_age_accel_columns(results)
    if accel_df.empty or len(accel_cols) < 2:
        print("[fig_concordance] Fewer than 2 AgeAccel dimensions -- skipping.")
        return

    print("\nGenerating Fig 2 (concordance heatmap)...")

    # Compute pairwise Pearson correlations
    corr = accel_df[accel_cols].corr(method="pearson")

    # Clean up column names for display
    display_names = [c.replace("_age_accel", "").replace("_", " ").title()
                     for c in accel_cols]
    corr.index = display_names
    corr.columns = display_names

    # Compute p-values for annotation
    n = len(accel_cols)
    pval_matrix = np.ones((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            valid = accel_df[[accel_cols[i], accel_cols[j]]].dropna()
            if len(valid) > 3:
                _, p = pearsonr(valid.iloc[:, 0], valid.iloc[:, 1])
                pval_matrix[i, j] = p
                pval_matrix[j, i] = p

    # Create annotation strings (* for p < 0.05, ** for p < 0.01, *** for p < 0.001)
    annot = np.empty_like(corr, dtype=object)
    for i in range(n):
        for j in range(n):
            r_val = corr.iloc[i, j]
            if i == j:
                annot[i, j] = ""
            else:
                stars = ""
                if pval_matrix[i, j] < 0.001:
                    stars = "***"
                elif pval_matrix[i, j] < 0.01:
                    stars = "**"
                elif pval_matrix[i, j] < 0.05:
                    stars = "*"
                annot[i, j] = f"{r_val:.2f}{stars}"

    fig, ax = plt.subplots(figsize=(max(8, n * 0.9), max(7, n * 0.8)))
    sns.heatmap(
        corr, annot=annot, fmt="", cmap="RdBu_r", center=0,
        vmin=-1, vmax=1, square=True, linewidths=0.5,
        cbar_kws={"label": "Pearson r", "shrink": 0.8},
        ax=ax,
    )
    ax.set_title("Cross-organ AgeAccel Concordance", fontsize=14, pad=12)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()

    out_path = FIGURES_DIR / "fig2_concordance.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def fig_subtypes(results: dict):
    """Fig 3: Aging subtypes UMAP colored by cluster and study group."""
    if "subtypes" not in results:
        print("[fig_subtypes] aging_subtypes.csv not found -- skipping.")
        return

    sub = results["subtypes"].copy()
    fm = results["feature_matrix"]

    # Normalize subtypes index to string person_id
    if "person_id" in sub.columns:
        sub["person_id"] = sub["person_id"].astype(str)
        sub = sub.set_index("person_id")
    elif sub.index.name != "person_id":
        sub.index = sub.index.astype(str)
        sub.index.name = "person_id"
    else:
        sub.index = sub.index.astype(str)

    # Need UMAP coordinates and cluster labels
    has_umap = "umap_1" in sub.columns and "umap_2" in sub.columns
    has_cluster = "cluster" in sub.columns or "subtype" in sub.columns

    if not (has_umap and has_cluster):
        # Try to recompute embedding from AgeAccel if available
        accel_df, accel_cols = _get_age_accel_columns(results)
        if accel_df.empty:
            print("[fig_subtypes] No UMAP coordinates or AgeAccel data -- skipping.")
            return

        print("\nGenerating Fig 3 (subtypes) from AgeAccel + cluster labels...")
        try:
            from sklearn.decomposition import PCA
            from sklearn.manifold import TSNE

            cluster_col = "cluster" if "cluster" in sub.columns else "subtype"

            common_idx = accel_df.index.intersection(sub.index).intersection(fm.index)
            X = accel_df.loc[common_idx, accel_cols].copy()

            # Impute and scale for dimensionality reduction
            imp = SimpleImputer(strategy="median")
            X_imp = imp.fit_transform(X)
            sc = StandardScaler()
            X_sc = sc.fit_transform(X_imp)

            # Use PCA + t-SNE (UMAP may not be installed)
            if X_sc.shape[1] > 2:
                pca = PCA(n_components=min(X_sc.shape[1], 10))
                X_pca = pca.fit_transform(X_sc)
            else:
                X_pca = X_sc

            tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(X_pca) - 1))
            coords = tsne.fit_transform(X_pca)

            clusters = sub.loc[common_idx, cluster_col].values
            study_groups = fm.loc[common_idx, "study_group"].values

            _plot_subtypes_panels(coords, clusters, study_groups)
        except Exception as e:
            print(f"  [fig_subtypes] Error computing embedding: {e}")
        return

    # If subtypes file has UMAP coords
    print("\nGenerating Fig 3 (subtypes) from pre-computed UMAP...")

    cluster_col = "cluster" if "cluster" in sub.columns else "subtype"
    common_idx = sub.index.intersection(fm.index)

    coords = sub.loc[common_idx, ["umap_1", "umap_2"]].values
    clusters = sub.loc[common_idx, cluster_col].values
    study_groups = fm.loc[common_idx, "study_group"].values

    _plot_subtypes_panels(coords, clusters, study_groups)


def _plot_subtypes_panels(coords, clusters, study_groups):
    """Create side-by-side panels: by cluster and by study group."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: colored by cluster
    unique_clusters = sorted(set(clusters))
    colors_cluster = [SUBTYPE_PALETTE[i % len(SUBTYPE_PALETTE)] for i in range(len(unique_clusters))]
    cluster_map = {c: i for i, c in enumerate(unique_clusters)}

    for cl in unique_clusters:
        mask = clusters == cl
        axes[0].scatter(
            coords[mask, 0], coords[mask, 1],
            c=[colors_cluster[cluster_map[cl]]], label=f"Cluster {cl}",
            s=10, alpha=0.6, edgecolors="none",
        )
    axes[0].set_title("Aging Subtypes (by Cluster)")
    axes[0].set_xlabel("Dimension 1")
    axes[0].set_ylabel("Dimension 2")
    axes[0].legend(markerscale=3, framealpha=0.8)

    # Right: colored by study group
    for i, sg in enumerate(STUDY_GROUP_ORDER):
        mask = study_groups == sg
        if mask.sum() == 0:
            continue
        axes[1].scatter(
            coords[mask, 0], coords[mask, 1],
            c=[SEVERITY_COLORS[i]], label=STUDY_GROUP_LABELS.get(sg, sg),
            s=10, alpha=0.6, edgecolors="none",
        )
    axes[1].set_title("Aging Subtypes (by Study Group)")
    axes[1].set_xlabel("Dimension 1")
    axes[1].set_ylabel("Dimension 2")
    axes[1].legend(markerscale=3, framealpha=0.8)

    plt.tight_layout()
    out_path = FIGURES_DIR / "fig3_subtypes.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def fig_gradient(results: dict):
    """Fig 4: Diabetes severity gradient per aging dimension (forest plot).

    For each aging dimension: effect size (healthy vs insulin-dependent)
    as a horizontal forest plot with 95% CI, sorted by effect size.
    """
    # Try to use AgeAccel columns first
    accel_df, accel_cols = _get_age_accel_columns(results)
    fm = results["feature_matrix"]

    # Collect effect sizes from either AgeAccel or pairwise_effect_sizes.csv
    records = []

    if not accel_df.empty:
        sg = fm.loc[accel_df.index, "study_group"]
        healthy_idx = sg[sg == "healthy"].index
        insulin_idx = sg[sg == "insulin_dependent"].index

        for col in accel_cols:
            h = accel_df.loc[healthy_idx, col].dropna()
            ins = accel_df.loc[insulin_idx, col].dropna()
            if len(h) < 10 or len(ins) < 10:
                continue

            mean_diff = ins.mean() - h.mean()
            pooled_std = np.sqrt(
                ((len(h) - 1) * h.std()**2 + (len(ins) - 1) * ins.std()**2)
                / (len(h) + len(ins) - 2)
            )
            d = mean_diff / pooled_std if pooled_std > 0 else 0
            # SE of Cohen's d
            se = np.sqrt((len(h) + len(ins)) / (len(h) * len(ins))
                         + d**2 / (2 * (len(h) + len(ins))))
            ci_low = d - 1.96 * se
            ci_high = d + 1.96 * se
            label = col.replace("_age_accel", "").replace("_", " ").title()
            records.append({
                "dimension": label, "effect_size": d,
                "ci_low": ci_low, "ci_high": ci_high,
            })

    # Also include pairwise effect sizes from Phase 1 if available
    if "pairwise_effect" in results and not records:
        pe = results["pairwise_effect"]
        for _, row in pe.iterrows():
            d = row.get("healthy_vs_insulin_d", 0)
            # Approximate CI since we don't have n per group here
            se = abs(d) * 0.15  # rough approximation
            records.append({
                "dimension": row["feature"].replace("_", " ").title(),
                "effect_size": d, "ci_low": d - 1.96 * se, "ci_high": d + 1.96 * se,
            })

    if not records:
        print("[fig_gradient] No effect size data available -- skipping.")
        return

    print("\nGenerating Fig 4 (severity gradient forest plot)...")
    df_eff = pd.DataFrame(records).sort_values("effect_size")

    fig, ax = plt.subplots(figsize=(8, max(4, len(df_eff) * 0.45)))

    y_pos = range(len(df_eff))
    ax.barh(
        y_pos, df_eff["effect_size"].values,
        xerr=[
            df_eff["effect_size"].values - df_eff["ci_low"].values,
            df_eff["ci_high"].values - df_eff["effect_size"].values,
        ],
        color=[
            "#d73027" if d > 0 else "#4575b4"
            for d in df_eff["effect_size"].values
        ],
        alpha=0.8, height=0.6, capsize=3, ecolor="gray",
    )
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(df_eff["dimension"].values)
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Cohen's d (Healthy vs Insulin-dependent)")
    ax.set_title("Diabetes Severity Gradient per Aging Dimension")

    plt.tight_layout()
    out_path = FIGURES_DIR / "fig4_gradient.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def fig_unified(results: dict, unified_results: dict | None = None):
    """Fig 5: Unified clock feature importance + comparison.

    Left: bar chart of feature importance in unified clock.
    Right: comparison of Unified AgeAccel vs KDM vs allostatic_load (AUC bars).
    """
    if unified_results is None or not unified_results:
        print("[fig_unified] No unified clock results -- skipping.")
        return

    importance_df = unified_results.get("importance_df")
    comparison = unified_results.get("comparison", {})

    if importance_df is None or importance_df.empty:
        print("[fig_unified] No importance data -- skipping.")
        return

    print("\nGenerating Fig 5 (unified clock summary)...")

    imp = importance_df.head(25).sort_values("importance_pct", ascending=True)
    has_comparison = len(comparison) > 1
    ncols = 2 if has_comparison else 1
    fig_height = max(5, min(10, len(imp) * 0.34))
    fig, axes = plt.subplots(1, ncols, figsize=(6 * ncols, fig_height))
    if ncols == 1:
        axes = [axes]

    # Left: feature importance
    labels = [d.replace("_age_accel", "").replace("_", " ").title()
              for d in imp["dimension"]]
    colors = plt.cm.Blues(np.linspace(0.3, 0.9, len(imp)))

    axes[0].barh(range(len(imp)), imp["importance_pct"].values, color=colors, height=0.7)
    axes[0].set_yticks(range(len(imp)))
    axes[0].set_yticklabels(labels)
    axes[0].set_xlabel("Relative Importance (%)")
    axes[0].set_title(f"Unified Clock ({unified_results.get('best_model_name', '')})")

    # Right: comparison AUC
    if has_comparison:
        names = list(comparison.keys())
        aucs = [comparison[n].get("auc", 0) for n in names]
        ds = [comparison[n].get("cohens_d", 0) for n in names]

        x = range(len(names))
        bar_colors = ["#2171b5" if n == "Unified_AgeAccel" else "#6baed6" for n in names]
        axes[1].bar(x, aucs, color=bar_colors, width=0.6, alpha=0.9)
        axes[1].set_xticks(list(x))
        axes[1].set_xticklabels(
            [n.replace("_", "\n") for n in names], fontsize=9,
        )
        axes[1].set_ylabel("AUC (Healthy vs Insulin-dependent)")
        axes[1].set_title("Study Group Discrimination")
        axes[1].set_ylim(0.5, 1.0)

        # Add Cohen's d annotation above bars
        for xi, (auc_val, d_val) in enumerate(zip(aucs, ds)):
            axes[1].text(xi, auc_val + 0.01, f"d={d_val:+.2f}",
                         ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    out_path = FIGURES_DIR / "fig5_unified.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def fig_radar(results: dict):
    """Fig 6: Radar plots showing aging profiles for each subtype.

    One radar per cluster, showing mean AgeAccel per dimension.
    """
    if "subtypes" not in results:
        print("[fig_radar] aging_subtypes.csv not found -- skipping.")
        return

    accel_df, accel_cols = _get_age_accel_columns(results)
    if accel_df.empty:
        print("[fig_radar] No AgeAccel data -- skipping.")
        return

    sub = results["subtypes"].copy()
    # Normalize subtypes index to string person_id
    if "person_id" in sub.columns:
        sub["person_id"] = sub["person_id"].astype(str)
        sub = sub.set_index("person_id")
    elif sub.index.name != "person_id":
        sub.index = sub.index.astype(str)
        sub.index.name = "person_id"
    else:
        sub.index = sub.index.astype(str)

    cluster_col = "cluster" if "cluster" in sub.columns else "subtype"
    if cluster_col not in sub.columns:
        print(f"[fig_radar] No '{cluster_col}' column in subtypes -- skipping.")
        return

    common_idx = accel_df.index.intersection(sub.index)
    if len(common_idx) < 10:
        print("[fig_radar] Insufficient overlapping data -- skipping.")
        return

    print("\nGenerating Fig 6 (radar plots per subtype)...")

    merged = accel_df.loc[common_idx, accel_cols].copy()
    merged["cluster"] = sub.loc[common_idx, cluster_col]

    # Standardize each AgeAccel for comparability
    for col in accel_cols:
        vals = merged[col]
        merged[col] = (vals - vals.mean()) / (vals.std() + 1e-8)

    unique_clusters = sorted(merged["cluster"].unique())
    n_clusters = len(unique_clusters)

    if n_clusters == 0:
        print("[fig_radar] No clusters found -- skipping.")
        return

    # Radar chart
    categories = [c.replace("_age_accel", "").replace("_", " ").title()
                  for c in accel_cols]
    n_cats = len(categories)
    angles = np.linspace(0, 2 * np.pi, n_cats, endpoint=False).tolist()
    angles += angles[:1]  # close the polygon

    ncols_radar = min(n_clusters, 3)
    nrows_radar = (n_clusters + ncols_radar - 1) // ncols_radar
    fig, axes = plt.subplots(
        nrows_radar, ncols_radar,
        figsize=(5 * ncols_radar, 5 * nrows_radar),
        subplot_kw={"projection": "polar"},
    )
    if n_clusters == 1:
        axes = np.array([[axes]])
    axes = np.atleast_2d(axes)

    for idx, cl in enumerate(unique_clusters):
        row, col = divmod(idx, ncols_radar)
        ax = axes[row, col]

        cl_data = merged[merged["cluster"] == cl][accel_cols]
        means = cl_data.mean().values.tolist()
        means += means[:1]

        color = SUBTYPE_PALETTE[idx % len(SUBTYPE_PALETTE)]
        ax.plot(angles, means, "o-", color=color, linewidth=2, markersize=4)
        ax.fill(angles, means, alpha=0.25, color=color)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=7)
        ax.set_title(f"Cluster {cl} (n={len(cl_data)})", pad=15, fontsize=11)

    # Hide empty subplots
    for idx in range(n_clusters, nrows_radar * ncols_radar):
        row, col = divmod(idx, ncols_radar)
        axes[row, col].set_visible(False)

    plt.suptitle("Aging Profiles by Subtype (Standardized AgeAccel)", fontsize=14, y=1.02)
    plt.tight_layout()
    out_path = FIGURES_DIR / "fig6_radar.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


# ── 7c. Summary Report ──────────────────────────────────────────────────────

def summary_report(results: dict, unified_results: dict | None = None):
    """Generate comprehensive summary of all findings."""
    print(f"\n{'=' * 72}")
    print("7c. Summary Report")
    print(f"{'=' * 72}")

    report = {}

    # 1. Per-clock performance
    if "clock_performance" in results:
        cp = results["clock_performance"]
        report["per_clock_performance"] = cp.to_dict(orient="records")
        best_clock = cp.loc[cp["mae"].idxmin()]
        report["best_clock"] = {
            "name": best_clock["clock_name"],
            "mae": float(best_clock["mae"]),
            "r_squared": float(best_clock["r_squared"]),
        }
        print(f"\nBest individual clock: {best_clock['clock_name']} "
              f"(MAE={best_clock['mae']:.2f}, R2={best_clock['r_squared']:.3f})")

    # 2. Concordance summary
    accel_df, accel_cols = _get_age_accel_columns(results)
    if not accel_df.empty and len(accel_cols) >= 2:
        corr = accel_df[accel_cols].corr(method="pearson")
        # Extract upper triangle correlations
        pairs = []
        for i in range(len(accel_cols)):
            for j in range(i + 1, len(accel_cols)):
                pairs.append({
                    "dim_a": accel_cols[i].replace("_age_accel", ""),
                    "dim_b": accel_cols[j].replace("_age_accel", ""),
                    "pearson_r": round(corr.iloc[i, j], 4),
                })
        pairs_sorted = sorted(pairs, key=lambda x: abs(x["pearson_r"]), reverse=True)
        report["concordance"] = {
            "most_correlated": pairs_sorted[:3] if pairs_sorted else [],
            "least_correlated": pairs_sorted[-3:] if len(pairs_sorted) >= 3 else pairs_sorted,
        }
        if pairs_sorted:
            print(f"\nMost correlated aging pair: "
                  f"{pairs_sorted[0]['dim_a']} <-> {pairs_sorted[0]['dim_b']} "
                  f"(r={pairs_sorted[0]['pearson_r']:.3f})")
            print(f"Least correlated aging pair: "
                  f"{pairs_sorted[-1]['dim_a']} <-> {pairs_sorted[-1]['dim_b']} "
                  f"(r={pairs_sorted[-1]['pearson_r']:.3f})")

    # 3. Subtypes summary
    if "subtypes" in results:
        sub = results["subtypes"]
        cluster_col = "cluster" if "cluster" in sub.columns else "subtype"
        if cluster_col in sub.columns:
            counts = sub[cluster_col].value_counts().to_dict()
            report["subtypes"] = {
                "n_clusters": len(counts),
                "cluster_sizes": {str(k): int(v) for k, v in counts.items()},
            }
            print(f"\nAging subtypes: {len(counts)} clusters, "
                  f"sizes = {dict(counts)}")

    # 4. Gradient summary (from pairwise effects)
    if "pairwise_effect" in results:
        pe = results["pairwise_effect"]
        if "healthy_vs_insulin_d" in pe.columns:
            steepest = pe.loc[pe["healthy_vs_insulin_d"].abs().idxmax()]
            flattest = pe.loc[pe["healthy_vs_insulin_d"].abs().idxmin()]
            report["gradient"] = {
                "steepest_dimension": steepest["feature"],
                "steepest_d": float(steepest["healthy_vs_insulin_d"]),
                "flattest_dimension": flattest["feature"],
                "flattest_d": float(flattest["healthy_vs_insulin_d"]),
            }
            print(f"\nSteepest gradient: {steepest['feature']} "
                  f"(d={steepest['healthy_vs_insulin_d']:.3f})")
            print(f"Flattest gradient: {flattest['feature']} "
                  f"(d={flattest['healthy_vs_insulin_d']:.3f})")

    # 5. Unified clock summary
    if unified_results and unified_results.get("best_test_mae") is not None:
        report["unified_clock"] = {
            "best_model": unified_results["best_model_name"],
            "test_mae": round(unified_results["best_test_mae"], 3),
            "test_r2": round(unified_results["best_r2"], 4),
            "test_pearson_r": round(unified_results["best_r"], 4),
            "n_features": len(unified_results.get("feature_cols", [])),
            "comparison": unified_results.get("comparison", {}),
        }
        print(f"\nUnified clock: {unified_results['best_model_name']}, "
              f"MAE={unified_results['best_test_mae']:.2f}, "
              f"R2={unified_results['best_r2']:.3f}")

        # Improvement over individual clocks
        if "clock_performance" in results:
            cp = results["clock_performance"]
            best_individual_mae = cp["mae"].min()
            improvement = best_individual_mae - unified_results["best_test_mae"]
            report["unified_clock"]["improvement_mae_vs_best_individual"] = round(improvement, 3)
            print(f"  Improvement over best individual clock: "
                  f"{improvement:+.2f} MAE")

    # 6. Cohort overview
    fm = results["feature_matrix"]
    report["cohort"] = {
        "n_total": len(fm),
        "study_groups": fm["study_group"].value_counts().to_dict(),
        "splits": fm["recommended_split"].value_counts().to_dict(),
        "age_range": [int(fm["age"].min()), int(fm["age"].max())],
        "mean_age": round(fm["age"].mean(), 1),
    }

    # Save
    out_path = result_path("study_summary.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Train the all-feature multimodal aging clock")
    parser.add_argument("--split-column", default="recommended_split",
                        help="Split column to use, e.g. recommended_split or balanced_split_v1")
    parser.add_argument("--output-suffix", default=None,
                        help="Optional artifact suffix. Defaults to split column for non-recommended splits.")
    parser.add_argument("--clip-outliers", action="store_true",
                        help="Winsorize feature values using train-only quantiles before imputation/scaling.")
    parser.add_argument("--write-reports", action="store_true",
                        help="Generate figures and study_summary.json for non-recommended split runs.")
    args = parser.parse_args()

    results = load_all_results()

    # Build the all-feature multimodal clock without using AgeAccel residuals
    # as predictors.
    unified_results = unified_clock(
        results,
        split_column=args.split_column,
        output_suffix=args.output_suffix,
        clip_outliers=args.clip_outliers,
    )

    write_reports = (
        args.write_reports
        or (
            args.split_column == "recommended_split"
            and args.output_suffix is None
            and not args.clip_outliers
        )
    )
    if write_reports:
        # Generate whatever figures we can from available data
        generate_figures(results, unified_results)

        # Summary report
        summary_report(results, unified_results)
    else:
        print("\nSkipping figure/report regeneration for non-default split run. "
              "Use --write-reports to force it.")

    print(f"\n{'=' * 72}")
    print("Phase 7 complete.")
    print(f"{'=' * 72}")


if __name__ == "__main__":
    main()
