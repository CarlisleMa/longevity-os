"""Test OCTA-derived biomarkers as predictors of MoCA.

This script consumes participant-level features created by
`extract_octa_biomarkers.py` and evaluates whether OCTA features improve MoCA
prediction beyond the same demographic/clinical baseline used in the main MoCA
mapping analysis.

Usage:
    python -m neuro_moca_mapping.run_octa_moca_mapping \
        --octa-features results/neuro_moca_mapping/octa_maestro2_macula_6_x_6_enface_only_participant_features.parquet
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning

from scripts.config import RESULTS_DIR, result_path

from .run_moca_mapping import (
    CLINICAL_SCORE_COLS,
    LAB_AND_VITAL_COLS,
    MOCA_LOW_TARGET,
    MOCA_TOTAL,
    SELECTED_DOMAIN_TARGETS,
    FeatureSpec,
    fit_classification,
    fit_regression,
    leakage_columns,
    unique_existing,
)


DEFAULT_OCTA_FEATURES = (
    RESULTS_DIR
    / "neuro_moca_mapping"
    / "octa_maestro2_macula_6_x_6_enface_only_participant_features.parquet"
)


def read_indexed(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "person_id" in df.columns:
        df = df.set_index("person_id")
    df.index = df.index.astype(str)
    df.index.name = "person_id"
    return df


def load_frame(octa_features_path: Path, split_column: str) -> tuple[pd.DataFrame, tuple[str, ...]]:
    feature_matrix = read_indexed(result_path("feature_matrix.parquet"))
    clinical_scores = read_indexed(result_path("clinical_scores.parquet"))
    octa = read_indexed(octa_features_path)

    df = feature_matrix.join(clinical_scores, how="left", rsuffix="_clinical_score")
    df = df.join(octa, how="left")

    split_path = result_path("split_assignments.parquet")
    if split_column not in df.columns and split_path.exists():
        splits = read_indexed(split_path)
        if split_column in splits.columns:
            df = df.join(splits[[split_column]], how="left")

    octa_cols = tuple(c for c in octa.columns if c in df.columns)
    if not octa_cols:
        raise ValueError(f"No OCTA feature columns found in {octa_features_path}")
    return df, octa_cols


def build_specs(df: pd.DataFrame, octa_cols: tuple[str, ...]) -> list[FeatureSpec]:
    leaked = leakage_columns(df)
    demo_num = unique_existing(["age"], df, leaked)
    demo_cat = unique_existing(["clinical_site", "study_group"], df, leaked)
    clinical_num = unique_existing(LAB_AND_VITAL_COLS + CLINICAL_SCORE_COLS, df, leaked)
    octa_num = unique_existing(octa_cols, df, leaked)
    demo_plus_clinical = demo_num + clinical_num

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
            description="Demographics plus clinical/metabolic features.",
        ),
        FeatureSpec(
            name="octa_biomarkers",
            numeric=octa_num,
            required_groups=(octa_num,),
            cohort="octa_feature_available",
            description="OCTA en face/segmentation biomarkers only.",
        ),
        FeatureSpec(
            name="clinical_on_octa_cohort",
            numeric=demo_plus_clinical,
            categorical=demo_cat,
            required_groups=(octa_num,),
            cohort="octa_feature_available",
            description="Clinical/metabolic baseline refit on the OCTA feature cohort.",
        ),
        FeatureSpec(
            name="clinical_plus_octa_biomarkers",
            numeric=demo_plus_clinical + octa_num,
            categorical=demo_cat,
            required_groups=(octa_num,),
            cohort="octa_feature_available",
            description="Clinical/metabolic predictors plus OCTA biomarkers.",
        ),
    ]


def cohort_summary(df: pd.DataFrame, split_column: str, octa_cols: tuple[str, ...]) -> pd.DataFrame:
    has_octa = df[list(octa_cols)].notna().any(axis=1)
    eligible = df[MOCA_TOTAL].notna() & df[split_column].isin(("train", "val", "test"))
    rows = []
    for cohort_name, cohort_mask in {
        "all_moca": eligible,
        "octa_feature_available": eligible & has_octa,
    }.items():
        for split_label in ("all", "train", "val", "test"):
            if split_label == "all":
                mask = cohort_mask
            else:
                mask = cohort_mask & df[split_column].eq(split_label)
            scores = df.loc[mask, MOCA_TOTAL].astype(float)
            rows.append({
                "cohort": cohort_name,
                "split": split_label,
                "n": int(mask.sum()),
                "moca_total_mean": float(scores.mean()) if len(scores) else float("nan"),
                "moca_total_sd": float(scores.std()) if len(scores) else float("nan"),
                "n_moca_low_lt26": int((scores < 26).sum()) if len(scores) else 0,
                "prevalence_moca_low_lt26": float((scores < 26).mean()) if len(scores) else float("nan"),
            })
    return pd.DataFrame(rows)


def incremental_table(perf: pd.DataFrame) -> pd.DataFrame:
    base = perf[perf["model_name"].eq("clinical_on_octa_cohort")]
    aug = perf[perf["model_name"].eq("clinical_plus_octa_biomarkers")]
    merged = base.merge(
        aug,
        on=["task", "target", "split", "cohort"],
        suffixes=("_baseline", "_augmented"),
    )
    rows = []
    for _, row in merged.iterrows():
        out = {
            "contrast": "octa_increment",
            "task": row["task"],
            "target": row["target"],
            "split": row["split"],
            "cohort": row["cohort"],
            "n_eval": int(row["n_eval_augmented"]),
        }
        for metric in ["r2", "mae", "auroc", "auprc", "balanced_accuracy", "brier"]:
            out[f"{metric}_baseline"] = row[f"{metric}_baseline"]
            out[f"{metric}_augmented"] = row[f"{metric}_augmented"]
            out[f"delta_{metric}"] = row[f"{metric}_augmented"] - row[f"{metric}_baseline"]
        rows.append(out)
    return pd.DataFrame(rows)


def run(args: argparse.Namespace) -> None:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)

    octa_path = Path(args.octa_features)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not octa_path.exists():
        raise FileNotFoundError(f"Missing OCTA feature file: {octa_path}")

    df, octa_cols = load_frame(octa_path, args.split_column)
    df[MOCA_LOW_TARGET] = np.where(df[MOCA_TOTAL].notna(), df[MOCA_TOTAL] < 26, np.nan)
    specs = build_specs(df, octa_cols)

    cohort = cohort_summary(df, args.split_column, octa_cols)
    cohort.to_csv(out_dir / "octa_cohort_summary.csv", index=False)

    performance_rows: list[dict] = []
    meta_rows: list[dict] = []
    for spec in specs:
        print(f"[moca_total] {spec.name}")
        rows, meta = fit_regression(df, spec, MOCA_TOTAL, args.split_column, args.max_missing_frac)
        performance_rows.extend(rows)
        meta_rows.append(meta)

        print(f"[moca_low_lt26] {spec.name}")
        rows, meta = fit_classification(df, spec, args.split_column, args.max_missing_frac)
        performance_rows.extend(rows)
        meta_rows.append(meta)

    perf = pd.DataFrame(performance_rows)
    perf.to_csv(out_dir / "octa_model_performance.csv", index=False)
    pd.DataFrame(meta_rows).to_csv(out_dir / "octa_model_fit_metadata.csv", index=False)
    incremental = incremental_table(perf)
    incremental.to_csv(out_dir / "octa_incremental_performance.csv", index=False)

    domain_rows: list[dict] = []
    if not args.skip_domains:
        domain_specs = [
            spec for spec in specs
            if spec.name in {"clinical_metabolic", "clinical_plus_octa_biomarkers"}
        ]
        for target in SELECTED_DOMAIN_TARGETS:
            if target not in df.columns:
                continue
            for spec in domain_specs:
                print(f"[{target}] {spec.name}")
                rows, _ = fit_regression(df, spec, target, args.split_column, args.max_missing_frac)
                domain_rows.extend(rows)
    if domain_rows:
        pd.DataFrame(domain_rows).to_csv(out_dir / "octa_domain_performance.csv", index=False)

    test = perf[perf["split"].eq("test")]
    summary = {
        "octa_features": str(octa_path),
        "n_octa_features": len(octa_cols),
        "best_test_regression": test[test["task"].eq("regression")]
        .sort_values("r2", ascending=False)
        [["model_name", "cohort", "n_eval", "n_features", "r2", "mae", "pearson_r"]]
        .head(5)
        .to_dict(orient="records"),
        "best_test_classification": test[test["task"].eq("classification")]
        .sort_values("auroc", ascending=False)
        [["model_name", "cohort", "n_eval", "n_features", "auroc", "auprc", "balanced_accuracy"]]
        .head(5)
        .to_dict(orient="records"),
        "test_incremental": incremental[incremental["split"].eq("test")].to_dict(orient="records"),
    }
    with (out_dir / "octa_analysis_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote OCTA MoCA mapping results to {out_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--octa-features", default=str(DEFAULT_OCTA_FEATURES))
    parser.add_argument("--split-column", default="recommended_split")
    parser.add_argument("--output-dir", default=str(RESULTS_DIR / "neuro_moca_mapping"))
    parser.add_argument("--max-missing-frac", type=float, default=0.50)
    parser.add_argument("--skip-domains", action="store_true")
    return parser.parse_args()


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
