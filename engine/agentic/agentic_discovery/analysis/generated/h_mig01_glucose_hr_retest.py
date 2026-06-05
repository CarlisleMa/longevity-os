"""Re-test H-MIG01 glucose-HR coupling severity gradient.

This analysis intentionally consumes an existing per-participant coupling
feature table rather than raw streams. It is an executable statistical
re-analysis for PLAN-20260515-0001, not a full raw-signal recomputation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


GROUP_ORDER = [
    "healthy",
    "pre_diabetes_lifestyle_controlled",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled",
    "insulin_dependent",
]
GROUP_LABELS = {
    "healthy": "healthy",
    "pre_diabetes_lifestyle_controlled": "pre_diabetes",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": "oral_medication",
    "insulin_dependent": "insulin_dependent",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coupling-features", type=Path, required=True)
    parser.add_argument("--participant-index", type=Path, required=True)
    parser.add_argument("--feature-matrix", type=Path, required=True)
    parser.add_argument("--feature", default="glucose_hr_awake_r")
    parser.add_argument("--candidate-id", default="CAND-LEGACY-H-MIG01")
    parser.add_argument("--plan-id", default="PLAN-20260515-0001")
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--group-csv", type=Path, required=True)
    parser.add_argument("--model-csv", type=Path, required=True)
    args = parser.parse_args()

    df = load_analysis_frame(
        coupling_features=args.coupling_features,
        participant_index=args.participant_index,
        feature_matrix=args.feature_matrix,
        feature=args.feature,
    )
    group_rows = group_summary(df, args.feature)
    model_rows = model_summary(df, args.feature)
    metrics = key_metrics(df, args.feature, group_rows=group_rows, model_rows=model_rows)

    args.group_csv.parent.mkdir(parents=True, exist_ok=True)
    args.model_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(group_rows).to_csv(args.group_csv, index=False)
    pd.DataFrame(model_rows).to_csv(args.model_csv, index=False)

    payload = {
        "analysis_id": "h_mig01_glucose_hr_retest",
        "created_at": now_utc(),
        "candidate_id": args.candidate_id,
        "plan_id": args.plan_id,
        "feature": args.feature,
        "inputs": {
            "coupling_features": str(args.coupling_features),
            "participant_index": str(args.participant_index),
            "feature_matrix": str(args.feature_matrix),
        },
        "outputs": {
            "group_csv": str(args.group_csv),
            "model_csv": str(args.model_csv),
            "summary_json": str(args.output_json),
        },
        "group_order": GROUP_ORDER,
        "group_summary": group_rows,
        "models": model_rows,
        "metrics": metrics,
        "interpretation": interpretation(metrics),
        "limitations": [
            "uses cached per-participant coupling features, not raw signal recomputation",
            "does not implement time-shift surrogate negative control",
            "does not adjust for beta-blocker or HR-modifying medications because no medication-class field was identified",
            "cross-sectional association; no causal progression inference",
        ],
        "mechanical_checks": {
            "feature_present": args.feature in df.columns,
            "all_required_groups_present": all(
                (df["study_group"] == group).any() for group in GROUP_ORDER
            ),
            "n_analyzed": int(df[args.feature].notna().sum()),
            "severity_order_prespecified": GROUP_ORDER,
            "no_test_set_or_train_split_used": True,
        },
    }
    args.output_json.write_text(json.dumps(clean_json(payload), indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(clean_json({"metrics": metrics, "interpretation": payload["interpretation"]}), indent=2))


def load_analysis_frame(
    coupling_features: Path,
    participant_index: Path,
    feature_matrix: Path,
    feature: str,
) -> pd.DataFrame:
    coupling = read_indexed_parquet(coupling_features)
    participant = read_indexed_parquet(participant_index)
    features = read_indexed_parquet(feature_matrix)
    if feature not in coupling.columns:
        raise KeyError(f"Feature not found in coupling table: {feature}")

    keep_participant = [c for c in ["study_group", "age", "clinical_site"] if c in participant.columns]
    keep_features = [c for c in ["hba1c", "bmi"] if c in features.columns]
    keep_coupling = [
        feature,
        "glucose_mean",
        "hr_mean",
        "activity_total_steps_proxy",
        "sleep_fraction",
        "aligned_hours",
    ]
    keep_coupling = [c for c in keep_coupling if c in coupling.columns]
    df = coupling[keep_coupling].join(participant[keep_participant], how="left")
    add_features = features[[c for c in keep_features if c not in df.columns]]
    df = df.join(add_features, how="left")
    df = df[df["study_group"].isin(GROUP_ORDER)].copy()
    df["severity"] = df["study_group"].map({group: idx for idx, group in enumerate(GROUP_ORDER)})
    return df.replace([np.inf, -np.inf], np.nan)


def read_indexed_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_parquet(path)
    if "person_id" in frame.columns:
        frame = frame.set_index("person_id")
    frame.index = frame.index.astype(str)
    return frame


def group_summary(df: pd.DataFrame, feature: str) -> list[dict[str, Any]]:
    rows = []
    for group in GROUP_ORDER:
        values = pd.to_numeric(df.loc[df["study_group"] == group, feature], errors="coerce").dropna()
        rows.append(
            {
                "study_group": group,
                "label": GROUP_LABELS[group],
                "n": int(len(values)),
                "mean": safe_float(values.mean()),
                "median": safe_float(values.median()),
                "sd": safe_float(values.std()),
                "q25": safe_float(values.quantile(0.25)),
                "q75": safe_float(values.quantile(0.75)),
            }
        )
    return rows


def model_summary(df: pd.DataFrame, feature: str) -> list[dict[str, Any]]:
    rows = []
    rows.append(ols_severity(df, feature, covariates=[], label="unadjusted"))
    rows.append(ols_severity(df, feature, covariates=["age", "clinical_site"], label="age_site"))
    rows.append(
        ols_severity(
            df,
            feature,
            covariates=[
                "age",
                "clinical_site",
                "hba1c",
                "bmi",
                "glucose_mean",
                "hr_mean",
                "activity_total_steps_proxy",
                "sleep_fraction",
            ],
            label="full_available_covariates",
        )
    )
    return rows


def key_metrics(
    df: pd.DataFrame,
    feature: str,
    group_rows: list[dict[str, Any]],
    model_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    values_by_group = [
        pd.to_numeric(df.loc[df["study_group"] == group, feature], errors="coerce").dropna()
        for group in GROUP_ORDER
    ]
    kw = stats.kruskal(*values_by_group)
    trend = stats.spearmanr(df["severity"], df[feature], nan_policy="omit")
    jt = jonckheere_terpstra_positive(values_by_group)
    d = cohens_d(values_by_group[0], values_by_group[-1])
    medians = {row["label"]: row["median"] for row in group_rows}
    full_model = next((row for row in model_rows if row["model"] == "full_available_covariates"), {})
    age_site_model = next((row for row in model_rows if row["model"] == "age_site"), {})
    return {
        "n": int(sum(len(values) for values in values_by_group)),
        "kruskal_h": safe_float(kw.statistic),
        "p_kruskal": safe_float(kw.pvalue),
        "severity_spearman_rho": safe_float(trend.statistic),
        "p_severity_spearman": safe_float(trend.pvalue),
        "jonckheere_terpstra_u": safe_float(jt["u"]),
        "jonckheere_terpstra_z_approx": safe_float(jt["z"]),
        "p_jt_positive_approx": safe_float(jt["p_positive"]),
        "healthy_vs_insulin_d": safe_float(d),
        "median_by_group": medians,
        "age_site_severity_coef": age_site_model.get("severity_coef"),
        "p_age_site_severity": age_site_model.get("p_severity"),
        "full_severity_coef": full_model.get("severity_coef"),
        "p_full_severity": full_model.get("p_severity"),
    }


def ols_severity(df: pd.DataFrame, feature: str, covariates: list[str], label: str) -> dict[str, Any]:
    columns = [feature, "severity"] + [c for c in covariates if c in df.columns]
    sub = df[columns].dropna().copy()
    if len(sub) < 50:
        return {"model": label, "n": int(len(sub)), "error": "too_few_rows"}

    x_parts = [sub[["severity"]].astype(float).rename(columns={"severity": "severity"})]
    used_covariates = []
    for covariate in covariates:
        if covariate not in sub.columns:
            continue
        if covariate == "clinical_site":
            dummies = pd.get_dummies(sub[covariate].astype(str), prefix=covariate, drop_first=True)
            if not dummies.empty:
                x_parts.append(dummies.astype(float))
                used_covariates.append(covariate)
            continue
        x_parts.append(sub[[covariate]].astype(float))
        used_covariates.append(covariate)

    x = pd.concat(x_parts, axis=1)
    x.insert(0, "intercept", 1.0)
    y = sub[feature].astype(float).to_numpy()
    x_mat = x.to_numpy(dtype=float)
    beta = np.linalg.pinv(x_mat) @ y
    fitted = x_mat @ beta
    resid = y - fitted
    rank = int(np.linalg.matrix_rank(x_mat))
    dof = max(len(y) - rank, 1)
    sigma2 = float(np.sum(resid**2) / dof)
    cov_beta = sigma2 * np.linalg.pinv(x_mat.T @ x_mat)
    se = np.sqrt(np.clip(np.diag(cov_beta), 0, np.inf))
    severity_idx = list(x.columns).index("severity")
    severity_coef = beta[severity_idx]
    severity_se = se[severity_idx]
    t_stat = severity_coef / severity_se if severity_se > 0 else np.nan
    p_value = 2 * stats.t.sf(abs(t_stat), dof) if np.isfinite(t_stat) else np.nan
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return {
        "model": label,
        "n": int(len(sub)),
        "covariates": used_covariates,
        "severity_coef": safe_float(severity_coef),
        "severity_se": safe_float(severity_se),
        "severity_t": safe_float(t_stat),
        "p_severity": safe_float(p_value),
        "r2": safe_float(r2),
    }


def jonckheere_terpstra_positive(groups: list[pd.Series]) -> dict[str, float]:
    """Normal approximation for positive ordered alternatives.

    The tie correction is intentionally not applied; this is reported as an
    approximate monotonic trend check alongside Spearman trend.
    """

    arrays = [pd.to_numeric(group, errors="coerce").dropna().to_numpy(dtype=float) for group in groups]
    u = 0.0
    for i, left in enumerate(arrays[:-1]):
        for right in arrays[i + 1 :]:
            if len(left) == 0 or len(right) == 0:
                continue
            comp = right[:, None] - left[None, :]
            u += float((comp > 0).sum() + 0.5 * (comp == 0).sum())
    ns = np.array([len(arr) for arr in arrays], dtype=float)
    n = float(ns.sum())
    mean = (n * n - np.sum(ns * ns)) / 4.0
    var = (n * n * (2 * n + 3) - np.sum(ns * ns * (2 * ns + 3))) / 72.0
    z = (u - mean) / np.sqrt(var) if var > 0 else np.nan
    p_positive = stats.norm.sf(z) if np.isfinite(z) else np.nan
    return {"u": u, "z": z, "p_positive": p_positive}


def cohens_d(a: pd.Series, b: pd.Series) -> float:
    a = pd.to_numeric(a, errors="coerce").dropna()
    b = pd.to_numeric(b, errors="coerce").dropna()
    if len(a) < 3 or len(b) < 3:
        return np.nan
    pooled = np.sqrt(((len(a) - 1) * a.var() + (len(b) - 1) * b.var()) / (len(a) + len(b) - 2))
    if pooled == 0 or not np.isfinite(pooled):
        return np.nan
    return float((b.mean() - a.mean()) / pooled)


def interpretation(metrics: dict[str, Any]) -> dict[str, Any]:
    replicated = (
        metrics.get("healthy_vs_insulin_d", 0) > 0
        and metrics.get("p_kruskal", 1) < 0.05
        and metrics.get("p_full_severity", 1) < 0.05
    )
    return {
        "legacy_direction_replicated_in_cached_features": bool(replicated),
        "summary": (
            "Positive severity gradient remains after available covariate adjustment."
            if replicated
            else "Positive severity gradient was not robust under the available checks."
        ),
        "claim_status": "executed_cached_feature_reanalysis",
        "not_final_support_until": [
            "raw signal recomputation is rerun",
            "time-shift surrogate negative control is added",
            "medication-class confounding is resolved or documented unavailable",
        ],
    }


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if not np.isfinite(out):
        return None
    return out


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_json(v) for v in value]
    if isinstance(value, tuple):
        return [clean_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return safe_float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


if __name__ == "__main__":
    main()
