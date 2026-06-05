"""Window sampling wrapper for target-token temporal JEPA.

This module intentionally reuses the split-preserving sampler from
``foundation_jepa.window.data``. V2 changes the objective and model geometry,
not the population/window construction, so controls remain directly comparable
with the existing window JEPA runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from foundation_jepa.window.data import WindowPreparedData
from foundation_jepa.window.data import build_window_data as build_v1_window_data
from foundation_jepa.window.data import split_window_indices as split_v1_window_indices


@dataclass(frozen=True)
class WindowV2PreparedData:
    windows: WindowPreparedData
    patch_len: int
    patch_stride: int
    target_patch_starts: np.ndarray

    @property
    def controls(self) -> dict[str, Any]:
        controls = dict(self.windows.controls)
        controls.update(
            {
                "window_jepa_version": "target_token_v2",
                "patch_len": self.patch_len,
                "patch_stride": self.patch_stride,
                "target_patch_starts": self.target_patch_starts.tolist(),
            }
        )
        return controls


def target_patch_starts(target_len: int, patch_len: int, patch_stride: int) -> np.ndarray:
    if patch_len <= 0 or patch_stride <= 0:
        raise ValueError("patch_len and patch_stride must be positive")
    if target_len < patch_len:
        raise ValueError("target_len must be >= patch_len")
    return np.arange(0, target_len - patch_len + 1, patch_stride, dtype=np.int32)


def _window_coverage(mask: np.ndarray, start: int, length: int) -> float:
    window = mask[start : start + length]
    if window.size == 0:
        return 0.0
    return float(window.mean())


def _post_control_target_coverages(windows: WindowPreparedData) -> np.ndarray:
    coverages = np.zeros(len(windows.person_idx), dtype=np.float32)
    for row_i in range(len(windows.person_idx)):
        target_name = windows.target_names[int(windows.target_modality_id[row_i])]
        target_person_i = int(windows.target_person_idx[row_i])
        target_start = int(windows.target_start[row_i])
        coverages[row_i] = _window_coverage(
            windows.base.sequence_masks[target_name][target_person_i],
            target_start,
            windows.target_len,
        )
    return coverages


def _filter_post_control_target_coverage(
    windows: WindowPreparedData,
    min_target_coverage: float,
) -> WindowPreparedData:
    coverages = _post_control_target_coverages(windows)
    keep = coverages >= min_target_coverage
    dropped = int((~keep).sum())
    controls = dict(windows.controls)
    controls.update(
        {
            "post_control_target_coverage_rechecked": True,
            "post_control_target_coverage_min": float(min_target_coverage),
            "post_control_target_coverage_dropped": dropped,
            "post_control_target_coverage_min_observed": (
                float(coverages.min()) if len(coverages) else None
            ),
        }
    )
    if dropped == 0:
        return WindowPreparedData(
            base=windows.base,
            person_idx=windows.person_idx,
            context_start=windows.context_start,
            target_person_idx=windows.target_person_idx,
            target_start=windows.target_start,
            target_modality_id=windows.target_modality_id,
            event_type=windows.event_type,
            window_split=windows.window_split,
            sequence_names=windows.sequence_names,
            target_names=windows.target_names,
            static_names=windows.static_names,
            context_len=windows.context_len,
            target_len=windows.target_len,
            horizon=windows.horizon,
            stride=windows.stride,
            controls=controls,
        )

    return WindowPreparedData(
        base=windows.base,
        person_idx=windows.person_idx[keep],
        context_start=windows.context_start[keep],
        target_person_idx=windows.target_person_idx[keep],
        target_start=windows.target_start[keep],
        target_modality_id=windows.target_modality_id[keep],
        event_type=windows.event_type[keep],
        window_split=windows.window_split[keep],
        sequence_names=windows.sequence_names,
        target_names=windows.target_names,
        static_names=windows.static_names,
        context_len=windows.context_len,
        target_len=windows.target_len,
        horizon=windows.horizon,
        stride=windows.stride,
        controls=controls,
    )


def build_window_v2_data(
    limit: int | None = None,
    seed: int = 42,
    cache_dir: str | Path | None = "foundation_jepa/sequence/artifacts/cache_5min_10d",
    use_cache: bool = True,
    context_len: int = 24,
    target_len: int = 12,
    horizon: int = 0,
    stride: int = 12,
    target_modalities: list[str] | tuple[str, ...] | None = None,
    max_windows_per_person: int | None = 96,
    min_context_coverage: float = 0.05,
    min_target_coverage: float = 0.25,
    control: str = "aligned",
    include_static: bool = False,
    event_mode: str = "random",
    cgm_rise_threshold: float = 0.5,
    activity_threshold: float = 0.75,
    sleep_change_threshold: float = 0.5,
    event_fallback_random: bool = False,
    patch_len: int = 6,
    patch_stride: int = 3,
) -> WindowV2PreparedData:
    """Build window data and validate target-token geometry."""

    starts = target_patch_starts(target_len, patch_len, patch_stride)
    windows = build_v1_window_data(
        limit=limit,
        seed=seed,
        cache_dir=cache_dir,
        use_cache=use_cache,
        context_len=context_len,
        target_len=target_len,
        horizon=horizon,
        stride=stride,
        target_modalities=target_modalities,
        max_windows_per_person=max_windows_per_person,
        min_context_coverage=min_context_coverage,
        min_target_coverage=min_target_coverage,
        control=control,
        include_static=include_static,
        event_mode=event_mode,
        cgm_rise_threshold=cgm_rise_threshold,
        activity_threshold=activity_threshold,
        sleep_change_threshold=sleep_change_threshold,
        event_fallback_random=event_fallback_random,
    )
    windows = _filter_post_control_target_coverage(
        windows,
        min_target_coverage=min_target_coverage,
    )
    return WindowV2PreparedData(
        windows=windows,
        patch_len=patch_len,
        patch_stride=patch_stride,
        target_patch_starts=starts,
    )


def split_window_indices(data: WindowV2PreparedData) -> dict[str, np.ndarray]:
    return split_v1_window_indices(data.windows)
