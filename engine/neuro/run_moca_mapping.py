"""Map AI-READI retinal and physiology modalities to MoCA cognition.

This is a first-pass, leakage-guarded model ladder for the project question:
do non-invasive AI-READI modalities carry signal related to cognitive function?

Usage:
    python -m neuro_moca_mapping.run_moca_mapping
"""

from __future__ import annotations

import argparse
import json
import os
import warnings
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-codex")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegressionCV, RidgeCV
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    mean_absolute_error,
    r2_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from scripts.config import RESULTS_DIR, result_path


MOCA_TOTAL = "moca_total"
MOCA_LOW_TARGET = "moca_low_lt26"
SPLIT_LABELS = ("train", "val", "test")

SELECTED_DOMAIN_TARGETS = [
    "moca_delayed_recall",
    "moca_trails",
    "moca_clock",
    "moca_digitspan",
    "moca_fluency",
    "moca_orientation",
]

LAB_AND_VITAL_COLS = [
    "ag_ratio",
    "albumin",
    "alk_phos",
    "alt",
    "ast",
    "bilirubin_total",
    "bun",
    "bun_cr_ratio",
    "c_peptide",
    "calcium",
    "chloride",
    "co2",
    "creatinine",
    "crp",
    "globulin",
    "glucose",
    "hba1c",
    "hdl",
    "hematocrit",
    "hemoglobin",
    "insulin",
    "ldl",
    "mch",
    "mchc",
    "mcv",
    "nt_probnp",
    "platelets",
    "potassium",
    "rbc",
    "rdw",
    "sodium",
    "total_cholesterol",
    "total_protein",
    "triglycerides",
    "troponin_t",
    "urine_albumin",
    "urine_creatinine",
    "wbc",
    "dbp",
    "heart_rate",
    "sbp",
    "bmi",
    "height_cm",
    "hip_cm",
    "waist_cm",
    "weight_kg",
    "whr",
    "ever_smoked",
    "ever_alcohol",
]

CLINICAL_SCORE_COLS = [
    "homa_ir",
    "tyg_index",
    "quicki",
    "pulse_pressure",
    "uacr",
]


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    numeric: tuple[str, ...]
    categorical: tuple[str, ...] = ()
    required_groups: tuple[tuple[str, ...], ...] = ()
    cohort: str = "all_moca"
    description: str = ""


def read_parquet_indexed(path: Path) -> pd.DataFrame:
    """Read a parquet table and normalize person_id indexing."""
    df = pd.read_parquet(path)
    if "person_id" in df.columns:
        df = df.set_index("person_id")
    df.index = df.index.astype(str)
    df.index.name = "person_id"
    return df


def load_analysis_frame(split_column: str) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Load and join the derived AI-READI feature tables used in this analysis."""
    feature_matrix = read_parquet_indexed(result_path("feature_matrix.parquet"))
    clinical_scores = read_parquet_indexed(result_path("clinical_scores.parquet"))
    multimodal = read_parquet_indexed(result_path("multimodal_features.parquet"))
    coupling = read_parquet_indexed(result_path("coupling_features.parquet"))
    predictability = read_parquet_indexed(result_path("cross_modal_predictability.parquet"))
    retinal_embeddings = read_parquet_indexed(result_path("retinal_embeddings.parquet"))
    retinal_age = read_parquet_indexed(result_path("retinal_age_accel.parquet"))

    df = feature_matrix.copy()

    split_path = result_path("split_assignments.parquet")
    if split_path.exists():
        splits = read_parquet_indexed(split_path)
        if split_column not in df.columns and split_column in splits.columns:
            df = df.join(splits[[split_column]], how="left")

    df = df.join(clinical_scores, how="left", rsuffix="_clinical_score")
    df = df.join(multimodal, how="left", rsuffix="_multimodal")
    df = df.join(coupling, how="left", rsuffix="_coupling")

    keep_predictability = [
        c for c in predictability.columns
        if not c.endswith("_n_train") and not c.endswith("_n_test")
    ]
    df = df.join(predictability[keep_predictability], how="left", rsuffix="_predictability")
    df = df.join(retinal_embeddings, how="left")

    retinal_age_keep = [c for c in ["retinal_age_accel"] if c in retinal_age.columns]
    df = df.join(retinal_age[retinal_age_keep], how="left")

    if MOCA_TOTAL not in df.columns:
        raise KeyError(f"Missing required target column: {MOCA_TOTAL}")
    if split_column not in df.columns:
        raise KeyError(f"Missing split column: {split_column}")

    column_groups = {
        "retinal_embeddings": [c for c in retinal_embeddings.columns if c in df.columns],
        "retinal_agegap": [c for c in retinal_age_keep if c in df.columns],
        "multimodal": [c for c in multimodal.columns if c in df.columns],
        "coupling": [c for c in coupling.columns if c in df.columns],
        "predictability": [c for c in keep_predictability if c in df.columns],
    }
    return df, column_groups


def leakage_columns(df: pd.DataFrame) -> set[str]:
    """Columns that cannot be used to predict MoCA."""
    leaked = {c for c in df.columns if c.startswith("moca_")}
    leaked.update({
        "cognitive_predicted_age",
        "cognitive_age_accel",
        MOCA_LOW_TARGET,
    })
    return leaked


def unique_existing(cols: list[str] | tuple[str, ...], df: pd.DataFrame, leaked: set[str]) -> tuple[str, ...]:
    """Return de-duplicated columns present in df and not target-leakage fields."""
    out: list[str] = []
    seen: set[str] = set()
    for col in cols:
        if col in seen or col in leaked or col not in df.columns:
            continue
        out.append(col)
        seen.add(col)
    return tuple(out)


def build_feature_specs(df: pd.DataFrame, groups: dict[str, list[str]]) -> list[FeatureSpec]:
    """Define the model ladder."""
    leaked = leakage_columns(df)
    demo_num = unique_existing(["age"], df, leaked)
    demo_cat = unique_existing(["clinical_site", "study_group"], df, leaked)
    clinical_num = unique_existing(LAB_AND_VITAL_COLS + CLINICAL_SCORE_COLS, df, leaked)
    retina_emb = unique_existing(groups["retinal_embeddings"], df, leaked)
    retina_age = unique_existing(groups["retinal_agegap"], df, leaked)
    physio = unique_existing(
        groups["multimodal"] + groups["coupling"] + groups["predictability"],
        df,
        leaked,
    )

    demo_plus_clinical = demo_num + clinical_num
    full_numeric = demo_plus_clinical + retina_emb + retina_age + physio

    return [
        FeatureSpec(
            name="demographics",
            numeric=demo_num,
            categorical=demo_cat,
            cohort="all_moca",
            description="Age, clinical site, and AI-READI study group.",
        ),
        FeatureSpec(
            name="clinical_metabolic",
            numeric=demo_plus_clinical,
            categorical=demo_cat,
            cohort="all_moca",
            description="Demographics plus labs, vitals, anthropometrics, and metabolic scores.",
        ),
        FeatureSpec(
            name="retina_image",
            numeric=retina_emb,
            required_groups=(retina_emb,),
            cohort="retina_image_available",
            description="RETFound retinal fundus image embeddings only.",
        ),
        FeatureSpec(
            name="retina_agegap",
            numeric=retina_age,
            required_groups=(retina_age,),
            cohort="retina_agegap_available",
            description="Retinal age acceleration only.",
        ),
        FeatureSpec(
            name="clinical_on_retina_cohort",
            numeric=demo_plus_clinical,
            categorical=demo_cat,
            required_groups=(retina_emb,),
            cohort="retina_image_available",
            description="Clinical/metabolic baseline refit on the retinal embedding cohort.",
        ),
        FeatureSpec(
            name="clinical_plus_retina_image",
            numeric=demo_plus_clinical + retina_emb,
            categorical=demo_cat,
            required_groups=(retina_emb,),
            cohort="retina_image_available",
            description="Clinical/metabolic predictors plus RETFound embeddings.",
        ),
        FeatureSpec(
            name="clinical_on_retina_agegap_cohort",
            numeric=demo_plus_clinical,
            categorical=demo_cat,
            required_groups=(retina_age,),
            cohort="retina_agegap_available",
            description="Clinical/metabolic baseline refit on the retinal age-gap cohort.",
        ),
        FeatureSpec(
            name="clinical_plus_retina_agegap",
            numeric=demo_plus_clinical + retina_age,
            categorical=demo_cat,
            required_groups=(retina_age,),
            cohort="retina_agegap_available",
            description="Clinical/metabolic predictors plus retinal age acceleration.",
        ),
        FeatureSpec(
            name="physiology",
            numeric=physio,
            required_groups=(physio,),
            cohort="physiology_available",
            description="CGM, ECG, wearable, environment, and coupling features only.",
        ),
        FeatureSpec(
            name="clinical_on_physiology_cohort",
            numeric=demo_plus_clinical,
            categorical=demo_cat,
            required_groups=(physio,),
            cohort="physiology_available",
            description="Clinical/metabolic baseline refit on the physiology cohort.",
        ),
        FeatureSpec(
            name="clinical_plus_physiology",
            numeric=demo_plus_clinical + physio,
            categorical=demo_cat,
            required_groups=(physio,),
            cohort="physiology_available",
            description="Clinical/metabolic predictors plus CGM/wearable/ECG/coupling features.",
        ),
        FeatureSpec(
            name="clinical_on_full_cohort",
            numeric=demo_plus_clinical,
            categorical=demo_cat,
            required_groups=(retina_emb, physio),
            cohort="retina_and_physiology_available",
            description="Clinical/metabolic baseline refit on the full multimodal cohort.",
        ),
        FeatureSpec(
            name="full_multimodal",
            numeric=full_numeric,
            categorical=demo_cat,
            required_groups=(retina_emb, physio),
            cohort="retina_and_physiology_available",
            description="Clinical/metabolic, retinal image, retinal age-gap, and physiology features.",
        ),
    ]


def make_one_hot_encoder() -> OneHotEncoder:
    """Construct a dense one-hot encoder across sklearn versions."""
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def make_preprocessor(numeric_cols: list[str], categorical_cols: list[str]) -> ColumnTransformer:
    transformers = []
    if numeric_cols:
        transformers.append((
            "num",
            Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]),
            numeric_cols,
        ))
    if categorical_cols:
        transformers.append((
            "cat",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", make_one_hot_encoder()),
            ]),
            categorical_cols,
        ))
    if not transformers:
        raise ValueError("No predictors available after leakage and missingness filtering.")
    return ColumnTransformer(transformers, remainder="drop", verbose_feature_names_out=False)


def required_mask(df: pd.DataFrame, spec: FeatureSpec) -> pd.Series:
    """Require at least one observed feature from each required modality group."""
    mask = pd.Series(True, index=df.index)
    for group in spec.required_groups:
        available = [c for c in group if c in df.columns]
        if not available:
            return pd.Series(False, index=df.index)
        mask &= df[available].notna().any(axis=1)
    return mask


def target_mask(df: pd.DataFrame, target: str, split_column: str, spec: FeatureSpec) -> pd.Series:
    mask = df[target].notna()
    mask &= df[split_column].isin(SPLIT_LABELS)
    mask &= required_mask(df, spec)
    return mask


def prepare_features(
    df: pd.DataFrame,
    spec: FeatureSpec,
    mask: pd.Series,
    split_column: str,
    max_missing_frac: float,
) -> tuple[pd.DataFrame, list[str], list[str], list[str]]:
    """Prepare feature matrix and drop highly missing training columns."""
    train_mask = mask & df[split_column].eq("train")
    dropped: list[str] = []

    numeric = [c for c in spec.numeric if c in df.columns]
    categorical = [c for c in spec.categorical if c in df.columns]

    kept_numeric: list[str] = []
    for col in numeric:
        train_values = pd.to_numeric(df.loc[train_mask, col], errors="coerce")
        missing_frac = (~np.isfinite(train_values.to_numpy(dtype=float))).mean()
        if missing_frac <= max_missing_frac:
            kept_numeric.append(col)
        else:
            dropped.append(col)

    kept_categorical: list[str] = []
    for col in categorical:
        if df.loc[train_mask, col].notna().any():
            kept_categorical.append(col)
        else:
            dropped.append(col)

    cols = kept_numeric + kept_categorical
    if not cols:
        raise ValueError(f"{spec.name}: no predictors left after missingness filtering.")

    X = df.loc[mask, cols].copy()
    for col in kept_numeric:
        X[col] = pd.to_numeric(X[col], errors="coerce")
        X[col] = X[col].replace([np.inf, -np.inf], np.nan)
    for col in kept_categorical:
        X[col] = X[col].astype("string")
    return X, kept_numeric, kept_categorical, dropped


def safe_pearson(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2 or np.nanstd(y_true) == 0 or np.nanstd(y_pred) == 0:
        return float("nan")
    return float(pearsonr(y_true, y_pred).statistic)


def safe_spearman(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2 or np.nanstd(y_true) == 0 or np.nanstd(y_pred) == 0:
        return float("nan")
    return float(spearmanr(y_true, y_pred).statistic)


def evaluate_regression(
    estimator: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    splits: pd.Series,
    spec: FeatureSpec,
    target: str,
    n_features: int,
    n_features_dropped: int,
    prediction_bounds: tuple[float, float],
) -> list[dict]:
    rows = []
    for split_label in SPLIT_LABELS:
        split_mask = splits.eq(split_label).to_numpy()
        if split_mask.sum() == 0:
            continue
        y_true = y.to_numpy(dtype=float)[split_mask]
        y_pred = estimator.predict(X.loc[split_mask])
        y_pred = np.clip(y_pred, prediction_bounds[0], prediction_bounds[1])
        rows.append({
            "task": "regression",
            "target": target,
            "model_name": spec.name,
            "cohort": spec.cohort,
            "split": split_label,
            "n_eval": int(split_mask.sum()),
            "n_features": int(n_features),
            "n_features_dropped": int(n_features_dropped),
            "r2": float(r2_score(y_true, y_pred)) if len(y_true) >= 2 else float("nan"),
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "pearson_r": safe_pearson(y_true, y_pred),
            "spearman_r": safe_spearman(y_true, y_pred),
            "auroc": float("nan"),
            "auprc": float("nan"),
            "balanced_accuracy": float("nan"),
            "brier": float("nan"),
            "prevalence": float("nan"),
            "threshold": float("nan"),
        })
    return rows


def best_youden_threshold(y_true: np.ndarray, prob: np.ndarray) -> float:
    """Pick a deterministic train threshold maximizing balanced accuracy."""
    thresholds = np.unique(np.round(prob, 6))
    if len(thresholds) == 0:
        return 0.5
    best_threshold = 0.5
    best_score = -np.inf
    for threshold in thresholds:
        pred = (prob >= threshold).astype(int)
        score = balanced_accuracy_score(y_true, pred)
        if score > best_score:
            best_score = score
            best_threshold = float(threshold)
    return best_threshold


def safe_auc(y_true: np.ndarray, prob: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, prob))


def safe_auprc(y_true: np.ndarray, prob: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(average_precision_score(y_true, prob))


def evaluate_classification(
    estimator: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    splits: pd.Series,
    spec: FeatureSpec,
    target: str,
    n_features: int,
    n_features_dropped: int,
) -> list[dict]:
    train_mask = splits.eq("train").to_numpy()
    train_prob = estimator.predict_proba(X.loc[train_mask])[:, 1]
    threshold = best_youden_threshold(y.to_numpy(dtype=int)[train_mask], train_prob)

    rows = []
    for split_label in SPLIT_LABELS:
        split_mask = splits.eq(split_label).to_numpy()
        if split_mask.sum() == 0:
            continue
        y_true = y.to_numpy(dtype=int)[split_mask]
        prob = estimator.predict_proba(X.loc[split_mask])[:, 1]
        pred = (prob >= threshold).astype(int)
        rows.append({
            "task": "classification",
            "target": target,
            "model_name": spec.name,
            "cohort": spec.cohort,
            "split": split_label,
            "n_eval": int(split_mask.sum()),
            "n_features": int(n_features),
            "n_features_dropped": int(n_features_dropped),
            "r2": float("nan"),
            "mae": float("nan"),
            "pearson_r": float("nan"),
            "spearman_r": float("nan"),
            "auroc": safe_auc(y_true, prob),
            "auprc": safe_auprc(y_true, prob),
            "balanced_accuracy": float(balanced_accuracy_score(y_true, pred)),
            "brier": float(brier_score_loss(y_true, prob)),
            "prevalence": float(np.mean(y_true)),
            "threshold": threshold,
        })
    return rows


def fit_regression(
    df: pd.DataFrame,
    spec: FeatureSpec,
    target: str,
    split_column: str,
    max_missing_frac: float,
) -> tuple[list[dict], dict]:
    mask = target_mask(df, target, split_column, spec)
    X, numeric, categorical, dropped = prepare_features(df, spec, mask, split_column, max_missing_frac)
    y = df.loc[mask, target].astype(float)
    splits = df.loc[mask, split_column].astype(str)

    if splits.eq("train").sum() < 50:
        raise ValueError(f"{spec.name}/{target}: too few training rows.")

    preprocessor = make_preprocessor(numeric, categorical)
    model = RidgeCV(alphas=np.logspace(-2, 6, 17))
    estimator = Pipeline([("preprocess", preprocessor), ("model", model)])
    estimator.fit(X.loc[splits.eq("train")], y.loc[splits.eq("train")])

    if target == MOCA_TOTAL:
        prediction_bounds = (0.0, 30.0)
    else:
        y_train = y.loc[splits.eq("train")]
        prediction_bounds = (float(y_train.min()), float(y_train.max()))

    rows = evaluate_regression(
        estimator,
        X,
        y,
        splits,
        spec,
        target,
        len(numeric) + len(categorical),
        len(dropped),
        prediction_bounds,
    )
    meta = {
        "model_name": spec.name,
        "target": target,
        "task": "regression",
        "n_total": int(mask.sum()),
        "n_train": int(splits.eq("train").sum()),
        "n_val": int(splits.eq("val").sum()),
        "n_test": int(splits.eq("test").sum()),
        "n_numeric_features": len(numeric),
        "n_categorical_features": len(categorical),
        "n_features_dropped": len(dropped),
        "dropped_features": dropped,
        "prediction_bounds": prediction_bounds,
    }
    return rows, meta


def fit_classification(
    df: pd.DataFrame,
    spec: FeatureSpec,
    split_column: str,
    max_missing_frac: float,
) -> tuple[list[dict], dict]:
    mask = target_mask(df, MOCA_TOTAL, split_column, spec)
    X, numeric, categorical, dropped = prepare_features(df, spec, mask, split_column, max_missing_frac)
    y = (df.loc[mask, MOCA_TOTAL] < 26).astype(int)
    splits = df.loc[mask, split_column].astype(str)

    y_train = y.loc[splits.eq("train")]
    if splits.eq("train").sum() < 50 or y_train.nunique() < 2:
        raise ValueError(f"{spec.name}/{MOCA_LOW_TARGET}: insufficient training data or one class.")

    preprocessor = make_preprocessor(numeric, categorical)
    model = LogisticRegressionCV(
        Cs=np.logspace(-3, 3, 7),
        cv=3,
        penalty="l2",
        solver="lbfgs",
        scoring="roc_auc",
        class_weight="balanced",
        max_iter=3000,
        n_jobs=-1,
        refit=True,
    )
    estimator = Pipeline([("preprocess", preprocessor), ("model", model)])
    estimator.fit(X.loc[splits.eq("train")], y_train)

    rows = evaluate_classification(
        estimator,
        X,
        y,
        splits,
        spec,
        MOCA_LOW_TARGET,
        len(numeric) + len(categorical),
        len(dropped),
    )
    meta = {
        "model_name": spec.name,
        "target": MOCA_LOW_TARGET,
        "task": "classification",
        "n_total": int(mask.sum()),
        "n_train": int(splits.eq("train").sum()),
        "n_val": int(splits.eq("val").sum()),
        "n_test": int(splits.eq("test").sum()),
        "n_numeric_features": len(numeric),
        "n_categorical_features": len(categorical),
        "n_features_dropped": len(dropped),
        "dropped_features": dropped,
    }
    return rows, meta


def cohort_summary(df: pd.DataFrame, split_column: str) -> pd.DataFrame:
    rows = []
    eligible = df[MOCA_TOTAL].notna() & df[split_column].isin(SPLIT_LABELS)
    for split_label in ("all",) + SPLIT_LABELS:
        if split_label == "all":
            mask = eligible
        else:
            mask = eligible & df[split_column].eq(split_label)
        scores = df.loc[mask, MOCA_TOTAL].astype(float)
        rows.append({
            "split": split_label,
            "n": int(mask.sum()),
            "moca_total_mean": float(scores.mean()),
            "moca_total_sd": float(scores.std()),
            "moca_total_min": float(scores.min()),
            "moca_total_max": float(scores.max()),
            "n_moca_low_lt26": int((scores < 26).sum()),
            "prevalence_moca_low_lt26": float((scores < 26).mean()),
        })
    return pd.DataFrame(rows)


def feature_block_summary(specs: list[FeatureSpec]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "model_name": spec.name,
            "cohort": spec.cohort,
            "n_numeric_declared": len(spec.numeric),
            "n_categorical_declared": len(spec.categorical),
            "n_required_groups": len(spec.required_groups),
            "description": spec.description,
        }
        for spec in specs
    ])


def build_incremental_table(perf: pd.DataFrame) -> pd.DataFrame:
    contrasts = [
        ("retina_image_increment", "clinical_on_retina_cohort", "clinical_plus_retina_image"),
        ("retina_agegap_increment", "clinical_on_retina_agegap_cohort", "clinical_plus_retina_agegap"),
        ("physiology_increment", "clinical_on_physiology_cohort", "clinical_plus_physiology"),
        ("full_multimodal_increment", "clinical_on_full_cohort", "full_multimodal"),
    ]
    rows = []
    metrics = ["r2", "mae", "auroc", "auprc", "balanced_accuracy", "brier"]
    for contrast_name, baseline, augmented in contrasts:
        base = perf[perf["model_name"].eq(baseline)]
        aug = perf[perf["model_name"].eq(augmented)]
        merged = base.merge(
            aug,
            on=["task", "target", "split", "cohort"],
            suffixes=("_baseline", "_augmented"),
        )
        for _, row in merged.iterrows():
            out = {
                "contrast": contrast_name,
                "task": row["task"],
                "target": row["target"],
                "split": row["split"],
                "cohort": row["cohort"],
                "baseline_model": baseline,
                "augmented_model": augmented,
                "n_eval": int(row["n_eval_augmented"]),
            }
            for metric in metrics:
                out[f"{metric}_baseline"] = row[f"{metric}_baseline"]
                out[f"{metric}_augmented"] = row[f"{metric}_augmented"]
                out[f"delta_{metric}"] = row[f"{metric}_augmented"] - row[f"{metric}_baseline"]
            rows.append(out)
    return pd.DataFrame(rows)


def plot_main_performance(perf: pd.DataFrame, fig_dir: Path) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    main_order = [
        "demographics",
        "clinical_metabolic",
        "retina_image",
        "retina_agegap",
        "physiology",
        "clinical_plus_retina_image",
        "clinical_plus_physiology",
        "full_multimodal",
    ]

    reg = perf[
        perf["task"].eq("regression")
        & perf["target"].eq(MOCA_TOTAL)
        & perf["split"].eq("test")
        & perf["model_name"].isin(main_order)
    ].copy()
    reg["model_name"] = pd.Categorical(reg["model_name"], categories=main_order, ordered=True)
    reg = reg.sort_values("model_name")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(reg["model_name"].astype(str), reg["r2"], color="#3a6ea5")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Test R2")
    ax.set_title("MoCA Total Regression")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(fig_dir / "moca_total_test_r2.png", dpi=200)
    plt.close(fig)

    clf = perf[
        perf["task"].eq("classification")
        & perf["target"].eq(MOCA_LOW_TARGET)
        & perf["split"].eq("test")
        & perf["model_name"].isin(main_order)
    ].copy()
    clf["model_name"] = pd.Categorical(clf["model_name"], categories=main_order, ordered=True)
    clf = clf.sort_values("model_name")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(clf["model_name"].astype(str), clf["auroc"], color="#6b8e23")
    ax.axhline(0.5, color="black", linewidth=0.8, linestyle="--")
    ax.set_ylim(0.35, max(0.75, float(np.nanmax(clf["auroc"])) + 0.05))
    ax.set_ylabel("Test AUROC")
    ax.set_title("MoCA < 26 Classification")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(fig_dir / "moca_low_test_auroc.png", dpi=200)
    plt.close(fig)


def plot_incremental(incremental: pd.DataFrame, fig_dir: Path) -> None:
    test = incremental[incremental["split"].eq("test")].copy()
    reg = test[test["task"].eq("regression")]
    clf = test[test["task"].eq("classification")]

    if not reg.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.bar(reg["contrast"], reg["delta_r2"], color="#7a4e9f")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_ylabel("Delta test R2")
        ax.set_title("Incremental MoCA Total Performance")
        ax.tick_params(axis="x", rotation=30)
        fig.tight_layout()
        fig.savefig(fig_dir / "incremental_test_delta_r2.png", dpi=200)
        plt.close(fig)

    if not clf.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.bar(clf["contrast"], clf["delta_auroc"], color="#b05a32")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_ylabel("Delta test AUROC")
        ax.set_title("Incremental MoCA < 26 Performance")
        ax.tick_params(axis="x", rotation=30)
        fig.tight_layout()
        fig.savefig(fig_dir / "incremental_test_delta_auroc.png", dpi=200)
        plt.close(fig)


def plot_domain_heatmap(domain_perf: pd.DataFrame, fig_dir: Path) -> None:
    test = domain_perf[domain_perf["split"].eq("test")].copy()
    keep_models = [
        "clinical_metabolic",
        "clinical_plus_retina_image",
        "clinical_plus_physiology",
        "full_multimodal",
    ]
    test = test[test["model_name"].isin(keep_models)]
    if test.empty:
        return
    pivot = test.pivot_table(index="target", columns="model_name", values="r2")
    pivot = pivot.reindex(index=SELECTED_DOMAIN_TARGETS, columns=keep_models)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    data = pivot.to_numpy(dtype=float)
    vmax = max(0.05, float(np.nanmax(np.abs(data))) if np.isfinite(data).any() else 0.05)
    im = ax.imshow(data, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=35, ha="right")
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title("MoCA Domain Regression Test R2")
    fig.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    fig.tight_layout()
    fig.savefig(fig_dir / "moca_domain_test_r2_heatmap.png", dpi=200)
    plt.close(fig)


def save_summary_json(
    out_dir: Path,
    perf: pd.DataFrame,
    incremental: pd.DataFrame,
    cohort: pd.DataFrame,
    split_column: str,
) -> None:
    test_perf = perf[perf["split"].eq("test")]
    reg = test_perf[test_perf["task"].eq("regression")].sort_values("r2", ascending=False)
    clf = test_perf[test_perf["task"].eq("classification")].sort_values("auroc", ascending=False)
    test_increment = incremental[incremental["split"].eq("test")]

    summary = {
        "split_column": split_column,
        "target_definition": {
            "regression": MOCA_TOTAL,
            "classification": f"{MOCA_TOTAL} < 26",
        },
        "cohort_summary": cohort.to_dict(orient="records"),
        "best_test_regression_models": reg.head(5)[
            ["model_name", "cohort", "r2", "mae", "pearson_r", "n_eval"]
        ].to_dict(orient="records"),
        "best_test_classification_models": clf.head(5)[
            ["model_name", "cohort", "auroc", "auprc", "balanced_accuracy", "n_eval"]
        ].to_dict(orient="records"),
        "test_incremental_results": test_increment.to_dict(orient="records"),
        "leakage_guard": (
            "All moca_* columns, moca_low_lt26, cognitive_predicted_age, and "
            "cognitive_age_accel are excluded from predictors."
        ),
    }
    with (out_dir / "analysis_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)


def run(args: argparse.Namespace) -> None:
    out_dir = Path(args.output_dir)
    fig_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", message="An input array is constant")

    df, groups = load_analysis_frame(args.split_column)
    df[MOCA_LOW_TARGET] = np.where(df[MOCA_TOTAL].notna(), df[MOCA_TOTAL] < 26, np.nan)
    specs = build_feature_specs(df, groups)

    cohort = cohort_summary(df, args.split_column)
    cohort.to_csv(out_dir / "cohort_summary.csv", index=False)
    feature_block_summary(specs).to_csv(out_dir / "feature_blocks.csv", index=False)

    performance_rows: list[dict] = []
    model_meta_rows: list[dict] = []

    for spec in specs:
        print(f"[moca_total] {spec.name}")
        rows, meta = fit_regression(
            df,
            spec,
            MOCA_TOTAL,
            args.split_column,
            args.max_missing_frac,
        )
        performance_rows.extend(rows)
        model_meta_rows.append(meta)

        print(f"[moca_low_lt26] {spec.name}")
        rows, meta = fit_classification(
            df,
            spec,
            args.split_column,
            args.max_missing_frac,
        )
        performance_rows.extend(rows)
        model_meta_rows.append(meta)

    perf = pd.DataFrame(performance_rows)
    perf.to_csv(out_dir / "model_performance.csv", index=False)
    pd.DataFrame(model_meta_rows).to_csv(out_dir / "model_fit_metadata.csv", index=False)

    incremental = build_incremental_table(perf)
    incremental.to_csv(out_dir / "incremental_performance.csv", index=False)

    domain_rows: list[dict] = []
    domain_meta_rows: list[dict] = []
    if not args.skip_domains:
        domain_specs = [
            spec for spec in specs
            if spec.name in {
                "clinical_metabolic",
                "clinical_plus_retina_image",
                "clinical_plus_physiology",
                "full_multimodal",
            }
        ]
        for target in SELECTED_DOMAIN_TARGETS:
            if target not in df.columns:
                continue
            for spec in domain_specs:
                print(f"[{target}] {spec.name}")
                rows, meta = fit_regression(
                    df,
                    spec,
                    target,
                    args.split_column,
                    args.max_missing_frac,
                )
                domain_rows.extend(rows)
                domain_meta_rows.append(meta)

    domain_perf = pd.DataFrame(domain_rows)
    if not domain_perf.empty:
        domain_perf.to_csv(out_dir / "domain_performance.csv", index=False)
        pd.DataFrame(domain_meta_rows).to_csv(out_dir / "domain_fit_metadata.csv", index=False)

    plot_main_performance(perf, fig_dir)
    plot_incremental(incremental, fig_dir)
    if not domain_perf.empty:
        plot_domain_heatmap(domain_perf, fig_dir)
    save_summary_json(out_dir, perf, incremental, cohort, args.split_column)

    print(f"Wrote MoCA mapping results to {out_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split-column",
        default="recommended_split",
        help="Participant split column to use for train/val/test evaluation.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(RESULTS_DIR / "neuro_moca_mapping"),
        help="Directory for generated result tables and figures.",
    )
    parser.add_argument(
        "--max-missing-frac",
        type=float,
        default=0.50,
        help="Drop predictors with more than this missing fraction in the training split.",
    )
    parser.add_argument(
        "--skip-domains",
        action="store_true",
        help="Skip selected MoCA subdomain regression models.",
    )
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
