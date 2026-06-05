"""
Per-person dynamic coupling features for AI-READI.

This is the first-pass, interpretable feature layer for the network
physiology direction. It deliberately starts with robust, cheap signal
processing features before heavier causal discovery or representation learning.

Default output:
    results/coupling/coupling_features.parquet

Run:
    python -m scripts.coupling.coupling_features --limit 50
    python -m scripts.coupling.coupling_features --include-env
"""

from __future__ import annotations

import argparse
import math
import os
import warnings
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats

from scripts.config import RESULTS_DIR, result_path
from scripts.loaders.cgm import load_cgm
from scripts.loaders.environment import load_environment
from scripts.loaders.wearable import load_wearable_submodality
from scripts.utils.temporal import align_timeseries
from scripts.utils.timezone import get_timezone


DEFAULT_OUTPUT = result_path("coupling_features.parquet")
FREQ = "5min"
STEP_MINUTES = 5
MAX_LAG_STEPS = 24  # +/- 120 minutes at 5 min resolution
MIN_PAIR_POINTS = 144  # 12 hours at 5 min resolution
MSE_SCALES = (1, 3, 12, 36, 72)  # 5 min, 15 min, 1 h, 3 h, 6 h
STUDY_GROUP_ORDER = (
    "healthy",
    "pre_diabetes_lifestyle_controlled",
    "oral_medication_and_or_non_insulin_injectable_medication_controlled",
    "insulin_dependent",
)


def _as_numeric_series(df: pd.DataFrame, value_col: str, out_col: str) -> pd.DataFrame:
    out = df[[value_col]].copy()
    out[value_col] = pd.to_numeric(out[value_col], errors="coerce")
    out = out.rename(columns={value_col: out_col})
    return out.dropna()


def _load_core_aligned(person_id: str, include_env: bool) -> pd.DataFrame:
    sources: dict[str, pd.DataFrame] = {}

    try:
        cgm, _ = load_cgm(person_id)
    except FileNotFoundError:
        cgm = pd.DataFrame()
    if not cgm.empty:
        sources["cgm"] = _as_numeric_series(cgm, "glucose_mg_dl", "glucose_mg_dl")

    try:
        hr = load_wearable_submodality(person_id, "heart_rate")
    except Exception:
        hr = pd.DataFrame()
    if not hr.empty:
        sources["hr"] = _as_numeric_series(hr, "value", "bpm")

    if include_env:
        try:
            env, _ = load_environment(person_id)
        except FileNotFoundError:
            env = pd.DataFrame()
        env_cols = [c for c in ["temp", "hum", "pm2.5"] if c in env.columns]
        if env_cols:
            env = env[env_cols].apply(pd.to_numeric, errors="coerce")
            sources["env"] = env.dropna(how="all")

    if "cgm" not in sources or "hr" not in sources:
        return pd.DataFrame()

    return align_timeseries(sources, freq=FREQ, method="nearest", tolerance="10min")


def _activity_steps_5min(person_id: str, index: pd.DatetimeIndex) -> pd.Series:
    try:
        activity = load_wearable_submodality(person_id, "physical_activity")
    except Exception:
        return pd.Series(0.0, index=index, name="activity_steps")

    if activity.empty or "start_time" not in activity.columns or "value" not in activity.columns:
        return pd.Series(0.0, index=index, name="activity_steps")

    activity = activity.copy()
    activity["value"] = pd.to_numeric(activity["value"], errors="coerce").clip(lower=0)
    activity = activity.dropna(subset=["start_time", "value"])
    if activity.empty:
        return pd.Series(0.0, index=index, name="activity_steps")

    steps = pd.Series(
        activity["value"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(activity["start_time"]),
        name="activity_steps",
    ).sort_index()

    # Garmin physical-activity records are interval-like. This conservative
    # first pass anchors each interval at its start and sums into 5 min bins.
    steps_5min = steps.resample(FREQ).sum().sort_index()
    aligned = steps_5min.reindex(index, method="nearest", tolerance=pd.Timedelta("150s"))
    return aligned.fillna(0.0).astype(float)


def _fallback_sleep_mask(index: pd.DatetimeIndex, person_id: str) -> pd.Series:
    tz = get_timezone(person_id)
    local = index.tz_convert(tz)
    hours = local.hour + local.minute / 60.0
    asleep = (hours >= 22.0) | (hours < 6.0)
    return pd.Series(asleep.astype(float), index=index, name="asleep")


def _sleep_mask_5min(person_id: str, index: pd.DatetimeIndex) -> pd.Series:
    try:
        sleep = load_wearable_submodality(person_id, "sleep")
    except Exception:
        return _fallback_sleep_mask(index, person_id)

    if sleep.empty or not {"start_time", "end_time"}.issubset(sleep.columns):
        return _fallback_sleep_mask(index, person_id)

    sleep = sleep.copy()
    if "value" in sleep.columns:
        sleep = sleep[sleep["value"].astype(str).str.lower() != "awake"]

    sleep = sleep.dropna(subset=["start_time", "end_time"])
    if sleep.empty:
        return _fallback_sleep_mask(index, person_id)

    intervals = (
        pd.DataFrame({"start_time": sleep["start_time"], "end_time": sleep["end_time"]})
        .sort_values("start_time")
        .dropna()
    )
    start_pos = index.searchsorted(pd.DatetimeIndex(intervals["start_time"]), side="left")
    end_pos = index.searchsorted(pd.DatetimeIndex(intervals["end_time"]), side="left")
    diff = np.zeros(len(index) + 1, dtype=int)
    valid = (end_pos > start_pos) & (start_pos < len(index)) & (end_pos > 0)
    for s_pos, e_pos in zip(start_pos[valid], end_pos[valid]):
        s_pos = max(0, min(int(s_pos), len(index)))
        e_pos = max(0, min(int(e_pos), len(index)))
        diff[s_pos] += 1
        diff[e_pos] -= 1
    asleep = np.cumsum(diff[:-1]) > 0

    return pd.Series(asleep.astype(float), index=index, name="asleep")


def _valid_pair(x: pd.Series, y: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    pair = pd.concat([x, y], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(pair) < MIN_PAIR_POINTS:
        return np.array([]), np.array([])
    return pair.iloc[:, 0].to_numpy(dtype=float), pair.iloc[:, 1].to_numpy(dtype=float)


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < MIN_PAIR_POINTS or np.nanstd(x) == 0 or np.nanstd(y) == 0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < MIN_PAIR_POINTS or np.nanstd(x) == 0 or np.nanstd(y) == 0:
        return np.nan
    return float(stats.spearmanr(x, y, nan_policy="omit").statistic)


def _lagged_corr(x: np.ndarray, y: np.ndarray, max_lag_steps: int = MAX_LAG_STEPS) -> dict:
    """Lag convention: positive lag means y follows x."""
    out = {
        "zero_lag_r": np.nan,
        "peak_xcorr": np.nan,
        "peak_abs_xcorr": np.nan,
        "peak_lag_min": np.nan,
    }
    if len(x) < MIN_PAIR_POINTS or np.nanstd(x) == 0 or np.nanstd(y) == 0:
        return out

    lags: list[int] = []
    corrs: list[float] = []
    n = len(x)
    for lag in range(-max_lag_steps, max_lag_steps + 1):
        if lag >= 0:
            xx = x[: n - lag]
            yy = y[lag:]
        else:
            xx = x[-lag:]
            yy = y[: n + lag]
        if len(xx) < MIN_PAIR_POINTS or np.nanstd(xx) == 0 or np.nanstd(yy) == 0:
            continue
        lags.append(lag)
        corrs.append(float(np.corrcoef(xx, yy)[0, 1]))

    if not corrs:
        return out

    corr_arr = np.asarray(corrs, dtype=float)
    lag_arr = np.asarray(lags, dtype=float)
    best = int(np.nanargmax(np.abs(corr_arr)))
    out["zero_lag_r"] = float(corr_arr[np.where(lag_arr == 0)[0][0]]) if 0 in lag_arr else np.nan
    out["peak_xcorr"] = float(corr_arr[best])
    out["peak_abs_xcorr"] = float(abs(corr_arr[best]))
    out["peak_lag_min"] = float(lag_arr[best] * STEP_MINUTES)
    return out


def _residualize(values: np.ndarray, covariates: np.ndarray) -> np.ndarray:
    mask = np.isfinite(values) & np.all(np.isfinite(covariates), axis=1)
    resid = np.full(len(values), np.nan, dtype=float)
    if mask.sum() < MIN_PAIR_POINTS:
        return resid
    x = np.column_stack([np.ones(mask.sum()), covariates[mask]])
    y = values[mask]
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid[mask] = y - x @ beta
    return resid


def _partial_corr(x: pd.Series, y: pd.Series, covariates: pd.DataFrame) -> float:
    frame = pd.concat([x, y, covariates], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < MIN_PAIR_POINTS:
        return np.nan
    xv = frame.iloc[:, 0].to_numpy(dtype=float)
    yv = frame.iloc[:, 1].to_numpy(dtype=float)
    cov = frame.iloc[:, 2:].to_numpy(dtype=float)
    if np.nanstd(xv) == 0 or np.nanstd(yv) == 0:
        return np.nan
    rx = _residualize(xv, cov)
    ry = _residualize(yv, cov)
    mask = np.isfinite(rx) & np.isfinite(ry)
    if mask.sum() < MIN_PAIR_POINTS:
        return np.nan
    return _pearson(rx[mask], ry[mask])


def _coarse_grain(values: np.ndarray, scale: int) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if scale <= 1:
        return x
    n = len(x) // scale
    if n == 0:
        return np.array([])
    return x[: n * scale].reshape(n, scale).mean(axis=1)


def _normalized_shannon_entropy(values: np.ndarray, bins: int = 20) -> float:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 30 or np.nanstd(x) == 0:
        return np.nan
    z = (x - np.nanmean(x)) / np.nanstd(x)
    counts, _ = np.histogram(z, bins=bins, range=(-3, 3))
    total = counts.sum()
    if total == 0:
        return np.nan
    p = counts[counts > 0] / total
    return float(-(p * np.log(p)).sum() / math.log(bins))


def _multiscale_entropy_proxy(values: np.ndarray, prefix: str) -> dict:
    # This is a coarse-grained distributional entropy proxy, not formal
    # Costa-style sample entropy. It is fast enough for cohort-scale screening.
    out = {}
    for scale in MSE_SCALES:
        out[f"{prefix}_ms_entropy_s{scale}"] = _normalized_shannon_entropy(
            _coarse_grain(values, scale)
        )
    return out


def _add_pair_features(
    out: dict,
    name: str,
    x: pd.Series,
    y: pd.Series,
    transform_x=None,
    transform_y=None,
) -> None:
    xv, yv = _valid_pair(x, y)
    out[f"{name}_n"] = int(len(xv))
    out[f"{name}_zero_lag_r"] = np.nan
    out[f"{name}_spearman_r"] = np.nan
    out[f"{name}_peak_xcorr"] = np.nan
    out[f"{name}_peak_abs_xcorr"] = np.nan
    out[f"{name}_peak_lag_min"] = np.nan

    if len(xv) < MIN_PAIR_POINTS:
        return

    if transform_x is not None:
        xv = transform_x(xv)
    if transform_y is not None:
        yv = transform_y(yv)

    out[f"{name}_spearman_r"] = _spearman(xv, yv)
    lagged = _lagged_corr(xv, yv)
    for key, value in lagged.items():
        out[f"{name}_{key}"] = value


def compute_coupling_features(person_id: str, include_env: bool = False) -> dict | None:
    aligned = _load_core_aligned(person_id, include_env=include_env)
    if aligned.empty or not {"cgm_glucose_mg_dl", "hr_bpm"}.issubset(aligned.columns):
        return None

    aligned = aligned.sort_index()
    aligned["activity_steps"] = _activity_steps_5min(person_id, aligned.index)
    aligned["asleep"] = _sleep_mask_5min(person_id, aligned.index)

    glucose = aligned["cgm_glucose_mg_dl"]
    hr = aligned["hr_bpm"]
    activity = np.log1p(aligned["activity_steps"])
    asleep = aligned["asleep"]

    out: dict[str, object] = {
        "person_id": person_id,
        "n_aligned_points": int(len(aligned)),
        "aligned_hours": float(len(aligned) * STEP_MINUTES / 60.0),
        "glucose_mean": float(glucose.mean(skipna=True)),
        "glucose_sd": float(glucose.std(skipna=True)),
        "hr_mean": float(hr.mean(skipna=True)),
        "hr_sd": float(hr.std(skipna=True)),
        "activity_total_steps_proxy": float(aligned["activity_steps"].sum(skipna=True)),
        "sleep_fraction": float(asleep.mean(skipna=True)),
    }

    _add_pair_features(out, "glucose_hr", glucose, hr)
    _add_pair_features(out, "glucose_activity", glucose, activity)
    _add_pair_features(out, "hr_activity", hr, activity)

    cov = pd.DataFrame(
        {
            "activity_log_steps": activity,
            "asleep": asleep,
        },
        index=aligned.index,
    )
    out["glucose_hr_partial_r_activity_sleep"] = _partial_corr(glucose, hr, cov)

    awake = asleep < 0.5
    sleep_state = asleep >= 0.5
    gx, hy = _valid_pair(glucose[awake], hr[awake])
    out["glucose_hr_awake_r"] = _pearson(gx, hy)
    gx, hy = _valid_pair(glucose[sleep_state], hr[sleep_state])
    out["glucose_hr_sleep_r"] = _pearson(gx, hy)

    out.update(_multiscale_entropy_proxy(glucose.to_numpy(dtype=float), "glucose"))
    out.update(_multiscale_entropy_proxy(hr.to_numpy(dtype=float), "hr"))

    if include_env and "env_pm2.5" in aligned.columns:
        pm25 = aligned["env_pm2.5"]
        out["pm25_mean"] = float(pm25.mean(skipna=True))
        out["pm25_sd"] = float(pm25.std(skipna=True))
        _add_pair_features(out, "pm25_glucose", pm25, glucose)
        _add_pair_features(out, "pm25_hr", pm25, hr)

    return out


def _eligible_participants() -> list[str]:
    index_path = result_path("participant_index.parquet")
    if not index_path.exists():
        raise FileNotFoundError(f"Missing {index_path}. Run participant index first.")

    idx = pd.read_parquet(index_path)
    if "person_id" in idx.columns:
        idx = idx.set_index("person_id")

    mask = pd.Series(True, index=idx.index)
    for col in ["wearable_blood_glucose", "wearable_activity_monitor"]:
        if col in idx.columns:
            mask &= idx[col].fillna(False).astype(bool)

    groups = [g for g in STUDY_GROUP_ORDER if g in set(idx.get("study_group", []))]
    if groups and "study_group" in idx.columns:
        mask &= idx["study_group"].isin(groups)

    return sorted(idx.index[mask].astype(str).tolist())


def _parse_people(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    path = Path(raw)
    if path.exists():
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]
    return [part.strip() for part in raw.split(",") if part.strip()]


def _write_rows(rows: list[dict], output: Path) -> pd.DataFrame:
    df = pd.DataFrame(rows).set_index("person_id").sort_index()
    output.parent.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        df.to_parquet(output)
    return df


def run(
    participants: Iterable[str],
    output: Path = DEFAULT_OUTPUT,
    include_env: bool = False,
    checkpoint_every: int = 0,
    resume: bool = False,
) -> pd.DataFrame:
    participants = list(participants)
    rows: list[dict] = []
    failures: list[tuple[str, str]] = []
    completed: set[str] = set()

    if resume and output.exists():
        previous = pd.read_parquet(output)
        if "person_id" in previous.columns:
            previous = previous.set_index("person_id")
        previous.index = previous.index.astype(str)
        completed = set(previous.index)
        rows = previous.reset_index().rename(columns={"index": "person_id"}).to_dict("records")
        participants = [p for p in participants if p not in completed]
        print(
            f"Resuming from {output}: {len(completed)} done, {len(participants)} remaining",
            flush=True,
        )

    for i, person_id in enumerate(participants, start=1):
        try:
            row = compute_coupling_features(person_id, include_env=include_env)
            if row is not None:
                rows.append(row)
        except Exception as exc:  # keep cohort runs moving
            failures.append((person_id, str(exc)))

        if i % 100 == 0:
            print(
                f"Processed {i}/{len(participants)} in this run; "
                f"usable={len(rows)} failures={len(failures)}",
                flush=True,
            )
        if checkpoint_every and i % checkpoint_every == 0 and rows:
            _write_rows(rows, output)
            print(f"Checkpointed {len(rows)} rows to {output}", flush=True)

    if not rows:
        raise RuntimeError("No coupling features could be computed.")

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
    parser.add_argument("--include-env", action="store_true", help="Include PM2.5 coupling features.")
    parser.add_argument("--limit", type=int, default=None, help="Limit participants for pilot runs.")
    parser.add_argument("--checkpoint-every", type=int, default=0)
    parser.add_argument("--resume", action="store_true", help="Resume from an existing output parquet.")
    parser.add_argument("--num-shards", type=int, default=None)
    parser.add_argument("--shard-index", type=int, default=None)
    parser.add_argument(
        "--participants",
        type=str,
        default=None,
        help="Comma-separated person IDs or a text file with one ID per line.",
    )
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
        if shard_index < 0 or shard_index >= num_shards:
            raise ValueError("--shard-index must be in [0, --num-shards).")
        participants = participants[shard_index::num_shards]
        print(
            f"Shard {shard_index}/{num_shards}: {len(participants)} participants",
            flush=True,
        )

    print(
        f"Computing coupling features for {len(participants)} participants "
        f"(include_env={args.include_env})",
        flush=True,
    )
    run(
        participants,
        output=args.output,
        include_env=args.include_env,
        checkpoint_every=args.checkpoint_every,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
