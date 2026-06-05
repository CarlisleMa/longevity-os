"""Wearable-derived features: per-night sleep architecture, per-day summaries,
circadian rhythm metrics.

All timestamps converted to participant local time before aggregation (night
boundaries, day boundaries, and time-of-day binning are all local-time concepts).
Timezone is derived from clinical_site via utils.timezone.

Key references:
  - Ancoli-Israel S et al., *Sleep* 2003;26:342-392, PMID 12749557 (actigraphy)
  - Witting W et al., *Biol Psychiatry* 1990;27:563-572, PMID 2322616 (IS/IV)
  - Van Someren EJ et al., *Chronobiol Int* 1999;16:505-518, PMID 10442243 (M10/L5/RA)
  - Cornelissen G, *Theor Biol Med Model* 2014;11:16, PMID 24725531 (cosinor)
  - Migueles JH et al., *Sports Medicine* 2017;47:1821-1845, PMID 28303543 (accelerometry)

Caveat: Garmin sleep staging is consumer-grade and has poor epoch-by-epoch
agreement with PSG (Núñez-Cortés 2024 PMID 38557751; Menghini 2025 PMID 40291577).
Treat the sleep architecture metrics as estimates, not PSG-equivalent measurements.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .loaders.wearable import load_wearable_submodality
from .utils.timezone import get_timezone, to_local


# ── Sleep architecture (per night) ─────────────────────────────────────────


def _covered_minutes(intervals: pd.DataFrame) -> float:
    """Total minutes covered by the union of start/end intervals."""
    if intervals.empty:
        return 0.0

    pairs = []
    for start, end in intervals[["start_time", "end_time"]].itertuples(index=False):
        if pd.isna(start) or pd.isna(end) or end <= start:
            continue
        pairs.append((start, end))
    if not pairs:
        return 0.0

    pairs.sort(key=lambda x: x[0])
    merged = []
    cur_start, cur_end = pairs[0]
    for start, end in pairs[1:]:
        if start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))

    return float(sum((end - start).total_seconds() for start, end in merged) / 60)


def segment_nights(sleep_df: pd.DataFrame, gap_min: int = 60) -> list[pd.DataFrame]:
    """Segment a participant's sleep intervals into discrete nights.

    A new night begins when the gap between the end of one interval and the
    start of the next exceeds `gap_min` minutes (default 60).

    Args:
        sleep_df: DataFrame with start_time, end_time, value (stage) columns
            from load_wearable_submodality(pid, 'sleep').
        gap_min: minimum gap in minutes that separates nights.

    Returns:
        List of DataFrames, one per night, each containing the original rows.
        Empty list if sleep_df is empty.
    """
    if sleep_df.empty:
        return []
    df = sleep_df.sort_values("start_time").reset_index(drop=True)
    gaps = df["start_time"] - df["end_time"].shift(1)
    night_id = (gaps > pd.Timedelta(minutes=gap_min)).cumsum()
    return [g.reset_index(drop=True) for _, g in df.groupby(night_id)]


def _night_metrics(night: pd.DataFrame, person_id: str) -> dict:
    """Compute sleep architecture metrics for one night's intervals."""
    night = night.sort_values("start_time").reset_index(drop=True)
    night["duration_min"] = (night["end_time"] - night["start_time"]).dt.total_seconds() / 60

    stages = night["value"]
    sleep_mask = stages.isin(["light", "deep", "rem"])

    # If no actual sleep, return empty-ish row
    if not sleep_mask.any():
        return None

    sleep_intervals = night.loc[sleep_mask, ["start_time", "end_time"]]
    first_sleep_start = sleep_intervals["start_time"].min()
    last_sleep_end = sleep_intervals["end_time"].max()

    night_start = night["start_time"].min()
    night_end = night["end_time"].max()

    tib_min = (night_end - night_start).total_seconds() / 60

    # TST = non-overlapping sleep-stage coverage. Raw Garmin files can contain
    # overlapping intervals; summing rows can make sleep efficiency exceed 100%.
    tst_min = _covered_minutes(night.loc[sleep_mask, ["start_time", "end_time"]])

    # WASO = non-overlapping awake coverage BETWEEN first and last sleep epoch.
    between = night[
        (night["end_time"] > first_sleep_start)
        & (night["start_time"] < last_sleep_end)
    ]
    awake_between = between.loc[between["value"] == "awake", ["start_time", "end_time"]].copy()
    if not awake_between.empty:
        awake_between["start_time"] = awake_between["start_time"].where(
            awake_between["start_time"] > first_sleep_start, first_sleep_start
        )
        awake_between["end_time"] = awake_between["end_time"].where(
            awake_between["end_time"] < last_sleep_end, last_sleep_end
        )
    waso_min = _covered_minutes(awake_between)

    # SOL = time from night_start to first sleep epoch start
    sol_min = (first_sleep_start - night_start).total_seconds() / 60

    # Per-stage durations
    rem_min = _covered_minutes(night.loc[stages == "rem", ["start_time", "end_time"]])
    deep_min = _covered_minutes(night.loc[stages == "deep", ["start_time", "end_time"]])
    light_min = _covered_minutes(night.loc[stages == "light", ["start_time", "end_time"]])

    # N_awakenings = count of "awake" intervals between sleep epochs
    n_awakenings = int((between["value"] == "awake").sum())

    # Sleep midpoint (local time) = midpoint between first sleep start and last sleep end
    midpoint_utc = first_sleep_start + (last_sleep_end - first_sleep_start) / 2
    midpoint_local = to_local(pd.DatetimeIndex([midpoint_utc]), person_id)[0]
    # Represent midpoint as hour-of-day float (e.g., 2.5 = 2:30 AM)
    midpoint_hr = midpoint_local.hour + midpoint_local.minute / 60

    se = tst_min / tib_min * 100 if tib_min > 0 else np.nan

    return {
        "night_start": to_local(pd.DatetimeIndex([night_start]), person_id)[0],
        "night_end": to_local(pd.DatetimeIndex([night_end]), person_id)[0],
        "tib_min": round(tib_min, 1),
        "tst_min": round(tst_min, 1),
        "se": round(se, 2),
        "waso_min": round(waso_min, 1),
        "sol_min": round(sol_min, 1),
        "rem_pct": round(rem_min / tst_min * 100, 2) if tst_min > 0 else np.nan,
        "deep_pct": round(deep_min / tst_min * 100, 2) if tst_min > 0 else np.nan,
        "light_pct": round(light_min / tst_min * 100, 2) if tst_min > 0 else np.nan,
        "n_awakenings": n_awakenings,
        "sleep_midpoint_hr": round(midpoint_hr, 2),
    }


def compute_sleep_architecture(person_id: str) -> pd.DataFrame:
    """Per-night sleep architecture for a participant.

    Returns DataFrame with one row per detected night. Columns:
      night_start, night_end (local time)
      tib_min, tst_min, se (%)
      waso_min, sol_min
      rem_pct, deep_pct, light_pct
      n_awakenings
      sleep_midpoint_hr (clock hours 0-24 in local time)

    Nights separated by >60 min gaps. Night with no actual sleep (all "awake")
    are dropped.
    """
    sleep_df = load_wearable_submodality(person_id, "sleep")
    if sleep_df.empty:
        return pd.DataFrame()

    rows = []
    for night in segment_nights(sleep_df, gap_min=60):
        metrics = _night_metrics(night, person_id)
        if metrics is not None:
            rows.append(metrics)
    return pd.DataFrame(rows)


# ── Calorie time series (continuous, temporal-granularity preserving) ─────


def compute_calorie_timeseries(person_id: str) -> pd.DataFrame:
    """Per-record incremental calorie time series, preserving temporal granularity.

    The raw physical_activity_calorie stream is a noisy cumulative counter:
    mostly monotonically increasing through each day, but intermittently dropping
    to small values (sync glitches where the counter briefly shows a stale/partial
    value before recovering). Verified 2026-04-16 on participant 1023: most "drops"
    are followed within minutes by a return to a value consistent with the prior
    cumulative trajectory, not a true session restart.

    Robust approach: within each local date, track the RUNNING MAXIMUM of the
    raw counter. The per-record kcal delta is the increment to the running max:
        running_max[i] = max(running_max[i-1], raw_value[i])
        kcal_delta[i]  = running_max[i] - running_max[i-1]

    Properties of this aggregation:
      - Daily sum of deltas = daily max of raw counter (physiologically plausible,
        matches step correlation r ≈ 0.66 and ~40 kcal/1000 steps).
      - Preserves temporal granularity: delta > 0 at the moments the cumulative
        counter actually advanced; delta = 0 during idle periods or noise drops.
      - Robust to transient counter drops (they become zero-delta events, not
        spurious kcal additions).

    Caveat: on days where the counter legitimately restarts (e.g., device
    reset), this UNDER-counts because the running-max approach only captures
    the maximum of a single continuous monotonic envelope per day. Without
    a reliable reset-detection signal, this is the safer direction to err.

    Returns DataFrame indexed by local-time timestamp with columns:
      kcal_delta: incremental kcal attributable to this record (≥0)
      running_max: running maximum of the cumulative counter within the day
      raw_value: original record value (for reference/debugging)
    """
    cal_df = load_wearable_submodality(person_id, "physical_activity_calorie")
    if cal_df.empty:
        return pd.DataFrame(columns=["kcal_delta", "running_max", "raw_value"])

    tz = get_timezone(person_id)
    local_idx = cal_df.index.tz_convert(tz)
    df = pd.DataFrame(
        {"raw_value": cal_df["value"].values.astype(float)}, index=local_idx
    ).sort_index()

    # Running max within each local date; delta = diff of running max
    dates = pd.Series(df.index.date, index=df.index)
    running_max = df.groupby(dates)["raw_value"].cummax()
    # diff with prepend=0 gives the first record as its own value (delta = running_max[0])
    kcal_delta = running_max.groupby(dates).diff().fillna(running_max)
    # The first record of each day gets delta = running_max (= raw_value[0]).
    # Subsequent records: delta = running_max[i] - running_max[i-1] (≥ 0).

    df["running_max"] = running_max
    df["kcal_delta"] = kcal_delta
    return df[["kcal_delta", "running_max", "raw_value"]]


# ── Per-day summary ────────────────────────────────────────────────────────


def _assign_asleep(timestamps: pd.DatetimeIndex, sleep_intervals: pd.DataFrame) -> np.ndarray:
    """Boolean array: True if timestamp falls inside a non-awake sleep interval."""
    if sleep_intervals.empty:
        return np.zeros(len(timestamps), dtype=bool)
    non_awake = sleep_intervals[sleep_intervals["value"] != "awake"]
    if non_awake.empty:
        return np.zeros(len(timestamps), dtype=bool)
    starts = non_awake["start_time"].values
    ends = non_awake["end_time"].values
    ts = timestamps.values
    # Vectorized: for each ts, check if any interval contains it.
    # For ~10K timestamps × ~500 intervals this is fast enough.
    asleep = np.zeros(len(ts), dtype=bool)
    for s, e in zip(starts, ends):
        asleep |= (ts >= s) & (ts < e)
    return asleep


def compute_daily_summary(person_id: str) -> pd.DataFrame:
    """Per-date wearable summary.

    Returns DataFrame indexed by local date. Columns:
      hr_mean_day, hr_mean_night: mean HR during waking / sleep periods (bpm)
      resting_hr: 5th percentile of HR during sleep (robust min proxy) (bpm)
      nocturnal_hr_dip: (day - night) / day × 100 (%; non-dipping <10% per
          Eguchi 2009 Am J Hypertens PMC3806286)
      daily_steps: sum per day (reliable)
      daily_active_calories: sum of reset-aware incremental kcal deltas.
          The physical_activity_calorie stream is a cumulative counter with
          transient drops; compute_calorie_timeseries() converts it to per-record
          kcal deltas via a within-day running maximum before aggregation.
      spo2_mean_night, spo2_min_night, t90_night: SpO2 during sleep
      stress_mean_day, stress_sd_day
      rr_mean_day, rr_mean_night: respiratory rate
      sleep_hours: TST in hours (joined from sleep architecture if available)
      n_hr_readings, n_asleep_hr_readings: data-density diagnostics

    Day vs night split uses sleep intervals when available, falling back to
    local clock (22:00-06:00 = night) when no sleep data.
    """
    tz = get_timezone(person_id)

    hr_df = load_wearable_submodality(person_id, "heart_rate")
    spo2_df = load_wearable_submodality(person_id, "oxygen_saturation")
    stress_df = load_wearable_submodality(person_id, "stress")
    rr_df = load_wearable_submodality(person_id, "respiratory_rate")
    act_df = load_wearable_submodality(person_id, "physical_activity")
    cal_df = load_wearable_submodality(person_id, "physical_activity_calorie")
    sleep_df = load_wearable_submodality(person_id, "sleep")

    # Convert each to local time (DatetimeIndex → tz_convert, else .dt.tz_convert)
    def _to_local_index(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        out = df.copy()
        out.index = out.index.tz_convert(tz) if isinstance(out.index, pd.DatetimeIndex) else out.index
        return out

    hr_df = _to_local_index(hr_df)
    spo2_df = _to_local_index(spo2_df)
    stress_df = _to_local_index(stress_df)
    rr_df = _to_local_index(rr_df)

    # Determine asleep mask for each point-record source
    def _asleep_mask(df: pd.DataFrame) -> np.ndarray:
        if df.empty or sleep_df.empty:
            # Fallback clock-based: 22:00-06:00 = night
            if df.empty:
                return np.zeros(0, dtype=bool)
            hours = df.index.hour
            return (hours >= 22) | (hours < 6)
        return _assign_asleep(df.index.tz_convert("UTC"), sleep_df)

    hr_asleep = _asleep_mask(hr_df)
    spo2_asleep = _asleep_mask(spo2_df)
    stress_asleep = _asleep_mask(stress_df)
    rr_asleep = _asleep_mask(rr_df)

    # Group by local date (not by UTC date — crosses midnight differently per site)
    def _day_night_agg(df: pd.DataFrame, asleep: np.ndarray, col: str = "value") -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()
        v = df[col]
        day = v[~asleep]
        night = v[asleep]
        out = pd.DataFrame(
            {
                "date": df.index.date,
                "val": v,
                "asleep": asleep,
            }
        )
        agg_day = out[~out["asleep"]].groupby("date")["val"].mean().rename(f"{col}_mean_day")
        agg_night = out[out["asleep"]].groupby("date")["val"].mean().rename(f"{col}_mean_night")
        return pd.concat([agg_day, agg_night], axis=1)

    # HR aggregations
    if not hr_df.empty:
        hr_tbl = pd.DataFrame({"date": hr_df.index.date, "val": hr_df["value"], "asleep": hr_asleep})
        hr_day = hr_tbl[~hr_tbl["asleep"]].groupby("date")["val"].mean().rename("hr_mean_day")
        hr_night = hr_tbl[hr_tbl["asleep"]].groupby("date")["val"].mean().rename("hr_mean_night")
        resting_hr = hr_tbl[hr_tbl["asleep"]].groupby("date")["val"].quantile(0.05).rename("resting_hr")
        n_hr = hr_tbl.groupby("date").size().rename("n_hr_readings")
        n_hr_asleep = hr_tbl[hr_tbl["asleep"]].groupby("date").size().rename("n_asleep_hr_readings")
        hr_block = pd.concat([hr_day, hr_night, resting_hr, n_hr, n_hr_asleep], axis=1)
    else:
        hr_block = pd.DataFrame()

    # SpO2 aggregations (only night meaningful)
    if not spo2_df.empty:
        spo2_tbl = pd.DataFrame(
            {"date": spo2_df.index.date, "val": spo2_df["value"], "asleep": spo2_asleep}
        )
        spo2_night_grp = spo2_tbl[spo2_tbl["asleep"]].groupby("date")["val"]
        spo2_block = pd.concat(
            [
                spo2_night_grp.mean().rename("spo2_mean_night"),
                spo2_night_grp.min().rename("spo2_min_night"),
                (spo2_tbl[spo2_tbl["asleep"]].groupby("date").apply(
                    lambda g: (g["val"] < 90).mean(), include_groups=False
                )).rename("t90_night"),
            ],
            axis=1,
        )
    else:
        spo2_block = pd.DataFrame()

    # Stress
    if not stress_df.empty:
        stress_tbl = pd.DataFrame(
            {"date": stress_df.index.date, "val": stress_df["value"], "asleep": stress_asleep}
        )
        stress_day_grp = stress_tbl[~stress_tbl["asleep"]].groupby("date")["val"]
        stress_block = pd.concat(
            [
                stress_day_grp.mean().rename("stress_mean_day"),
                stress_day_grp.std().rename("stress_sd_day"),
            ],
            axis=1,
        )
    else:
        stress_block = pd.DataFrame()

    # RR
    if not rr_df.empty:
        rr_tbl = pd.DataFrame(
            {"date": rr_df.index.date, "val": rr_df["value"], "asleep": rr_asleep}
        )
        rr_block = pd.concat(
            [
                rr_tbl[~rr_tbl["asleep"]].groupby("date")["val"].mean().rename("rr_mean_day"),
                rr_tbl[rr_tbl["asleep"]].groupby("date")["val"].mean().rename("rr_mean_night"),
            ],
            axis=1,
        )
    else:
        rr_block = pd.DataFrame()

    # Activity: intervals with start_time, end_time, value (steps)
    if not act_df.empty:
        act_local = act_df.copy()
        act_local["start_time"] = act_local["start_time"].dt.tz_convert(tz)
        act_local["date"] = act_local["start_time"].dt.date
        act_block = act_local.groupby("date")["value"].sum().rename("daily_steps").to_frame()
    else:
        act_block = pd.DataFrame()

    # Calories: per-day aggregate uses SUM of per-record incremental kcal
    # (computed via the reset-aware diff — see compute_calorie_timeseries for
    # details). For continuous temporal analysis use compute_calorie_timeseries
    # directly; this daily column is a convenience aggregate only.
    if not cal_df.empty:
        inc = compute_calorie_timeseries(person_id)["kcal_delta"]
        cal_block = (
            inc.groupby(inc.index.date).sum().rename("daily_active_calories").to_frame()
        )
        cal_block.index.name = "date"
    else:
        cal_block = pd.DataFrame()

    # Sleep hours from sleep architecture (TST)
    sa = compute_sleep_architecture(person_id)
    if not sa.empty:
        sa = sa.copy()
        # Attribute each night to the date of its wake-up (when the person got up)
        sa["date"] = sa["night_end"].dt.date
        sleep_block = sa.groupby("date")["tst_min"].sum().div(60).rename("sleep_hours").to_frame()
    else:
        sleep_block = pd.DataFrame()

    # Combine
    summary = pd.concat(
        [hr_block, spo2_block, stress_block, rr_block, act_block, cal_block, sleep_block],
        axis=1,
    )
    if summary.empty:
        return summary
    summary.index.name = "date"

    # Derived: nocturnal HR dip
    if {"hr_mean_day", "hr_mean_night"}.issubset(summary.columns):
        summary["nocturnal_hr_dip"] = (
            (summary["hr_mean_day"] - summary["hr_mean_night"]) / summary["hr_mean_day"] * 100
        ).round(2)

    return summary.sort_index()


# ── Circadian rhythm metrics (nonparametric + cosinor) ─────────────────────


def _hourly_binned_hr(person_id: str) -> pd.Series:
    """Return mean HR per hour (local time), as a DatetimeIndex-indexed Series."""
    hr_df = load_wearable_submodality(person_id, "heart_rate")
    if hr_df.empty:
        return pd.Series(dtype=float)
    tz = get_timezone(person_id)
    local_idx = hr_df.index.tz_convert(tz)
    hourly = pd.Series(hr_df["value"].values, index=local_idx).resample("1h").mean().dropna()
    return hourly


def compute_circadian_metrics(person_id: str) -> dict:
    """Nonparametric + parametric circadian metrics on hourly-binned HR.

    HR is preferred over steps because it's continuously sampled (steps have
    gaps during sedentary periods that bias IV upward).

    Returns dict with:
      is_: interdaily stability ∈ [0, 1]; higher = more reproducible 24h pattern.
           IS = var(24h-averaged hourly profile) / var(all hourly values).
           (Witting 1990 PMID 2322616)
      iv: intradaily variability; higher = more within-day fragmentation.
          IV = mean squared successive difference / total variance.
      m10: mean HR in the most-active 10 consecutive hours of the 24h profile.
      l5:  mean HR in the least-active 5 consecutive hours of the 24h profile
           (circular search — allows windows that span midnight).
      ra:  relative amplitude = (M10 - L5) / (M10 + L5). Declines with aging.
           (Van Someren 1999 PMID 10442243)
      cosinor_amplitude (A), cosinor_acrophase_hr (φ in clock hours 0-24),
      cosinor_mesor (M) from least-squares fit of A·cos(2π(t − φ)/24) + M.
           (Cornelissen 2014 PMID 24725531)
      n_hours: total hourly bins used.
      n_days_covered: approximate number of calendar days.
    """
    hourly = _hourly_binned_hr(person_id)
    if len(hourly) < 24:
        return {}

    values = hourly.values
    hours_of_day = hourly.index.hour
    overall_mean = values.mean()

    # 24h average profile (mean at each hour-of-day across days)
    profile = np.array([values[hours_of_day == h].mean() for h in range(24)])
    # Drop NaN bins (hours with no data) — variance ops would otherwise NaN
    profile_valid = profile[~np.isnan(profile)]
    if len(profile_valid) < 12:
        return {}

    # IS and IV
    var_total = np.mean((values - overall_mean) ** 2)
    var_between = np.mean((profile_valid - overall_mean) ** 2)
    is_ = var_between / var_total if var_total > 0 else np.nan

    diffs = np.diff(values)
    iv = np.mean(diffs ** 2) / var_total if var_total > 0 else np.nan

    # M10 and L5: circular sliding window on the 24h profile
    # Use np.roll to wrap around midnight
    profile_filled = np.where(np.isnan(profile), overall_mean, profile)
    m10_mean = -np.inf
    l5_mean = np.inf
    for start in range(24):
        w10 = np.array([profile_filled[(start + i) % 24] for i in range(10)])
        w5 = np.array([profile_filled[(start + i) % 24] for i in range(5)])
        if w10.mean() > m10_mean:
            m10_mean = w10.mean()
        if w5.mean() < l5_mean:
            l5_mean = w5.mean()
    ra = (m10_mean - l5_mean) / (m10_mean + l5_mean) if (m10_mean + l5_mean) > 0 else np.nan

    # Cosinor via linear least squares on y = M + a·cos(ωt) + b·sin(ωt)
    t = np.arange(len(values))  # in hours
    omega = 2 * np.pi / 24
    # Use clock hour as t so acrophase is interpretable
    t_hr = hourly.index.hour + hourly.index.minute / 60
    X = np.column_stack([np.ones_like(values), np.cos(omega * t_hr), np.sin(omega * t_hr)])
    # Solve X @ [M, a, b] = values
    coefs, *_ = np.linalg.lstsq(X, values, rcond=None)
    M, a, b = coefs
    amplitude = float(np.sqrt(a ** 2 + b ** 2))
    acrophase_rad = float(np.arctan2(b, a))  # peak of a·cos + b·sin
    acrophase_hr = (acrophase_rad / omega) % 24

    n_days = (hourly.index.max() - hourly.index.min()).total_seconds() / 86400

    return {
        "is_": round(float(is_), 4),
        "iv": round(float(iv), 4),
        "m10": round(float(m10_mean), 2),
        "l5": round(float(l5_mean), 2),
        "ra": round(float(ra), 4),
        "cosinor_amplitude": round(amplitude, 2),
        "cosinor_acrophase_hr": round(acrophase_hr, 2),
        "cosinor_mesor": round(float(M), 2),
        "n_hours": int(len(hourly)),
        "n_days_covered": round(n_days, 1),
    }
