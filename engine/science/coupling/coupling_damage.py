"""
Screen dynamic coupling features against structural and clinical damage markers.

The central test is whether 10-day coupling features explain retinal/cardiac
age acceleration or clinical burden after age, HbA1c, BMI, and site adjustment.

Outputs:
    results/coupling/coupling_damage.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

try:
    import statsmodels.api as sm
except Exception as exc:  # pragma: no cover
    raise ImportError("statsmodels is required for coupling_damage.py") from exc

from scripts.config import RESULTS_DIR, result_path
from .coupling_atlas import _candidate_features, _fdr_bh


DEFAULT_INPUT = result_path("coupling_features.parquet")
DEFAULT_OUTPUT = result_path("coupling_damage.csv")
DEFAULT_TARGETS = [
    "retinal_age_accel",
    "cardiac_age_accel",
    "frailty_index",
    "allostatic_load",
    "homeostatic_dysregulation",
    "kdm_age_accel",
    "hba1c",
    "uacr",
]


def _read_table(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if "person_id" in frame.columns:
        frame = frame.set_index("person_id")
    frame.index = frame.index.astype(str)
    return frame


def _load_outcomes() -> pd.DataFrame:
    tables = []
    for name in [
        "feature_matrix.parquet",
        "clinical_scores.parquet",
        "age_accel.parquet",
        "retinal_age_accel.parquet",
        "cardiac_age_accel.parquet",
    ]:
        path = RESULTS_DIR / name
        if path.exists():
            tables.append(_read_table(path))

    if not tables:
        raise FileNotFoundError("No outcome/covariate result tables found.")

    out = tables[0].copy()
    for table in tables[1:]:
        add_cols = [c for c in table.columns if c not in out.columns]
        out = out.join(table[add_cols], how="left")
    return out


def _zscore(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    sd = s.std()
    if sd == 0 or np.isnan(sd):
        return pd.Series(np.nan, index=series.index)
    return (s - s.mean()) / sd


def _partial_r_from_t(t_value: float, df_resid: float) -> float:
    if not np.isfinite(t_value) or not np.isfinite(df_resid) or df_resid <= 0:
        return np.nan
    r = np.sqrt((t_value * t_value) / (t_value * t_value + df_resid))
    return float(np.sign(t_value) * r)


def _fit_adjusted(df: pd.DataFrame, feature: str, target: str) -> dict:
    covariates = ["age", "bmi", "clinical_site"]
    if target != "hba1c":
        covariates.append("hba1c")
    available_covariates = [c for c in covariates if c in df.columns]
    cols = [feature, target] + available_covariates
    sub = df[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(sub) < 50:
        return {}

    x = pd.DataFrame({"feature_z": _zscore(sub[feature])}, index=sub.index)
    y = _zscore(sub[target])
    if y.notna().sum() < 50 or x["feature_z"].notna().sum() < 50:
        return {}

    for cov in available_covariates:
        if cov == "clinical_site":
            site = pd.get_dummies(sub[cov].astype(str), prefix="site", drop_first=True)
            x = pd.concat([x, site.astype(float)], axis=1)
        else:
            x[cov] = pd.to_numeric(sub[cov], errors="coerce")

    model_frame = pd.concat([y.rename("target_z"), x], axis=1).dropna()
    if len(model_frame) < 50:
        return {}

    x_model = sm.add_constant(model_frame.drop(columns=["target_z"]), has_constant="add")
    model = sm.OLS(model_frame["target_z"], x_model).fit()
    return {
        "target": target,
        "feature": feature,
        "n": int(model.nobs),
        "std_beta": float(model.params["feature_z"]),
        "p_value": float(model.pvalues["feature_z"]),
        "partial_r": _partial_r_from_t(float(model.tvalues["feature_z"]), float(model.df_resid)),
        "model_r2": float(model.rsquared),
        "covariates": ",".join(available_covariates),
    }


def run_damage_screen(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    targets: list[str] | None = None,
) -> pd.DataFrame:
    coupling = _read_table(input_path)
    outcomes = _load_outcomes()
    df = coupling.join(outcomes, how="inner")
    features = _candidate_features(coupling)
    targets = targets or DEFAULT_TARGETS
    targets = [t for t in targets if t in df.columns]
    if not targets:
        raise RuntimeError("None of the requested damage targets were available.")

    rows = []
    for target in targets:
        for feature in features:
            row = _fit_adjusted(df, feature, target)
            if row:
                rows.append(row)

    results = pd.DataFrame(rows)
    if results.empty:
        raise RuntimeError("No adjusted coupling-damage models could be fit.")

    results["p_fdr_by_target"] = np.nan
    for target, idx in results.groupby("target").groups.items():
        results.loc[idx, "p_fdr_by_target"] = _fdr_bh(results.loc[idx, "p_value"])
    results = results.sort_values(["target", "p_fdr_by_target", "p_value", "feature"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)
    print(f"Wrote {len(results)} adjusted coupling-damage tests to {output_path}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--targets",
        type=str,
        default=None,
        help="Comma-separated target columns. Defaults to imaging and clinical damage markers.",
    )
    args = parser.parse_args()

    targets = [x.strip() for x in args.targets.split(",") if x.strip()] if args.targets else None
    results = run_damage_screen(args.input, args.output, targets)

    print("\nTop associations per target:")
    cols = ["target", "feature", "n", "std_beta", "partial_r", "p_fdr_by_target"]
    print(results.groupby("target", group_keys=False).head(5)[cols].to_string(index=False))


if __name__ == "__main__":
    main()
