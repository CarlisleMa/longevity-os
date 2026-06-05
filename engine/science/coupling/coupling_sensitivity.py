"""
Sensitivity models for the coupling atlas.

Tests whether diabetes-severity gradients in coupling features persist after
clinical covariates and simple raw-level summaries.

Output:
    results/coupling/coupling_atlas_sensitivity.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from scripts.config import RESULTS_DIR, result_path
from .coupling_atlas import GROUP_ORDER, _candidate_features, _fdr_bh


DEFAULT_INPUT = result_path("coupling_features.parquet")
DEFAULT_OUTPUT = result_path("coupling_atlas_sensitivity.csv")


MODELS = {
    "base_age_site": ["age", "clinical_site"],
    "clinical": ["age", "clinical_site", "hba1c", "bmi"],
    "clinical_plus_levels": [
        "age",
        "clinical_site",
        "hba1c",
        "bmi",
        "glucose_mean",
        "hr_mean",
        "activity_total_steps_proxy",
        "sleep_fraction",
    ],
}


def _read(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if "person_id" in frame.columns:
        frame = frame.set_index("person_id")
    frame.index = frame.index.astype(str)
    return frame


def _load_joined(input_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    coupling = _read(input_path)
    feature_matrix = _read(result_path("feature_matrix.parquet"))
    meta_cols = [c for c in ["study_group", "age", "clinical_site", "hba1c", "bmi"] if c in feature_matrix.columns]
    df = coupling.join(feature_matrix[meta_cols], how="left")
    df = df[df["study_group"].isin(GROUP_ORDER)].copy()
    df["study_group_ordinal"] = df["study_group"].map({g: i for i, g in enumerate(GROUP_ORDER)})
    return coupling, df


def _fit(df: pd.DataFrame, feature: str, covariates: list[str], model_name: str) -> dict | None:
    covariates = [c for c in covariates if c in df.columns and c != feature]
    cols = [feature, "study_group_ordinal"] + covariates
    sub = df[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(sub) < 100:
        return None

    x = pd.DataFrame({"study_group_ordinal": sub["study_group_ordinal"].astype(float)}, index=sub.index)
    for cov in covariates:
        if cov == "clinical_site":
            site = pd.get_dummies(sub[cov].astype(str), prefix="site", drop_first=True)
            x = pd.concat([x, site.astype(float)], axis=1)
        else:
            x[cov] = pd.to_numeric(sub[cov], errors="coerce")
    x = sm.add_constant(x, has_constant="add")
    y = pd.to_numeric(sub[feature], errors="coerce")
    model = sm.OLS(y, x).fit()
    return {
        "feature": feature,
        "model": model_name,
        "n": int(model.nobs),
        "severity_coef": float(model.params["study_group_ordinal"]),
        "p_severity": float(model.pvalues["study_group_ordinal"]),
        "model_r2": float(model.rsquared),
        "covariates": ",".join(covariates),
    }


def run_sensitivity(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> pd.DataFrame:
    coupling, df = _load_joined(input_path)
    rows = []
    for feature in _candidate_features(coupling):
        for model_name, covariates in MODELS.items():
            row = _fit(df, feature, covariates, model_name)
            if row:
                rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("No sensitivity models could be fit.")

    out["p_fdr_by_model"] = np.nan
    for model_name, idx in out.groupby("model").groups.items():
        out.loc[idx, "p_fdr_by_model"] = _fdr_bh(out.loc[idx, "p_severity"])
    out = out.sort_values(["model", "p_fdr_by_model", "p_severity", "feature"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    print(f"Wrote {len(out)} sensitivity models to {output_path}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    out = run_sensitivity(args.input, args.output)
    print(out.groupby("model", group_keys=False).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
