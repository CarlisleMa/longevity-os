"""
Per-person cross-modal predictability features.

For each participant, fit lightweight within-person Ridge models on the first
70% of aligned observations and evaluate on the final 30%:

  - glucose from HR, activity, sleep state, local time
  - HR from glucose, activity, sleep state, local time

The held-out R2 values are interpreted as a simple cross-modal predictability
biomarker. This is deliberately small and interpretable.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from scripts.config import RESULTS_DIR, result_path
from .coupling_features import (
    _activity_steps_5min,
    _eligible_participants,
    _load_core_aligned,
    _parse_people,
    _sleep_mask_5min,
    _write_rows,
)
from scripts.utils.timezone import get_timezone


DEFAULT_OUTPUT = result_path("cross_modal_predictability.parquet")
LAGS = (0, 1, 3, 6, 12)  # 0, 5, 15, 30, 60 min
MIN_TRAIN = 500
MIN_TEST = 150


def _local_time_features(index: pd.DatetimeIndex, person_id: str) -> pd.DataFrame:
    local = index.tz_convert(get_timezone(person_id))
    hour = local.hour + local.minute / 60.0
    phase = 2 * np.pi * hour / 24.0
    return pd.DataFrame(
        {
            "tod_sin": np.sin(phase),
            "tod_cos": np.cos(phase),
        },
        index=index,
    )


def _lagged_design(df: pd.DataFrame, predictors: list[str], person_id: str) -> pd.DataFrame:
    parts = []
    for col in predictors:
        for lag in LAGS:
            name = f"{col}_lag{lag}"
            parts.append(df[col].shift(lag).rename(name))
    parts.append(df["asleep"].rename("asleep"))
    parts.append(_local_time_features(df.index, person_id))
    return pd.concat(parts, axis=1)


def _fit_predictability(
    df: pd.DataFrame,
    target: str,
    predictors: list[str],
    person_id: str,
) -> dict:
    x = _lagged_design(df, predictors, person_id)
    y = df[target]
    frame = pd.concat([y.rename("target"), x], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < MIN_TRAIN + MIN_TEST:
        return {"r2": np.nan, "mae": np.nan, "n_train": 0, "n_test": 0}

    split_at = int(len(frame) * 0.70)
    train = frame.iloc[:split_at]
    test = frame.iloc[split_at:]
    if len(train) < MIN_TRAIN or len(test) < MIN_TEST:
        return {"r2": np.nan, "mae": np.nan, "n_train": len(train), "n_test": len(test)}

    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", RidgeCV(alphas=np.logspace(-3, 3, 13))),
        ]
    )
    features = [c for c in frame.columns if c != "target"]
    model.fit(train[features], train["target"])
    pred = model.predict(test[features])
    return {
        "r2": float(r2_score(test["target"], pred)),
        "mae": float(mean_absolute_error(test["target"], pred)),
        "n_train": int(len(train)),
        "n_test": int(len(test)),
    }


def compute_predictability(person_id: str) -> dict | None:
    aligned = _load_core_aligned(person_id, include_env=False)
    if aligned.empty or not {"cgm_glucose_mg_dl", "hr_bpm"}.issubset(aligned.columns):
        return None

    aligned = aligned.sort_index()
    aligned["activity_log_steps"] = np.log1p(_activity_steps_5min(person_id, aligned.index))
    aligned["asleep"] = _sleep_mask_5min(person_id, aligned.index)
    aligned = aligned.rename(columns={"cgm_glucose_mg_dl": "glucose", "hr_bpm": "hr"})

    glucose_model = _fit_predictability(
        aligned,
        target="glucose",
        predictors=["hr", "activity_log_steps"],
        person_id=person_id,
    )
    hr_model = _fit_predictability(
        aligned,
        target="hr",
        predictors=["glucose", "activity_log_steps"],
        person_id=person_id,
    )

    r2_values = [glucose_model["r2"], hr_model["r2"]]
    valid_r2 = [x for x in r2_values if np.isfinite(x)]
    return {
        "person_id": person_id,
        "glucose_from_hr_activity_r2": glucose_model["r2"],
        "glucose_from_hr_activity_mae": glucose_model["mae"],
        "glucose_from_hr_activity_n_train": glucose_model["n_train"],
        "glucose_from_hr_activity_n_test": glucose_model["n_test"],
        "hr_from_glucose_activity_r2": hr_model["r2"],
        "hr_from_glucose_activity_mae": hr_model["mae"],
        "hr_from_glucose_activity_n_train": hr_model["n_train"],
        "hr_from_glucose_activity_n_test": hr_model["n_test"],
        "predictability_mean_r2": float(np.mean(valid_r2)) if valid_r2 else np.nan,
        "predictability_min_r2": float(np.min(valid_r2)) if valid_r2 else np.nan,
    }


def run(
    participants: Iterable[str],
    output: Path = DEFAULT_OUTPUT,
    checkpoint_every: int = 0,
    resume: bool = False,
) -> pd.DataFrame:
    participants = list(participants)
    rows: list[dict] = []
    completed: set[str] = set()
    failures: list[tuple[str, str]] = []

    if resume and output.exists():
        previous = pd.read_parquet(output)
        if "person_id" in previous.columns:
            previous = previous.set_index("person_id")
        previous.index = previous.index.astype(str)
        completed = set(previous.index)
        rows = previous.reset_index().rename(columns={"index": "person_id"}).to_dict("records")
        participants = [p for p in participants if p not in completed]
        print(f"Resuming from {output}: {len(completed)} done, {len(participants)} remaining", flush=True)

    for i, person_id in enumerate(participants, start=1):
        try:
            row = compute_predictability(person_id)
            if row is not None:
                rows.append(row)
        except Exception as exc:
            failures.append((person_id, str(exc)))

        if i % 100 == 0:
            print(
                f"Processed {i}/{len(participants)} in this run; usable={len(rows)} failures={len(failures)}",
                flush=True,
            )
        if checkpoint_every and i % checkpoint_every == 0 and rows:
            _write_rows(rows, output)
            print(f"Checkpointed {len(rows)} rows to {output}", flush=True)

    if not rows:
        raise RuntimeError("No predictability rows could be computed.")

    df = _write_rows(rows, output)
    if failures:
        failure_path = output.with_suffix(".failures.csv")
        pd.DataFrame(failures, columns=["person_id", "error"]).to_csv(failure_path, index=False)
        print(f"Wrote failures to {failure_path}", flush=True)
    print(f"Wrote {df.shape[0]} participants x {df.shape[1]} features to {output}", flush=True)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--participants", type=str, default=None)
    parser.add_argument("--checkpoint-every", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--num-shards", type=int, default=None)
    parser.add_argument("--shard-index", type=int, default=None)
    args = parser.parse_args()

    participants = _parse_people(args.participants) or _eligible_participants()
    if args.limit is not None:
        participants = participants[: args.limit]

    num_shards = args.num_shards
    shard_index = args.shard_index
    if num_shards is None and os.getenv("SLURM_ARRAY_TASK_COUNT"):
        num_shards = int(os.environ["SLURM_ARRAY_TASK_COUNT"])
    if shard_index is None and os.getenv("SLURM_ARRAY_TASK_ID"):
        shard_index = int(os.environ["SLURM_ARRAY_TASK_ID"])
    if num_shards is not None or shard_index is not None:
        if num_shards is None or shard_index is None:
            raise ValueError("Both --num-shards and --shard-index are required for sharded runs.")
        participants = participants[shard_index::num_shards]
        print(f"Shard {shard_index}/{num_shards}: {len(participants)} participants", flush=True)

    print(f"Computing cross-modal predictability for {len(participants)} participants", flush=True)
    run(participants, output=args.output, checkpoint_every=args.checkpoint_every, resume=args.resume)


if __name__ == "__main__":
    main()
