"""Data assembly for isolated foundation-JEPA prototypes.

This module intentionally consumes existing participant-level artifacts only.
It does not modify shared results, scripts, or agent workspaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.config import result_path

GROUP_TO_SEVERITY = {
    "healthy": 0,
    "predm": 1,
    "preDM": 1,
    "pre_diabetes_lifestyle_controlled": 1,
    "prediabetes": 1,
    "oral": 2,
    "oral_medication_and_or_non_insulin_injectable_medication_controlled": 2,
    "insulin": 3,
    "insulin_dependent": 3,
}


@dataclass(frozen=True)
class ModalitySpec:
    name: str
    n_features: int
    columns: list[str]


@dataclass(frozen=True)
class PreparedData:
    ids: np.ndarray
    splits: np.ndarray
    ages: np.ndarray
    age_z: np.ndarray
    age_mean: float
    age_std: float
    study_group: np.ndarray
    severity: np.ndarray
    modalities: dict[str, np.ndarray]
    availability: dict[str, np.ndarray]
    specs: dict[str, ModalitySpec]
    controls: dict[str, object]


def _read_required_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact is missing: {path}")
    return pd.read_parquet(path)


def _read_optional_parquet(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_parquet(path)


def _numeric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    numeric = frame.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.loc[:, numeric.notna().any(axis=0)]
    return numeric.astype("float32")


def _columns_with_prefix(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    columns = [column for column in frame.columns if column.startswith(prefix)]
    return frame.loc[:, columns]


def _normalize_splits(raw: pd.Series) -> np.ndarray:
    values = raw.fillna("unknown").astype(str).str.lower()
    values = values.replace({"valid": "val", "validation": "val"})
    return values.to_numpy(dtype=str)


def _severity_from_group(raw: pd.Series) -> np.ndarray:
    values: list[int] = []
    for value in raw.fillna("unknown").astype(str):
        key = value.strip()
        values.append(GROUP_TO_SEVERITY.get(key, GROUP_TO_SEVERITY.get(key.lower(), -1)))
    return np.asarray(values, dtype=np.int64)


def _standardize_with_train_stats(
    frame: pd.DataFrame, train_mask: np.ndarray
) -> np.ndarray:
    values = frame.to_numpy(dtype=np.float32, copy=True)
    values[~np.isfinite(values)] = np.nan

    fit_mask = np.asarray(train_mask, dtype=bool)
    if fit_mask.sum() == 0:
        fit_mask = np.ones(values.shape[0], dtype=bool)

    fit_values = values[fit_mask]
    valid = np.isfinite(fit_values)
    counts = valid.sum(axis=0).astype(np.float32)
    sums = np.where(valid, fit_values, 0.0).sum(axis=0)
    means = np.divide(sums, counts, out=np.zeros_like(sums), where=counts > 0)

    centered = np.where(valid, fit_values - means, 0.0)
    variances = np.divide(
        (centered * centered).sum(axis=0),
        counts,
        out=np.ones_like(means),
        where=counts > 0,
    )
    stds = np.sqrt(variances)
    stds[(stds < 1e-6) | ~np.isfinite(stds)] = 1.0

    filled = np.where(np.isfinite(values), values, means)
    scaled = (filled - means) / stds
    scaled[~np.isfinite(scaled)] = 0.0
    return scaled.astype(np.float32)


def _age_target(ages: np.ndarray, train_mask: np.ndarray) -> tuple[np.ndarray, float, float]:
    fit_mask = np.asarray(train_mask, dtype=bool) & np.isfinite(ages)
    if fit_mask.sum() == 0:
        fit_mask = np.isfinite(ages)

    age_mean = float(np.nanmean(ages[fit_mask]))
    age_std = float(np.nanstd(ages[fit_mask]))
    if not np.isfinite(age_std) or age_std < 1e-6:
        age_std = 1.0

    age_z = ((ages - age_mean) / age_std).astype(np.float32)
    return age_z, age_mean, age_std


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


def _shuffle_one_modality(
    values: np.ndarray,
    flags: np.ndarray,
    splits: np.ndarray,
    seed: int,
    scope: str,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    shuffled_values = values.copy()
    shuffled_flags = flags.copy()

    if scope == "global":
        groups = [np.arange(values.shape[0])]
    elif scope == "within_split":
        groups = [np.flatnonzero(splits == split) for split in sorted(set(splits))]
    else:
        raise ValueError("shuffle_scope must be either 'within_split' or 'global'")

    for group in groups:
        if len(group) < 2:
            continue
        permuted = group.copy()
        rng.shuffle(permuted)
        shuffled_values[group] = values[permuted]
        shuffled_flags[group] = flags[permuted]
    return shuffled_values, shuffled_flags


def build_prepared_data(
    limit: int | None = None,
    seed: int = 42,
    drop_modalities: list[str] | tuple[str, ...] | None = None,
    shuffle_modalities: list[str] | tuple[str, ...] | None = None,
    shuffle_scope: str = "within_split",
) -> PreparedData:
    """Load and align the current participant-level multimodal artifacts."""

    feature_matrix = _read_required_parquet(result_path("feature_matrix.parquet"))
    if not isinstance(feature_matrix.index, pd.Index):
        raise ValueError("feature_matrix.parquet must be indexed by participant id")

    if limit is not None and limit > 0 and limit < len(feature_matrix):
        rng = np.random.default_rng(seed)
        selected = np.sort(rng.choice(len(feature_matrix), size=limit, replace=False))
        feature_matrix = feature_matrix.iloc[selected].copy()

    multimodal = _read_optional_parquet(result_path("multimodal_features.parquet"))
    retinal = _read_optional_parquet(result_path("retinal_embeddings.parquet"))
    cardiac = _read_optional_parquet(result_path("cardiac_embeddings.parquet"))

    if multimodal is not None:
        multimodal = multimodal.reindex(feature_matrix.index)
    if retinal is not None:
        retinal = retinal.reindex(feature_matrix.index)
    if cardiac is not None:
        cardiac = cardiac.reindex(feature_matrix.index)

    modality_frames: dict[str, pd.DataFrame] = {}

    clinical = feature_matrix.drop(
        columns=[
            "age",
            "recommended_split",
            "study_group",
            "clinical_site",
            "study_visit_date",
        ],
        errors="ignore",
    )
    modality_frames["clinical"] = _numeric_frame(clinical)

    if multimodal is not None:
        modality_frames["cgm"] = _numeric_frame(_columns_with_prefix(multimodal, "cgm_"))
        modality_frames["environment"] = _numeric_frame(
            _columns_with_prefix(multimodal, "env_")
        )
        modality_frames["wearable"] = _numeric_frame(
            _columns_with_prefix(multimodal, "wear_")
        )

    if retinal is not None:
        modality_frames["retinal"] = _numeric_frame(retinal)
    if cardiac is not None:
        modality_frames["cardiac"] = _numeric_frame(cardiac)

    modality_frames = {
        name: frame for name, frame in modality_frames.items() if frame.shape[1] > 0
    }
    available_modalities = list(modality_frames)
    dropped = _expand_modality_selection(
        drop_modalities, available_modalities, "drop_modalities"
    )
    for name in dropped:
        modality_frames.pop(name)

    if len(modality_frames) < 2:
        raise ValueError(
            "At least two modalities are required after applying modality drops"
        )

    splits = _normalize_splits(
        feature_matrix.get(
            "recommended_split",
            pd.Series("train", index=feature_matrix.index, dtype=object),
        )
    )
    train_mask = splits == "train"

    ages = pd.to_numeric(feature_matrix["age"], errors="coerce").to_numpy(
        dtype=np.float32
    )
    age_z, age_mean, age_std = _age_target(ages, train_mask)

    study_group = feature_matrix.get(
        "study_group", pd.Series("unknown", index=feature_matrix.index, dtype=object)
    ).fillna("unknown")
    severity = _severity_from_group(study_group)

    modalities: dict[str, np.ndarray] = {}
    availability: dict[str, np.ndarray] = {}
    specs: dict[str, ModalitySpec] = {}
    for name, frame in modality_frames.items():
        availability[name] = frame.notna().any(axis=1).to_numpy(dtype=bool)
        modalities[name] = _standardize_with_train_stats(frame, train_mask)
        specs[name] = ModalitySpec(
            name=name,
            n_features=int(frame.shape[1]),
            columns=list(frame.columns),
        )

    shuffled = _expand_modality_selection(
        shuffle_modalities, list(modalities), "shuffle_modalities"
    )
    for offset, name in enumerate(shuffled):
        shuffled_values, shuffled_flags = _shuffle_one_modality(
            modalities[name],
            availability[name],
            splits,
            seed=seed + 1009 * (offset + 1),
            scope=shuffle_scope,
        )
        modalities[name] = shuffled_values
        availability[name] = shuffled_flags

    return PreparedData(
        ids=feature_matrix.index.astype(str).to_numpy(),
        splits=splits,
        ages=ages,
        age_z=age_z,
        age_mean=age_mean,
        age_std=age_std,
        study_group=study_group.astype(str).to_numpy(),
        severity=severity,
        modalities=modalities,
        availability=availability,
        specs=specs,
        controls={
            "drop_modalities": dropped,
            "shuffle_modalities": shuffled,
            "shuffle_scope": shuffle_scope if shuffled else None,
        },
    )
