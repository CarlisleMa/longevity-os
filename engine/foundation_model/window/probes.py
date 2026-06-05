"""Physiology probes for window-level JEPA context embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from .data import WindowPreparedData

PROBE_STANDARDIZED_FEATURE_CLIP = 10.0


def _move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {
        "context_values": {
            name: tensor.to(device) for name, tensor in batch["context_values"].items()
        },
        "context_masks": {
            name: tensor.to(device) for name, tensor in batch["context_masks"].items()
        },
        "target_values": {
            name: tensor.to(device) for name, tensor in batch["target_values"].items()
        },
        "target_masks": {
            name: tensor.to(device) for name, tensor in batch["target_masks"].items()
        },
        "target_modality_id": batch["target_modality_id"].to(device),
        "person_idx": batch["person_idx"].to(device),
        "target_person_idx": batch["target_person_idx"].to(device),
        "context_start": batch["context_start"].to(device),
        "target_start": batch["target_start"].to(device),
        "indices": batch["indices"].to(device),
        "static": {name: tensor.to(device) for name, tensor in batch["static"].items()},
        "static_availability": {
            name: tensor.to(device)
            for name, tensor in batch["static_availability"].items()
        },
    }


def _masked_values(
    values: np.ndarray,
    masks: np.ndarray,
    start: int,
    length: int,
    channel: int,
) -> np.ndarray:
    segment = values[start : start + length, channel]
    valid = masks[start : start + length, channel] > 0.5
    out = segment[valid]
    return out[np.isfinite(out)]


def _mean(values: np.ndarray) -> float:
    return float(np.mean(values)) if len(values) else np.nan


def _std(values: np.ndarray) -> float:
    return float(np.std(values)) if len(values) else np.nan


def _delta(values: np.ndarray) -> float:
    if len(values) < 2:
        return np.nan
    mid = max(len(values) // 2, 1)
    first = values[:mid]
    second = values[mid:]
    if len(second) == 0:
        return np.nan
    return float(np.mean(second) - np.mean(first))


def _window_summary(
    data: WindowPreparedData,
    person_i: int,
    start: int,
    length: int,
    prefix: str,
) -> dict[str, float]:
    row: dict[str, float] = {}
    if "cgm" in data.base.sequences:
        values = _masked_values(
            data.base.sequences["cgm"][person_i],
            data.base.sequence_masks["cgm"][person_i],
            start,
            length,
            0,
        )
        row[f"{prefix}_cgm_mean_z"] = _mean(values)
        row[f"{prefix}_cgm_sd_z"] = _std(values)
        row[f"{prefix}_cgm_delta_z"] = _delta(values)

    if "wearable" in data.base.sequences:
        wearable_names = ["hr", "steps", "asleep", "calories"]
        for channel, name in enumerate(wearable_names):
            values = _masked_values(
                data.base.sequences["wearable"][person_i],
                data.base.sequence_masks["wearable"][person_i],
                start,
                length,
                channel,
            )
            row[f"{prefix}_{name}_mean_z"] = _mean(values)
            row[f"{prefix}_{name}_sd_z"] = _std(values)
            if name == "hr":
                row[f"{prefix}_{name}_delta_z"] = _delta(values)

    if "environment" in data.base.sequences:
        env_names = ["pm25", "temp", "humidity", "screen", "light_total", "light_blue"]
        for channel, name in enumerate(env_names):
            values = _masked_values(
                data.base.sequences["environment"][person_i],
                data.base.sequence_masks["environment"][person_i],
                start,
                length,
                channel,
            )
            row[f"{prefix}_{name}_mean_z"] = _mean(values)
    return row


def _target_labels(
    data: WindowPreparedData,
    target_person_i: int,
    target_start: int,
    target_name: str,
) -> dict[str, float]:
    row: dict[str, float] = {}
    summary = _window_summary(
        data,
        target_person_i,
        target_start,
        data.target_len,
        "target",
    )
    if target_name == "cgm":
        for key in ["target_cgm_mean_z", "target_cgm_sd_z", "target_cgm_delta_z"]:
            row[key] = summary.get(key, np.nan)
        delta = row.get("target_cgm_delta_z", np.nan)
        row["target_cgm_rise_event"] = float(delta > 0.5) if np.isfinite(delta) else np.nan
    elif target_name == "wearable":
        for key in [
            "target_hr_mean_z",
            "target_hr_sd_z",
            "target_hr_delta_z",
            "target_steps_mean_z",
            "target_asleep_mean_z",
            "target_calories_mean_z",
        ]:
            row[key] = summary.get(key, np.nan)
    elif target_name == "environment":
        for key in [
            "target_pm25_mean_z",
            "target_temp_mean_z",
            "target_humidity_mean_z",
            "target_screen_mean_z",
            "target_light_total_mean_z",
            "target_light_blue_mean_z",
        ]:
            row[key] = summary.get(key, np.nan)
    return row


def collect_embeddings_and_metadata(
    model,
    loader,
    data: WindowPreparedData,
    device: torch.device,
) -> tuple[np.ndarray, pd.DataFrame, np.ndarray]:
    model.eval()
    embeddings: list[np.ndarray] = []
    feature_rows: list[dict[str, float]] = []
    rows: list[dict[str, Any]] = []

    with torch.no_grad():
        for raw_batch in loader:
            batch = _move_batch(raw_batch, device)
            latent = model.encode_context(batch).detach().cpu().numpy().astype(np.float32)
            embeddings.append(latent)

            idx = raw_batch["indices"].numpy()
            person_idx = raw_batch["person_idx"].numpy()
            target_person_idx = raw_batch["target_person_idx"].numpy()
            context_start = raw_batch["context_start"].numpy()
            target_start = raw_batch["target_start"].numpy()
            target_ids = raw_batch["target_modality_id"].numpy()

            for local_i, window_i in enumerate(idx):
                person_i = int(person_idx[local_i])
                target_person_i = int(target_person_idx[local_i])
                target_name = data.target_names[int(target_ids[local_i])]
                row = {
                    "window_index": int(window_i),
                    "person_id": data.base.ids[person_i],
                    "split": data.window_split[window_i],
                    "event_type": data.event_type[window_i],
                    "study_group": data.base.study_group[person_i],
                    "severity": int(data.base.severity[person_i]),
                    "age": float(data.base.ages[person_i]),
                    "context_start": int(context_start[local_i]),
                    "target_start": int(target_start[local_i]),
                    "target_modality": target_name,
                    "horizon_steps": int(data.horizon),
                    "horizon_minutes": int(data.horizon * 5),
                }
                features = _window_summary(
                    data,
                    person_i,
                    int(context_start[local_i]),
                    data.context_len,
                    "context",
                )
                row.update(_target_labels(data, target_person_i, int(target_start[local_i]), target_name))
                rows.append(row)
                feature_rows.append(features)

    embedding_array = (
        np.concatenate(embeddings, axis=0)
        if embeddings
        else np.zeros((0, 0), dtype=np.float32)
    )
    metadata = pd.DataFrame(rows)
    context_features = np.array(
        pd.DataFrame(feature_rows).to_numpy(dtype=np.float32),
        copy=True,
    )
    context_features[~np.isfinite(context_features)] = 0.0
    return embedding_array, metadata, context_features


def _standardize(train_x: np.ndarray, all_x: np.ndarray) -> np.ndarray:
    mean = train_x.mean(axis=0, keepdims=True)
    std = train_x.std(axis=0, keepdims=True)
    std[(std < 1e-6) | ~np.isfinite(std)] = 1.0
    mean[~np.isfinite(mean)] = 0.0
    scaled = (all_x - mean) / std
    scaled[~np.isfinite(scaled)] = 0.0
    scaled = np.clip(
        scaled,
        -PROBE_STANDARDIZED_FEATURE_CLIP,
        PROBE_STANDARDIZED_FEATURE_CLIP,
    )
    return scaled.astype(np.float64)


def _fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    x_aug = np.concatenate([x, np.ones((x.shape[0], 1), dtype=x.dtype)], axis=1)
    reg = np.eye(x_aug.shape[1], dtype=x_aug.dtype) * alpha
    reg[-1, -1] = 0.0
    lhs = x_aug.T @ x_aug + reg
    rhs = x_aug.T @ y
    try:
        return np.linalg.solve(lhs, rhs)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(lhs) @ rhs


def _predict_ridge(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    x_aug = np.concatenate([x, np.ones((x.shape[0], 1), dtype=x.dtype)], axis=1)
    return x_aug @ weights


def _regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float | int | None]:
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


def _auc_score(y_true: np.ndarray, scores: np.ndarray) -> float | None:
    mask = np.isfinite(y_true) & np.isfinite(scores)
    y = y_true[mask].astype(int)
    s = scores[mask]
    if len(np.unique(y)) < 2:
        return None
    order = np.argsort(s)
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, len(s) + 1)
    pos = y == 1
    n_pos = int(pos.sum())
    n_neg = int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    rank_sum = float(ranks[pos].sum())
    return float((rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def _probe_label(
    x: np.ndarray,
    metadata: pd.DataFrame,
    label: str,
    feature_set: str,
    alpha: float,
) -> dict[str, Any] | None:
    if label not in metadata.columns:
        return None
    y = metadata[label].to_numpy(dtype=np.float64)
    splits = metadata["split"].to_numpy(dtype=str)
    train_mask = (splits == "train") & np.isfinite(y)
    test_mask = (splits == "test") & np.isfinite(y)
    if train_mask.sum() < 10 or test_mask.sum() < 10:
        return None

    x_scaled = _standardize(x[train_mask].astype(np.float64), x.astype(np.float64))
    weights = _fit_ridge(x_scaled[train_mask], y[train_mask], alpha)
    pred = _predict_ridge(x_scaled, weights)

    metrics = _regression_metrics(y[test_mask], pred[test_mask])
    row: dict[str, Any] = {
        "label": label,
        "feature_set": feature_set,
        "train_n": int(train_mask.sum()),
        "test_n": int(test_mask.sum()),
        **{f"test_{key}": value for key, value in metrics.items()},
    }
    finite_y = y[np.isfinite(y)]
    if set(np.unique(finite_y)).issubset({0.0, 1.0}):
        row["test_auc"] = _auc_score(y[test_mask], pred[test_mask])
    return row


def _probe_label_stratified(
    x: np.ndarray,
    metadata: pd.DataFrame,
    label: str,
    feature_set: str,
    alpha: float,
) -> list[dict[str, Any]]:
    if label not in metadata.columns:
        return []
    y = metadata[label].to_numpy(dtype=np.float64)
    splits = metadata["split"].to_numpy(dtype=str)
    train_mask = (splits == "train") & np.isfinite(y)
    test_mask = (splits == "test") & np.isfinite(y)
    if train_mask.sum() < 10 or test_mask.sum() < 10:
        return []

    x_scaled = _standardize(x[train_mask].astype(np.float64), x.astype(np.float64))
    weights = _fit_ridge(x_scaled[train_mask], y[train_mask], alpha)
    pred = _predict_ridge(x_scaled, weights)

    rows: list[dict[str, Any]] = []
    group_specs: list[tuple[str, Any, np.ndarray]] = []
    if "severity" in metadata.columns:
        for severity in sorted(metadata.loc[test_mask, "severity"].dropna().unique()):
            mask = test_mask & (metadata["severity"].to_numpy() == severity)
            group_specs.append(("severity", int(severity), mask))
    if "event_type" in metadata.columns:
        for event_type in sorted(metadata.loc[test_mask, "event_type"].dropna().unique()):
            mask = test_mask & (metadata["event_type"].to_numpy(dtype=str) == str(event_type))
            group_specs.append(("event_type", str(event_type), mask))
    if "target_modality" in metadata.columns:
        for target_modality in sorted(metadata.loc[test_mask, "target_modality"].dropna().unique()):
            mask = test_mask & (
                metadata["target_modality"].to_numpy(dtype=str) == str(target_modality)
            )
            group_specs.append(("target_modality", str(target_modality), mask))

    finite_y = y[np.isfinite(y)]
    is_binary = set(np.unique(finite_y)).issubset({0.0, 1.0})
    for group_type, group_value, mask in group_specs:
        if mask.sum() < 10:
            continue
        metrics = _regression_metrics(y[mask], pred[mask])
        row: dict[str, Any] = {
            "label": label,
            "feature_set": feature_set,
            "group_type": group_type,
            "group_value": group_value,
            "train_n": int(train_mask.sum()),
            "test_n": int(mask.sum()),
            **{f"test_{key}": value for key, value in metrics.items()},
        }
        if is_binary:
            row["test_auc"] = _auc_score(y[mask], pred[mask])
        rows.append(row)
    return rows


def run_physiology_probes(
    model,
    loader,
    data: WindowPreparedData,
    device: torch.device,
    output_dir: Path,
    ridge_alpha: float = 1.0,
    save_embeddings: bool = False,
) -> dict[str, Any]:
    embeddings, metadata, context_features = collect_embeddings_and_metadata(
        model,
        loader,
        data,
        device,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata.to_csv(output_dir / "window_probe_metadata.csv", index=False)
    if save_embeddings:
        np.save(output_dir / "context_embeddings.npy", embeddings)
        np.save(output_dir / "context_summary_features.npy", context_features)

    labels = [
        "target_cgm_mean_z",
        "target_cgm_sd_z",
        "target_cgm_delta_z",
        "target_cgm_rise_event",
        "target_hr_mean_z",
        "target_hr_sd_z",
        "target_hr_delta_z",
        "target_steps_mean_z",
        "target_asleep_mean_z",
        "target_calories_mean_z",
        "target_pm25_mean_z",
        "target_temp_mean_z",
        "target_humidity_mean_z",
        "target_screen_mean_z",
        "target_light_total_mean_z",
        "target_light_blue_mean_z",
    ]
    rows: list[dict[str, Any]] = []
    stratified_rows: list[dict[str, Any]] = []
    for label in labels:
        for feature_set, features in [
            ("jepa_embedding", embeddings),
            ("context_summary", context_features),
        ]:
            row = _probe_label(features, metadata, label, feature_set, ridge_alpha)
            if row is not None:
                rows.append(row)
            stratified_rows.extend(
                _probe_label_stratified(features, metadata, label, feature_set, ridge_alpha)
            )

    metrics = pd.DataFrame(rows)
    metrics.to_csv(output_dir / "physiology_probe_metrics.csv", index=False)
    stratified_metrics = pd.DataFrame(stratified_rows)
    stratified_metrics.to_csv(
        output_dir / "physiology_probe_stratified_metrics.csv",
        index=False,
    )
    return {
        "n_windows": int(len(metadata)),
        "n_embedding_features": int(embeddings.shape[1]) if embeddings.ndim == 2 else 0,
        "n_context_summary_features": int(context_features.shape[1])
        if context_features.ndim == 2
        else 0,
        "ridge_alpha": float(ridge_alpha),
        "standardized_feature_clip": float(PROBE_STANDARDIZED_FEATURE_CLIP),
        "metrics_path": str(output_dir / "physiology_probe_metrics.csv"),
        "stratified_metrics_path": str(
            output_dir / "physiology_probe_stratified_metrics.csv"
        ),
        "metadata_path": str(output_dir / "window_probe_metadata.csv"),
    }
