"""Analyze aging-clock residuals against diabetes severity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_RUN_ROOT = Path("foundation_jepa/sequence/artifacts/next_stage")
DEFAULT_CONFIGS = (
    "full_joint",
    "static_only_joint",
    "sequence_only_joint",
    "drop_clinical_joint",
    "drop_imaging_joint",
    "full_age_only",
    "full_pure_jepa",
    "sequence_only_pure_jepa",
)


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if mask.sum() == 0:
        return {"n": 0, "mae": None, "rmse": None, "r2": None, "corr": None}
    true = y_true[mask]
    pred = y_pred[mask]
    err = pred - true
    ss_res = float(np.sum(err * err))
    ss_tot = float(np.sum((true - true.mean()) ** 2))
    corr = None
    if len(true) >= 2 and np.std(true) > 1e-8 and np.std(pred) > 1e-8:
        corr = float(np.corrcoef(true, pred)[0, 1])
    return {
        "n": int(mask.sum()),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err * err))),
        "r2": None if ss_tot < 1e-12 else float(1.0 - ss_res / ss_tot),
        "corr": corr,
    }


def fit_age_calibration(frame: pd.DataFrame, pred_col: str) -> tuple[float, float]:
    train = frame[(frame["split"] == "train") & frame["age"].notna() & frame[pred_col].notna()]
    if len(train) < 2:
        return 0.0, 1.0
    x = train["age"].to_numpy(dtype=np.float64)
    y = train[pred_col].to_numpy(dtype=np.float64)
    x_aug = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.pinv(x_aug) @ y
    return float(beta[0]), float(beta[1])


def add_residuals(frame: pd.DataFrame, pred_col: str) -> pd.DataFrame:
    out = frame.copy()
    intercept, slope = fit_age_calibration(out, pred_col)
    out["clock_pred"] = out[pred_col]
    out["raw_age_accel"] = out["clock_pred"] - out["age"]
    out["age_calibrated_expected"] = intercept + slope * out["age"]
    out["age_residual"] = out["clock_pred"] - out["age_calibrated_expected"]
    out["calibration_intercept"] = intercept
    out["calibration_slope"] = slope
    return out


def load_run(config_dir: Path, config: str, seed: int) -> pd.DataFrame:
    run_dir = config_dir / config / f"seed_{seed}"
    pred_path = run_dir / "predictions.csv"
    if not pred_path.exists():
        raise FileNotFoundError(pred_path)
    frame = pd.read_csv(pred_path)
    frame["config"] = config
    frame["seed"] = seed
    frame["clock_source"] = "supervised_head"
    pred_col = "age_pred"

    pure_probe_path = run_dir / "probe_predictions.csv"
    if config.endswith("pure_jepa") and pure_probe_path.exists():
        probe = pd.read_csv(pure_probe_path)
        probe_cols = ["person_id", "probe_age_pred", "probe_severity"]
        frame = frame.merge(probe[probe_cols], on="person_id", how="left")
        frame["age_pred"] = frame["probe_age_pred"]
        frame["clock_source"] = "frozen_linear_probe"
        pred_col = "age_pred"

    return add_residuals(frame, pred_col)


def load_all_runs(run_root: Path, configs: list[str], seeds: list[int]) -> pd.DataFrame:
    frames = []
    for config in configs:
        for seed in seeds:
            path = run_root / config / f"seed_{seed}" / "predictions.csv"
            if not path.exists():
                continue
            frames.append(load_run(run_root, config, seed))
    if not frames:
        raise FileNotFoundError(f"No predictions found under {run_root}")
    return pd.concat(frames, ignore_index=True)


def summarize_groups(residuals: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, sub in residuals.groupby(["config", "seed", "split", "severity"], dropna=False):
        config, seed, split, severity = keys
        values = sub["age_residual"].to_numpy(dtype=np.float64)
        values = values[np.isfinite(values)]
        if len(values) == 0:
            continue
        rows.append(
            {
                "config": config,
                "seed": seed,
                "split": split,
                "severity": int(severity),
                "n": int(len(values)),
                "age_residual_mean": float(np.mean(values)),
                "age_residual_sd": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                "raw_age_accel_mean": float(np.nanmean(sub["raw_age_accel"])),
                "age_mean": float(np.nanmean(sub["age"])),
            }
        )
    return pd.DataFrame(rows)


def association_rows(residuals: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, sub in residuals.groupby(["config", "seed", "split"]):
        config, seed, split = keys
        y = sub["age_residual"].to_numpy(dtype=np.float64)
        severity = sub["severity"].to_numpy(dtype=np.float64)
        age = sub["age"].to_numpy(dtype=np.float64)
        mask = np.isfinite(y) & np.isfinite(severity) & (severity >= 0) & np.isfinite(age)
        if mask.sum() < 20 or np.std(severity[mask]) < 1e-8:
            continue
        x = np.column_stack([np.ones(mask.sum()), severity[mask]])
        beta = np.linalg.pinv(x) @ y[mask]
        pred = x @ beta
        metrics = regression_metrics(y[mask], pred)
        corr = None
        if np.std(y[mask]) > 1e-8:
            corr = float(np.corrcoef(severity[mask], y[mask])[0, 1])
        rows.append(
            {
                "config": config,
                "seed": seed,
                "split": split,
                "n": int(mask.sum()),
                "residual_per_severity_class": float(beta[1]),
                "severity_residual_corr": corr,
                "severity_residual_r2": metrics["r2"],
            }
        )
    return pd.DataFrame(rows)


def summarize_seed_means(frame: pd.DataFrame, value_cols: list[str]) -> pd.DataFrame:
    return (
        frame.groupby(["config", "split"])[value_cols]
        .agg(["mean", "std"])
        .reset_index()
    )


def frame_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    flat = frame.copy()
    flat.columns = [
        "_".join(str(part) for part in col if str(part))
        if isinstance(col, tuple)
        else str(col)
        for col in flat.columns
    ]
    columns = list(flat.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in flat.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.4g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_interpretation(
    output_dir: Path,
    group_summary: pd.DataFrame,
    association: pd.DataFrame,
) -> None:
    test_assoc = association[association["split"] == "test"].copy()
    lines = [
        "# Aging-Clock Residual Interpretation",
        "",
        "Age residual is calibrated on the train split as:",
        "",
        "```text",
        "age_residual = predicted_age - E[predicted_age | chronological_age]",
        "```",
        "",
        "Positive residual means the clock predicts older-than-expected age after train-split age calibration.",
        "",
        "## Test-Set Severity Association",
        "",
    ]
    if len(test_assoc):
        seed_mean = (
            test_assoc.groupby("config")[
                ["residual_per_severity_class", "severity_residual_corr", "severity_residual_r2"]
            ]
            .agg(["mean", "std"])
            .reset_index()
        )
        lines.append(frame_to_markdown(seed_mean))
    else:
        lines.append("No test-set association rows were available.")

    lines.extend(["", "## Test-Set Group Means", ""])
    test_groups = group_summary[group_summary["split"] == "test"].copy()
    if len(test_groups):
        compact = (
            test_groups.groupby(["config", "severity"])[["age_residual_mean", "raw_age_accel_mean"]]
            .mean()
            .reset_index()
        )
        lines.append(frame_to_markdown(compact))
    else:
        lines.append("No test-set group rows were available.")
    (output_dir / "INTERPRETATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    parser.add_argument("--output-dir", default="foundation_jepa/sequence/artifacts/aging_residuals")
    parser.add_argument("--configs", nargs="*", default=list(DEFAULT_CONFIGS))
    parser.add_argument("--seeds", nargs="*", default=["42", "43", "44"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seeds = [int(seed) for item in args.seeds for seed in str(item).split(",") if seed]
    configs = [token for item in args.configs for token in str(item).split(",") if token]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    residuals = load_all_runs(Path(args.run_root), configs, seeds)
    group_summary = summarize_groups(residuals)
    association = association_rows(residuals)

    residuals.to_csv(output_dir / "residual_rows.csv", index=False)
    group_summary.to_csv(output_dir / "group_summary.csv", index=False)
    association.to_csv(output_dir / "association_summary.csv", index=False)

    seed_mean = summarize_seed_means(
        association,
        ["residual_per_severity_class", "severity_residual_corr", "severity_residual_r2"],
    )
    seed_mean.to_csv(output_dir / "association_seed_means.csv", index=False)
    write_interpretation(output_dir, group_summary, association)

    print(json.dumps({
        "n_rows": int(len(residuals)),
        "n_associations": int(len(association)),
        "output_dir": str(output_dir),
    }, indent=2))


if __name__ == "__main__":
    main()
