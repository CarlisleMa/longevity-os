"""Window sampling for temporal physiology JEPA."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from foundation_jepa.sequence.data import SEQ_LEN, SequencePreparedData, build_sequence_data


SEQUENCE_MODALITIES = ("cgm", "wearable", "environment")


@dataclass(frozen=True)
class WindowPreparedData:
    base: SequencePreparedData
    person_idx: np.ndarray
    context_start: np.ndarray
    target_person_idx: np.ndarray
    target_start: np.ndarray
    target_modality_id: np.ndarray
    event_type: np.ndarray
    window_split: np.ndarray
    sequence_names: tuple[str, ...]
    target_names: tuple[str, ...]
    static_names: tuple[str, ...]
    context_len: int
    target_len: int
    horizon: int
    stride: int
    controls: dict[str, Any]


def _expand_selection(
    selected: list[str] | tuple[str, ...] | None,
    available: tuple[str, ...],
    argument_name: str,
) -> tuple[str, ...]:
    if not selected:
        return available
    requested: list[str] = []
    for item in selected:
        for token in str(item).split(","):
            token = token.strip()
            if token:
                requested.append(token)
    if "all" in requested:
        return available
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise ValueError(f"Unknown {argument_name}: {unknown}. Available: {available}")
    return tuple(name for name in available if name in set(requested))


def _window_coverage(mask: np.ndarray, start: int, length: int) -> float:
    window = mask[start : start + length]
    if window.size == 0:
        return 0.0
    return float(window.mean())


def _sample_starts(
    starts: np.ndarray,
    max_windows_per_person: int | None,
    rng: np.random.Generator,
) -> np.ndarray:
    if max_windows_per_person is None or max_windows_per_person <= 0:
        return starts
    if len(starts) <= max_windows_per_person:
        return starts
    selected = rng.choice(len(starts), size=max_windows_per_person, replace=False)
    return np.sort(starts[selected])


def _finite_mean(values: np.ndarray, mask: np.ndarray) -> float:
    valid = mask.astype(bool) & np.isfinite(values)
    if valid.sum() == 0:
        return np.nan
    return float(values[valid].mean())


def _window_channel_mean(
    values: np.ndarray,
    masks: np.ndarray,
    start: int,
    length: int,
    channel: int,
) -> float:
    return _finite_mean(
        values[start : start + length, channel],
        masks[start : start + length, channel],
    )


def _window_channel_delta(
    values: np.ndarray,
    masks: np.ndarray,
    start: int,
    length: int,
    channel: int,
) -> float:
    mid = max(length // 2, 1)
    first = _window_channel_mean(values, masks, start, mid, channel)
    second = _window_channel_mean(values, masks, start + mid, length - mid, channel)
    if not np.isfinite(first) or not np.isfinite(second):
        return np.nan
    return float(second - first)


def _event_candidate_starts(
    base: SequencePreparedData,
    person_i: int,
    candidate_starts: np.ndarray,
    context_len: int,
    target_len: int,
    horizon: int,
    event_mode: str,
    cgm_rise_threshold: float,
    activity_threshold: float,
    sleep_change_threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    if event_mode == "random":
        return candidate_starts, np.asarray(["random"] * len(candidate_starts), dtype=object)

    selected: list[int] = []
    event_types: list[str] = []

    modes = (
        ["glucose_rise", "activity_bout", "sleep_transition", "dawn_proxy"]
        if event_mode == "mixed_events"
        else [event_mode]
    )

    for context_start in candidate_starts:
        target_start = int(context_start + context_len + horizon)
        for mode in modes:
            keep = False
            if mode == "glucose_rise" and "cgm" in base.sequences:
                cgm = base.sequences["cgm"][person_i]
                mask = base.sequence_masks["cgm"][person_i]
                target_delta = _window_channel_delta(cgm, mask, target_start, target_len, 0)
                context_mean = _window_channel_mean(cgm, mask, context_start, context_len, 0)
                target_mean = _window_channel_mean(cgm, mask, target_start, target_len, 0)
                mean_shift = (
                    target_mean - context_mean
                    if np.isfinite(target_mean) and np.isfinite(context_mean)
                    else np.nan
                )
                keep = (
                    np.isfinite(target_delta)
                    and target_delta >= cgm_rise_threshold
                ) or (
                    np.isfinite(mean_shift)
                    and mean_shift >= cgm_rise_threshold
                )
            elif mode == "activity_bout" and "wearable" in base.sequences:
                wearable = base.sequences["wearable"][person_i]
                mask = base.sequence_masks["wearable"][person_i]
                steps = _window_channel_mean(wearable, mask, context_start, context_len, 1)
                calories = _window_channel_mean(wearable, mask, context_start, context_len, 3)
                keep = (
                    np.isfinite(steps)
                    and steps >= activity_threshold
                ) or (
                    np.isfinite(calories)
                    and calories >= activity_threshold
                )
            elif mode == "sleep_transition" and "wearable" in base.sequences:
                wearable = base.sequences["wearable"][person_i]
                mask = base.sequence_masks["wearable"][person_i]
                context_delta = _window_channel_delta(
                    wearable, mask, context_start, context_len, 2
                )
                target_delta = _window_channel_delta(
                    wearable, mask, target_start, target_len, 2
                )
                keep = (
                    np.isfinite(context_delta)
                    and abs(context_delta) >= sleep_change_threshold
                ) or (
                    np.isfinite(target_delta)
                    and abs(target_delta) >= sleep_change_threshold
                )
            elif mode == "dawn_proxy":
                # The sequence cache currently does not persist absolute clock time.
                # This is a daily-position proxy rather than true local dawn.
                target_in_day = target_start % (24 * 12)
                keep = 5 * 12 <= target_in_day < 9 * 12
            else:
                raise ValueError(
                    "Unknown event_mode. Expected random, glucose_rise, "
                    "activity_bout, sleep_transition, dawn_proxy, or mixed_events"
                )

            if keep:
                selected.append(int(context_start))
                event_types.append(mode)

    if not selected:
        return (
            np.asarray([], dtype=np.int32),
            np.asarray([], dtype=object),
        )
    return np.asarray(selected, dtype=np.int32), np.asarray(event_types, dtype=object)


def _apply_participant_shuffle(
    person_idx: np.ndarray,
    target_start: np.ndarray,
    target_modality_id: np.ndarray,
    window_split: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    shuffled_person = person_idx.copy()
    shuffled_start = target_start.copy()
    for split in sorted(set(window_split.astype(str))):
        for target_id in sorted(set(target_modality_id.tolist())):
            idx = np.flatnonzero(
                (window_split == split) & (target_modality_id == target_id)
            )
            if len(idx) < 2:
                continue
            permuted = idx.copy()
            rng.shuffle(permuted)
            shuffled_person[idx] = person_idx[permuted]
            shuffled_start[idx] = target_start[permuted]
    return shuffled_person, shuffled_start


def _apply_wrong_day_shift(
    person_idx: np.ndarray,
    target_start: np.ndarray,
    target_len: int,
    shift_steps: int,
) -> tuple[np.ndarray, np.ndarray]:
    shifted = target_start + shift_steps
    too_late = shifted + target_len > SEQ_LEN
    shifted[too_late] = target_start[too_late] - shift_steps
    too_early = shifted < 0
    shifted[too_early] = target_start[too_early]
    return person_idx.copy(), shifted.astype(np.int32)


def build_window_data(
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
    include_static: bool = True,
    event_mode: str = "random",
    cgm_rise_threshold: float = 0.5,
    activity_threshold: float = 0.75,
    sleep_change_threshold: float = 0.5,
    event_fallback_random: bool = False,
) -> WindowPreparedData:
    """Build a split-preserving table of aligned context/target windows."""

    if context_len <= 0 or target_len <= 0 or stride <= 0:
        raise ValueError("context_len, target_len, and stride must be positive")
    if horizon < 0:
        raise ValueError("horizon must be non-negative")
    last_context_start = SEQ_LEN - context_len - horizon - target_len
    if last_context_start < 0:
        raise ValueError("context_len + horizon + target_len exceeds sequence length")

    base = build_sequence_data(
        limit=limit,
        seed=seed,
        cache_dir=cache_dir,
        use_cache=use_cache,
        drop_modalities=None,
        shuffle_modalities=None,
    )

    sequence_names = tuple(name for name in SEQUENCE_MODALITIES if name in base.sequences)
    if len(sequence_names) < 2:
        raise ValueError("Window JEPA requires at least two temporal modalities")
    target_names = _expand_selection(target_modalities, sequence_names, "target_modalities")
    if not target_names:
        raise ValueError("At least one target modality is required")
    static_names = tuple(base.static) if include_static else ()

    rng = np.random.default_rng(seed)
    target_to_id = {name: i for i, name in enumerate(target_names)}

    person_rows: list[int] = []
    context_rows: list[int] = []
    target_start_rows: list[int] = []
    target_id_rows: list[int] = []
    event_type_rows: list[str] = []
    split_rows: list[str] = []

    candidate_starts = np.arange(0, last_context_start + 1, stride, dtype=np.int32)
    for person_i in range(len(base.ids)):
        starts, start_event_types = _event_candidate_starts(
            base=base,
            person_i=person_i,
            candidate_starts=candidate_starts,
            context_len=context_len,
            target_len=target_len,
            horizon=horizon,
            event_mode=event_mode,
            cgm_rise_threshold=cgm_rise_threshold,
            activity_threshold=activity_threshold,
            sleep_change_threshold=sleep_change_threshold,
        )
        if len(starts) == 0 and event_fallback_random:
            starts = candidate_starts
            start_event_types = np.asarray(
                [f"{event_mode}_fallback_random"] * len(starts),
                dtype=object,
            )
        selected = _sample_starts(
            np.arange(len(starts), dtype=np.int32),
            max_windows_per_person,
            rng,
        )
        starts = starts[selected]
        start_event_types = start_event_types[selected]
        split = str(base.splits[person_i])
        for context_start, event_type in zip(starts, start_event_types, strict=False):
            context_valid = 0.0
            context_size = 0
            for name in sequence_names:
                mask = base.sequence_masks[name][person_i]
                context_valid += float(mask[context_start : context_start + context_len].sum())
                context_size += int(mask[context_start : context_start + context_len].size)
            context_coverage = context_valid / max(context_size, 1)
            if context_coverage < min_context_coverage:
                continue

            target_start = int(context_start + context_len + horizon)
            for target_name in target_names:
                target_cov = _window_coverage(
                    base.sequence_masks[target_name][person_i],
                    target_start,
                    target_len,
                )
                if target_cov < min_target_coverage:
                    continue
                person_rows.append(person_i)
                context_rows.append(int(context_start))
                target_start_rows.append(target_start)
                target_id_rows.append(target_to_id[target_name])
                event_type_rows.append(str(event_type))
                split_rows.append(split)

    person_idx = np.asarray(person_rows, dtype=np.int32)
    context_start_arr = np.asarray(context_rows, dtype=np.int32)
    target_start_arr = np.asarray(target_start_rows, dtype=np.int32)
    target_modality_id = np.asarray(target_id_rows, dtype=np.int16)
    event_type_arr = np.asarray(event_type_rows, dtype=str)
    window_split = np.asarray(split_rows, dtype=str)

    target_person_idx = person_idx.copy()
    if control == "aligned":
        pass
    elif control == "participant_shuffle":
        target_person_idx, target_start_arr = _apply_participant_shuffle(
            person_idx,
            target_start_arr,
            target_modality_id,
            window_split,
            seed + 1009,
        )
    elif control == "wrong_day":
        target_person_idx, target_start_arr = _apply_wrong_day_shift(
            person_idx,
            target_start_arr,
            target_len,
            shift_steps=24 * 12,
        )
    else:
        raise ValueError(
            "Unknown control. Expected one of: aligned, participant_shuffle, wrong_day"
        )

    return WindowPreparedData(
        base=base,
        person_idx=person_idx,
        context_start=context_start_arr,
        target_person_idx=target_person_idx,
        target_start=target_start_arr,
        target_modality_id=target_modality_id,
        event_type=event_type_arr,
        window_split=window_split,
        sequence_names=sequence_names,
        target_names=target_names,
        static_names=static_names,
        context_len=context_len,
        target_len=target_len,
        horizon=horizon,
        stride=stride,
        controls={
            "control": control,
            "context_len": context_len,
            "target_len": target_len,
            "horizon": horizon,
            "stride": stride,
            "target_modalities": list(target_names),
            "max_windows_per_person": max_windows_per_person,
            "min_context_coverage": min_context_coverage,
            "min_target_coverage": min_target_coverage,
            "include_static": include_static,
            "event_mode": event_mode,
            "cgm_rise_threshold": cgm_rise_threshold,
            "activity_threshold": activity_threshold,
            "sleep_change_threshold": sleep_change_threshold,
            "event_fallback_random": event_fallback_random,
        },
    )


def split_window_indices(data: WindowPreparedData) -> dict[str, np.ndarray]:
    splits: dict[str, np.ndarray] = {}
    for split in ["train", "val", "test"]:
        idx = np.flatnonzero(data.window_split == split)
        if len(idx):
            splits[split] = idx
    for split in sorted(set(data.window_split.astype(str)) - set(splits)):
        idx = np.flatnonzero(data.window_split == split)
        if len(idx):
            splits[split] = idx
    if "train" not in splits and len(data.person_idx):
        splits["train"] = np.arange(len(data.person_idx), dtype=np.int64)
    return splits
