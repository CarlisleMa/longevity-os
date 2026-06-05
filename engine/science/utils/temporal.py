"""Temporal alignment utilities for continuous modalities.

Aligns CGM (5-min), wearable (variable), and environmental (5-sec)
time series onto a common time grid within the ~10-day overlap window.
"""

import pandas as pd
import numpy as np


def get_overlap_window(
    *dataframes: pd.DataFrame,
) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    """Find the overlapping time window across multiple time-indexed DataFrames.

    Returns (start, end) as UTC timestamps, or None if no overlap.
    """
    starts = []
    ends = []
    for df in dataframes:
        if df.empty:
            continue
        idx = df.index if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df.index)
        starts.append(idx.min())
        ends.append(idx.max())

    if not starts:
        return None

    overlap_start = max(starts)
    overlap_end = min(ends)

    if overlap_start >= overlap_end:
        return None
    return (overlap_start, overlap_end)


def align_timeseries(
    dataframes: dict[str, pd.DataFrame],
    freq: str = "5min",
    method: str = "nearest",
    tolerance: str | None = "10min",
) -> pd.DataFrame:
    """Align multiple time-indexed DataFrames onto a common time grid.

    Args:
        dataframes: dict mapping name → DataFrame (must have DatetimeIndex).
            Each DataFrame's value columns are prefixed with the name.
        freq: resampling frequency (e.g., '5min', '1min', '15min').
        method: reindex method ('nearest', 'ffill', 'bfill').
        tolerance: max time gap for 'nearest' match (e.g., '10min').

    Returns a single DataFrame on the common time grid, columns prefixed by source name.
    Only the overlapping time window is returned.

    Note: only numeric columns are aligned. Categorical data (e.g., sleep stages,
    activity names) is silently dropped. For sleep/activity analysis, use the
    interval-based DataFrames from wearable loaders directly.
    """
    non_empty = {k: v for k, v in dataframes.items() if not v.empty}
    if not non_empty:
        return pd.DataFrame()

    window = get_overlap_window(*non_empty.values())
    if window is None:
        return pd.DataFrame()

    start, end = window
    common_index = pd.date_range(start=start, end=end, freq=freq, tz="UTC")

    aligned = pd.DataFrame(index=common_index)
    aligned.index.name = "timestamp"

    tol = pd.Timedelta(tolerance) if tolerance else None

    for name, df in non_empty.items():
        # Select value columns (skip non-numeric for point data)
        value_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not value_cols:
            continue

        sub = df[value_cols].copy()
        sub = sub[~sub.index.duplicated(keep="first")]

        if method == "nearest":
            reindexed = sub.reindex(common_index, method="nearest", tolerance=tol)
        else:
            reindexed = sub.reindex(common_index, method=method)

        reindexed.columns = [f"{name}_{col}" for col in reindexed.columns]
        aligned = aligned.join(reindexed)

    return aligned


def compute_overlap_stats(
    cgm: pd.DataFrame | None = None,
    wearable_hr: pd.DataFrame | None = None,
    environment: pd.DataFrame | None = None,
) -> dict:
    """Compute overlap statistics for the three continuous modalities.

    Returns dict with start/end times, duration, and per-modality coverage.
    """
    modalities = {}
    if cgm is not None and not cgm.empty:
        modalities["cgm"] = cgm
    if wearable_hr is not None and not wearable_hr.empty:
        modalities["wearable_hr"] = wearable_hr
    if environment is not None and not environment.empty:
        modalities["environment"] = environment

    if not modalities:
        return {"overlap_days": 0, "modalities": {}}

    window = get_overlap_window(*modalities.values())

    stats = {"modalities": {}}
    for name, df in modalities.items():
        idx = df.index if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df.index)
        duration = (idx.max() - idx.min()).total_seconds() / 86400
        stats["modalities"][name] = {
            "start": idx.min(),
            "end": idx.max(),
            "duration_days": round(duration, 1),
            "n_records": len(df),
        }

    if window:
        stats["overlap_start"] = window[0]
        stats["overlap_end"] = window[1]
        stats["overlap_days"] = round((window[1] - window[0]).total_seconds() / 86400, 1)
    else:
        stats["overlap_days"] = 0

    return stats
