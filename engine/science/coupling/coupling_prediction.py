"""
Held-out prediction checks for dynamic coupling features.

This is intentionally lightweight: Ridge for continuous outcomes and logistic
regression for binary diabetes contrasts, using the repository's recommended
train/val/test split.

Outputs:
    results/coupling/coupling_prediction_performance.csv
    results/coupling/coupling_predictions.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    mean_absolute_error,
    roc_auc_score,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from scripts.config import RESULTS_DIR, result_path
from .coupling_atlas import GROUP_ORDER, _candidate_features


DEFAULT_INPUT = result_path("coupling_features.parquet")
DEFAULT_PERFORMANCE = result_path("coupling_prediction_performance.csv")
DEFAULT_PREDICTIONS = result_path("coupling_predictions.parquet")


def _read(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "person_id" in df.columns:
        df = df.set_index("person_id")
    df.index = df.index.astype(str)
    return df


def _load_data(input_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    coupling = _read(input_path)
    feature_matrix = _read(result_path("feature_matrix.parquet"))
    clinical_scores = _read(result_path("clinical_scores.parquet"))
    outcomes = feature_matrix.join(
        clinical_scores[[c for c in clinical_scores.columns if c not in feature_matrix.columns]],
        how="left",
    )
    df = coupling.join(outcomes, how="inner")
    return coupling, df


def _feature_sets(coupling: pd.DataFrame) -> dict[str, list[str]]:
    numeric = coupling.select_dtypes(include=[np.number]).columns.tolist()
    coverage_terms = ("_n", "n_aligned", "aligned_hours")
    summary_terms = ("_mean", "_sd", "steps_proxy", "sleep_fraction")
    coupling_only = _candidate_features(coupling)
    coupling_plus_summary = [
        c
        for c in numeric
        if c not in coverage_terms and not any(term in c for term in coverage_terms)
    ]
    interpretable_no_levels = [
        c
        for c in coupling_plus_summary
        if not any(term in c for term in summary_terms)
    ]
    return {
        "coupling_only": coupling_only,
        "interpretable_no_levels": interpretable_no_levels,
        "coupling_plus_summary": coupling_plus_summary,
    }


def _split_masks(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    split = df["recommended_split"].astype(str)
    train = split.isin(["train", "val"])
    test = split == "test"
    return train, test


def _continuous_model(df: pd.DataFrame, features: list[str], target: str, name: str) -> tuple[dict, pd.Series]:
    cols = features + [target, "recommended_split"]
    sub = df[cols].replace([np.inf, -np.inf], np.nan).dropna(subset=[target, "recommended_split"])
    train, test = _split_masks(sub)
    if train.sum() < 50 or test.sum() < 20:
        return {}, pd.Series(dtype=float)

    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", RidgeCV(alphas=np.logspace(-3, 3, 13))),
        ]
    )
    model.fit(sub.loc[train, features], sub.loc[train, target])
    pred = pd.Series(model.predict(sub.loc[test, features]), index=sub.index[test], name=f"{target}_{name}_pred")
    y = sub.loc[test, target]
    pearson = stats.pearsonr(y, pred).statistic if len(y) >= 3 and y.std() > 0 and pred.std() > 0 else np.nan
    row = {
        "feature_set": name,
        "outcome": target,
        "task": "continuous",
        "n_train": int(train.sum()),
        "n_test": int(test.sum()),
        "r2": float(r2_score(y, pred)),
        "mae": float(mean_absolute_error(y, pred)),
        "pearson_r": float(pearson),
        "auroc": np.nan,
        "average_precision": np.nan,
        "accuracy": np.nan,
    }
    return row, pred


def _binary_model(
    df: pd.DataFrame,
    features: list[str],
    label: pd.Series,
    outcome_name: str,
    feature_set_name: str,
) -> tuple[dict, pd.Series]:
    sub = df[features + ["recommended_split"]].copy()
    sub["label"] = label
    sub = sub.replace([np.inf, -np.inf], np.nan).dropna(subset=["label", "recommended_split"])
    train, test = _split_masks(sub)
    if train.sum() < 50 or test.sum() < 20 or sub.loc[train, "label"].nunique() < 2:
        return {}, pd.Series(dtype=float)

    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("logit", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )
    model.fit(sub.loc[train, features], sub.loc[train, "label"].astype(int))
    prob = pd.Series(
        model.predict_proba(sub.loc[test, features])[:, 1],
        index=sub.index[test],
        name=f"{outcome_name}_{feature_set_name}_prob",
    )
    y = sub.loc[test, "label"].astype(int)
    pred_label = (prob >= 0.5).astype(int)
    row = {
        "feature_set": feature_set_name,
        "outcome": outcome_name,
        "task": "binary",
        "n_train": int(train.sum()),
        "n_test": int(test.sum()),
        "r2": np.nan,
        "mae": np.nan,
        "pearson_r": np.nan,
        "auroc": float(roc_auc_score(y, prob)),
        "average_precision": float(average_precision_score(y, prob)),
        "accuracy": float(accuracy_score(y, pred_label)),
    }
    return row, prob


def run_prediction_checks(
    input_path: Path = DEFAULT_INPUT,
    performance_path: Path = DEFAULT_PERFORMANCE,
    predictions_path: Path = DEFAULT_PREDICTIONS,
) -> pd.DataFrame:
    coupling, df = _load_data(input_path)
    feature_sets = _feature_sets(coupling)
    rows = []
    predictions = pd.DataFrame(index=df.index)

    continuous_targets = [
        target
        for target in ["age", "hba1c", "frailty_index", "allostatic_load", "homeostatic_dysregulation"]
        if target in df.columns
    ]
    group_map = {group: i for i, group in enumerate(GROUP_ORDER)}
    if "study_group" in df.columns:
        df["study_group_ordinal"] = df["study_group"].map(group_map)
        continuous_targets.append("study_group_ordinal")

    for feature_set_name, features in feature_sets.items():
        features = [f for f in features if f in df.columns]
        for target in continuous_targets:
            row, pred = _continuous_model(df, features, target, feature_set_name)
            if row:
                rows.append(row)
                predictions = predictions.join(pred, how="left")

        if "study_group" in df.columns:
            group = df["study_group"]
            any_diabetes = group.where(group == "healthy", "diabetes")
            label = (any_diabetes == "diabetes").astype(float)
            label[group.isna()] = np.nan
            row, pred = _binary_model(df, features, label, "any_diabetes_vs_healthy", feature_set_name)
            if row:
                rows.append(row)
                predictions = predictions.join(pred, how="left")

            subset = group.isin(["healthy", "insulin_dependent"])
            label = pd.Series(np.nan, index=df.index)
            label.loc[subset] = (group.loc[subset] == "insulin_dependent").astype(float)
            row, pred = _binary_model(df, features, label, "insulin_vs_healthy", feature_set_name)
            if row:
                rows.append(row)
                predictions = predictions.join(pred, how="left")

    performance = pd.DataFrame(rows)
    performance_path.parent.mkdir(parents=True, exist_ok=True)
    performance.to_csv(performance_path, index=False)
    predictions.to_parquet(predictions_path)
    print(f"Wrote performance to {performance_path}")
    print(f"Wrote predictions to {predictions_path}")
    return performance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--performance", type=Path, default=DEFAULT_PERFORMANCE)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    args = parser.parse_args()

    performance = run_prediction_checks(args.input, args.performance, args.predictions)
    sort_cols = ["task", "outcome", "feature_set"]
    print(performance.sort_values(sort_cols).to_string(index=False))


if __name__ == "__main__":
    main()
