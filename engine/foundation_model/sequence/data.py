"""Raw 10-day sequence data assembly for JEPA experiments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.loaders.cgm import load_cgm
from scripts.loaders.environment import load_environment
from scripts.loaders.wearable import load_wearable_submodality
from scripts.features_wearable import compute_calorie_timeseries
from scripts.config import result_path


FREQ = "5min"
SEQ_LEN = 10 * 24 * 12
CACHE_VERSION = "sequence_jepa_v2"

GROUP_TO_SEVERITY = {
    "healthy": 0,
    "predm": 1,
    "prediabetes": 1,
    "pre_diabetes_lifestyle_controlled": 1,
    "oral": 2,
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": 2,
    "insulin": 3,
    "insulin_dependent": 3,
}

SEQUENCE_CHANNELS = {
    "cgm": ["glucose_mg_dl"],
    "wearable": ["hr_bpm", "log_steps", "asleep", "active_calories"],
    "environment": ["pm25", "temp", "humidity", "screen", "light_total", "light_blue"],
}


@dataclass(frozen=True)
class ModalitySpec:
    name: str
    n_features: int
    columns: list[str]
    kind: str


@dataclass(frozen=True)
class SequencePreparedData:
    ids: np.ndarray
    splits: np.ndarray
    ages: np.ndarray
    age_z: np.ndarray
    age_mean: float
    age_std: float
    study_group: np.ndarray
    severity: np.ndarray
    sequences: dict[str, np.ndarray]
    sequence_masks: dict[str, np.ndarray]
    static: dict[str, np.ndarray]
    availability: dict[str, np.ndarray]
    specs: dict[str, ModalitySpec]
    controls: dict[str, object]


def _read_required_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact is missing: {path}")
    frame = pd.read_parquet(path)
    if "person_id" in frame.columns:
        frame = frame.set_index("person_id")
    frame.index = frame.index.astype(str)
    return frame


def _read_optional_parquet(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    frame = pd.read_parquet(path)
    if "person_id" in frame.columns:
        frame = frame.set_index("person_id")
    frame.index = frame.index.astype(str)
    return frame


def _numeric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    numeric = frame.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.loc[:, numeric.notna().any(axis=0)]
    return numeric.astype("float32")


def _normalize_splits(raw: pd.Series) -> np.ndarray:
    values = raw.fillna("train").astype(str).str.lower()
    values = values.replace({"valid": "val", "validation": "val"})
    return values.to_numpy(dtype=str)


def _severity_from_group(raw: pd.Series) -> np.ndarray:
    values: list[int] = []
    for value in raw.fillna("unknown").astype(str):
        key = value.strip()
        values.append(GROUP_TO_SEVERITY.get(key, GROUP_TO_SEVERITY.get(key.lower(), -1)))
    return np.asarray(values, dtype=np.int64)


def _expand_modality_selection(
    selected: list[str] | tuple[str, ...] | None,
    available: list[str],
    argument_name: str,
) -> list[str]:
    if not selected:
        return []
    requested: list[str] = []
    for item in selected:
        for token in str(item).split(","):
            token = token.strip()
            if token:
                requested.append(token)
    if "all" in requested:
        requested = list(available)
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise ValueError(
            f"Unknown {argument_name}: {unknown}. Available modalities: {available}"
        )
    return sorted(set(requested), key=available.index)


def _fixed_grid(start: pd.Timestamp) -> pd.DatetimeIndex:
    start = pd.Timestamp(start).tz_convert("UTC").floor(FREQ)
    return pd.date_range(start=start, periods=SEQ_LEN, freq=FREQ, tz="UTC")


def _first_timestamp(frames: list[pd.DataFrame]) -> pd.Timestamp | None:
    starts = []
    for frame in frames:
        if frame is None or frame.empty:
            continue
        if isinstance(frame.index, pd.DatetimeIndex):
            starts.append(frame.index.min())
        elif "start_time" in frame.columns:
            starts.append(pd.DatetimeIndex(frame["start_time"]).min())
        elif "timestamp" in frame.columns:
            starts.append(pd.DatetimeIndex(frame["timestamp"]).min())
    if not starts:
        return None
    return min(starts)


def _point_to_grid(
    series: pd.Series,
    grid: pd.DatetimeIndex,
    tolerance: str = "7min",
) -> np.ndarray:
    if series.empty:
        return np.full(len(grid), np.nan, dtype=np.float32)
    series = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    series = series[~series.index.duplicated(keep="first")]
    if series.empty:
        return np.full(len(grid), np.nan, dtype=np.float32)
    aligned = series.reindex(grid, method="nearest", tolerance=pd.Timedelta(tolerance))
    return aligned.to_numpy(dtype=np.float32)


def _resample_to_grid(
    frame: pd.DataFrame,
    columns: list[str],
    grid: pd.DatetimeIndex,
) -> dict[str, np.ndarray]:
    out = {column: np.full(len(grid), np.nan, dtype=np.float32) for column in columns}
    if frame.empty:
        return out
    available = [column for column in columns if column in frame.columns]
    if not available:
        return out
    sub = frame[available].apply(pd.to_numeric, errors="coerce")
    sub = sub.resample(FREQ).mean()
    sub = sub.reindex(grid)
    for column in available:
        out[column] = sub[column].to_numpy(dtype=np.float32)
    return out


def _activity_steps_to_grid(person_id: str, grid: pd.DatetimeIndex) -> np.ndarray:
    activity = load_wearable_submodality(person_id, "physical_activity")
    values = np.full(len(grid), np.nan, dtype=np.float32)
    if activity.empty or not {"start_time", "value"}.issubset(activity.columns):
        return values
    activity = activity.dropna(subset=["start_time", "value"]).copy()
    if activity.empty:
        return values
    activity["value"] = pd.to_numeric(activity["value"], errors="coerce").clip(lower=0)
    steps = pd.Series(
        activity["value"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(activity["start_time"]),
    ).sort_index()
    steps_5min = steps.resample(FREQ).sum()
    aligned = steps_5min.reindex(grid).fillna(0.0)
    valid_window = (grid >= steps.index.min().floor(FREQ)) & (grid <= steps.index.max().ceil(FREQ))
    values[valid_window] = np.log1p(aligned.to_numpy(dtype=np.float32)[valid_window])
    return values


def _sleep_to_grid(person_id: str, grid: pd.DatetimeIndex) -> np.ndarray:
    sleep = load_wearable_submodality(person_id, "sleep")
    values = np.full(len(grid), np.nan, dtype=np.float32)
    if sleep.empty or not {"start_time", "end_time"}.issubset(sleep.columns):
        return values

    sleep = sleep.dropna(subset=["start_time", "end_time"]).copy()
    if sleep.empty:
        return values

    valid_window = (grid >= sleep["start_time"].min().floor(FREQ)) & (
        grid <= sleep["end_time"].max().ceil(FREQ)
    )
    values[valid_window] = 0.0

    asleep = sleep.copy()
    if "value" in asleep.columns:
        asleep = asleep[asleep["value"].astype(str).str.lower() != "awake"]
    for _, row in asleep.iterrows():
        mask = (grid >= row["start_time"]) & (grid < row["end_time"])
        values[mask] = 1.0
    return values


def _calories_to_grid(person_id: str, grid: pd.DatetimeIndex) -> np.ndarray:
    calories = compute_calorie_timeseries(person_id)
    values = np.full(len(grid), np.nan, dtype=np.float32)
    if calories.empty or "kcal_delta" not in calories.columns:
        return values
    kcal = pd.to_numeric(calories["kcal_delta"], errors="coerce").clip(lower=0).dropna()
    if kcal.empty:
        return values
    kcal = kcal.sort_index()
    if isinstance(kcal.index, pd.DatetimeIndex) and kcal.index.tz is not None:
        kcal.index = kcal.index.tz_convert("UTC")
    kcal_5min = kcal.resample(FREQ).sum()
    aligned = kcal_5min.reindex(grid).fillna(0.0)
    valid_window = (grid >= kcal.index.min().floor(FREQ)) & (
        grid <= kcal.index.max().ceil(FREQ)
    )
    if not valid_window.any():
        return np.full(len(grid), np.nan, dtype=np.float32)
    values[valid_window] = np.log1p(
        aligned.to_numpy(dtype=np.float32)[valid_window]
    )
    return values.astype(np.float32)


def _build_raw_sequences(person_id: str) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    frames_for_start: list[pd.DataFrame] = []

    try:
        cgm, _ = load_cgm(person_id)
    except FileNotFoundError:
        cgm = pd.DataFrame()
    if not cgm.empty:
        frames_for_start.append(cgm)

    hr = load_wearable_submodality(person_id, "heart_rate")
    if not hr.empty:
        frames_for_start.append(hr)

    try:
        env, _ = load_environment(person_id)
    except FileNotFoundError:
        env = pd.DataFrame()
    if not env.empty:
        frames_for_start.append(env)

    start = _first_timestamp(frames_for_start)
    if start is None:
        nan_sequences: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for name, channels in SEQUENCE_CHANNELS.items():
            values = np.full((SEQ_LEN, len(channels)), np.nan, dtype=np.float32)
            mask = np.zeros_like(values, dtype=bool)
            nan_sequences[name] = (values, mask)
        return nan_sequences

    grid = _fixed_grid(start)

    cgm_values = np.full((SEQ_LEN, 1), np.nan, dtype=np.float32)
    if not cgm.empty and "glucose_mg_dl" in cgm.columns:
        cgm_values[:, 0] = _point_to_grid(cgm["glucose_mg_dl"], grid, tolerance="10min")

    wearable_values = np.column_stack(
        [
            _point_to_grid(hr["value"], grid, tolerance="7min")
            if not hr.empty and "value" in hr.columns
            else np.full(len(grid), np.nan, dtype=np.float32),
            _activity_steps_to_grid(person_id, grid),
            _sleep_to_grid(person_id, grid),
            _calories_to_grid(person_id, grid),
        ]
    ).astype(np.float32)

    env_values = np.full((SEQ_LEN, 6), np.nan, dtype=np.float32)
    if not env.empty:
        resampled = _resample_to_grid(env, ["pm2.5", "temp", "hum", "screen"], grid)
        light_cols = [column for column in env.columns if column.startswith("lch")]
        light = pd.DataFrame(index=env.index)
        if light_cols:
            light["light_total"] = env[light_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
        if "lch2" in env.columns:
            light["light_blue"] = pd.to_numeric(env["lch2"], errors="coerce")
        light_resampled = _resample_to_grid(light, ["light_total", "light_blue"], grid)
        env_values = np.column_stack(
            [
                resampled["pm2.5"],
                resampled["temp"],
                resampled["hum"],
                resampled["screen"],
                light_resampled["light_total"],
                light_resampled["light_blue"],
            ]
        ).astype(np.float32)

    out = {
        "cgm": (cgm_values, np.isfinite(cgm_values)),
        "wearable": (wearable_values, np.isfinite(wearable_values)),
        "environment": (env_values, np.isfinite(env_values)),
    }
    return out


def _cache_path(cache_dir: Path, person_id: str) -> Path:
    return cache_dir / f"{person_id}.npz"


def _load_or_build_sequences(
    person_id: str,
    cache_dir: Path | None = None,
    use_cache: bool = True,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = _cache_path(cache_dir, person_id)
        if use_cache and path.exists():
            try:
                data = np.load(path, allow_pickle=False)
                if str(data["version"]) == CACHE_VERSION:
                    return {
                        name: (data[f"{name}_values"], data[f"{name}_mask"].astype(bool))
                        for name in SEQUENCE_CHANNELS
                    }
            except Exception:
                pass

    sequences = _build_raw_sequences(person_id)
    if cache_dir is not None and use_cache:
        path = _cache_path(cache_dir, person_id)
        payload: dict[str, Any] = {"version": np.asarray(CACHE_VERSION)}
        for name, (values, mask) in sequences.items():
            payload[f"{name}_values"] = values.astype(np.float32)
            payload[f"{name}_mask"] = mask.astype(np.uint8)
        np.savez_compressed(path, **payload)
    return sequences


def _standardize_static(frame: pd.DataFrame, train_mask: np.ndarray) -> np.ndarray:
    values = frame.to_numpy(dtype=np.float32, copy=True)
    values[~np.isfinite(values)] = np.nan
    fit = train_mask.astype(bool)
    if fit.sum() == 0:
        fit = np.ones(values.shape[0], dtype=bool)
    fit_values = values[fit]
    means = np.nanmean(fit_values, axis=0)
    stds = np.nanstd(fit_values, axis=0)
    means[~np.isfinite(means)] = 0.0
    stds[(stds < 1e-6) | ~np.isfinite(stds)] = 1.0
    filled = np.where(np.isfinite(values), values, means)
    scaled = (filled - means) / stds
    scaled[~np.isfinite(scaled)] = 0.0
    return scaled.astype(np.float32)


def _standardize_sequence(
    values: np.ndarray,
    masks: np.ndarray,
    train_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    valid = masks.astype(bool) & np.isfinite(values)
    fit_values = values[train_mask.astype(bool)]
    fit_valid = valid[train_mask.astype(bool)]
    means = []
    stds = []
    for channel in range(values.shape[-1]):
        channel_values = fit_values[..., channel][fit_valid[..., channel]]
        if len(channel_values) == 0:
            means.append(0.0)
            stds.append(1.0)
        else:
            mean = float(np.mean(channel_values))
            std = float(np.std(channel_values))
            means.append(mean if np.isfinite(mean) else 0.0)
            stds.append(std if np.isfinite(std) and std > 1e-6 else 1.0)
    mean_arr = np.asarray(means, dtype=np.float32)
    std_arr = np.asarray(stds, dtype=np.float32)
    filled = np.where(valid, values, mean_arr.reshape(1, 1, -1))
    scaled = (filled - mean_arr.reshape(1, 1, -1)) / std_arr.reshape(1, 1, -1)
    scaled[~np.isfinite(scaled)] = 0.0
    return scaled.astype(np.float32), valid.astype(np.float32)


def _age_target(ages: np.ndarray, train_mask: np.ndarray) -> tuple[np.ndarray, float, float]:
    fit = train_mask.astype(bool) & np.isfinite(ages)
    if fit.sum() == 0:
        fit = np.isfinite(ages)
    age_mean = float(np.nanmean(ages[fit]))
    age_std = float(np.nanstd(ages[fit]))
    if not np.isfinite(age_std) or age_std < 1e-6:
        age_std = 1.0
    return ((ages - age_mean) / age_std).astype(np.float32), age_mean, age_std


def _shuffle_modality(
    array: np.ndarray,
    availability: np.ndarray,
    splits: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    shuffled = array.copy()
    shuffled_availability = availability.copy()
    for split in sorted(set(splits)):
        idx = np.flatnonzero(splits == split)
        if len(idx) < 2:
            continue
        permuted = idx.copy()
        rng.shuffle(permuted)
        shuffled[idx] = array[permuted]
        shuffled_availability[idx] = availability[permuted]
    return shuffled, shuffled_availability


def build_sequence_data(
    limit: int | None = None,
    seed: int = 42,
    cache_dir: str | Path | None = "foundation_jepa/sequence/artifacts/cache_5min_10d",
    use_cache: bool = True,
    drop_modalities: list[str] | tuple[str, ...] | None = None,
    shuffle_modalities: list[str] | tuple[str, ...] | None = None,
    min_coverage: float = 0.05,
) -> SequencePreparedData:
    feature_matrix = _read_required_parquet(result_path("feature_matrix.parquet"))
    if limit is not None and limit > 0 and limit < len(feature_matrix):
        rng = np.random.default_rng(seed)
        selected = np.sort(rng.choice(len(feature_matrix), size=limit, replace=False))
        feature_matrix = feature_matrix.iloc[selected].copy()

    ids = feature_matrix.index.astype(str).to_numpy()
    splits = _normalize_splits(
        feature_matrix.get(
            "recommended_split",
            pd.Series("train", index=feature_matrix.index, dtype=object),
        )
    )
    train_mask = splits == "train"

    cache_path = Path(cache_dir) if cache_dir else None
    raw_by_modality = {
        name: np.zeros((len(ids), SEQ_LEN, len(channels)), dtype=np.float32)
        for name, channels in SEQUENCE_CHANNELS.items()
    }
    masks_by_modality = {
        name: np.zeros((len(ids), SEQ_LEN, len(channels)), dtype=np.float32)
        for name, channels in SEQUENCE_CHANNELS.items()
    }

    for i, person_id in enumerate(ids, start=1):
        sequences = _load_or_build_sequences(person_id, cache_path, use_cache=use_cache)
        for name, (values, mask) in sequences.items():
            raw_by_modality[name][i - 1] = values
            masks_by_modality[name][i - 1] = mask.astype(np.float32)
        if i % 100 == 0:
            print(f"Loaded sequence tensors for {i}/{len(ids)} participants", flush=True)

    sequences: dict[str, np.ndarray] = {}
    sequence_masks: dict[str, np.ndarray] = {}
    availability: dict[str, np.ndarray] = {}
    specs: dict[str, ModalitySpec] = {}

    for name, values in raw_by_modality.items():
        scaled, valid = _standardize_sequence(values, masks_by_modality[name], train_mask)
        sequences[name] = scaled
        sequence_masks[name] = valid
        availability[name] = (valid.mean(axis=(1, 2)) >= min_coverage)
        specs[name] = ModalitySpec(
            name=name,
            n_features=int(values.shape[-1]),
            columns=list(SEQUENCE_CHANNELS[name]),
            kind="sequence",
        )

    clinical = feature_matrix.drop(
        columns=["age", "recommended_split", "study_group", "clinical_site", "study_visit_date"],
        errors="ignore",
    )
    static_frames: dict[str, pd.DataFrame] = {"clinical": _numeric_frame(clinical)}

    retinal = _read_optional_parquet(result_path("retinal_embeddings.parquet"))
    if retinal is not None:
        static_frames["retinal"] = _numeric_frame(retinal.reindex(feature_matrix.index))
    cardiac = _read_optional_parquet(result_path("cardiac_embeddings.parquet"))
    if cardiac is not None:
        static_frames["cardiac"] = _numeric_frame(cardiac.reindex(feature_matrix.index))

    static: dict[str, np.ndarray] = {}
    for name, frame in static_frames.items():
        if frame.shape[1] == 0:
            continue
        static[name] = _standardize_static(frame, train_mask)
        availability[name] = frame.notna().any(axis=1).to_numpy(dtype=bool)
        specs[name] = ModalitySpec(
            name=name,
            n_features=int(frame.shape[1]),
            columns=list(frame.columns),
            kind="static",
        )

    all_modalities = list(sequences) + list(static)
    dropped = _expand_modality_selection(drop_modalities, all_modalities, "drop_modalities")
    for name in dropped:
        sequences.pop(name, None)
        sequence_masks.pop(name, None)
        static.pop(name, None)
        availability.pop(name, None)
        specs.pop(name, None)

    shuffled = _expand_modality_selection(
        shuffle_modalities, list(specs), "shuffle_modalities"
    )
    for offset, name in enumerate(shuffled):
        if name in sequences:
            sequences[name], availability[name] = _shuffle_modality(
                sequences[name], availability[name], splits, seed + 997 * (offset + 1)
            )
            sequence_masks[name], _ = _shuffle_modality(
                sequence_masks[name],
                availability[name],
                splits,
                seed + 997 * (offset + 1),
            )
        elif name in static:
            static[name], availability[name] = _shuffle_modality(
                static[name], availability[name], splits, seed + 997 * (offset + 1)
            )

    if len(specs) < 2:
        raise ValueError("At least two modalities are required for sequence JEPA")

    ages = pd.to_numeric(feature_matrix["age"], errors="coerce").to_numpy(np.float32)
    age_z, age_mean, age_std = _age_target(ages, train_mask)
    study_group = feature_matrix.get(
        "study_group", pd.Series("unknown", index=feature_matrix.index, dtype=object)
    ).fillna("unknown")
    severity = _severity_from_group(study_group)

    return SequencePreparedData(
        ids=ids,
        splits=splits,
        ages=ages,
        age_z=age_z,
        age_mean=age_mean,
        age_std=age_std,
        study_group=study_group.astype(str).to_numpy(),
        severity=severity,
        sequences=sequences,
        sequence_masks=sequence_masks,
        static=static,
        availability=availability,
        specs=specs,
        controls={
            "drop_modalities": dropped,
            "shuffle_modalities": shuffled,
            "min_coverage": min_coverage,
            "seq_len": SEQ_LEN,
            "freq": FREQ,
        },
    )
