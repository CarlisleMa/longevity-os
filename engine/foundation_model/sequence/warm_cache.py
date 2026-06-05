"""Warm the per-participant sequence cache without training a model."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from scripts.config import result_path

from .data import CACHE_VERSION
from .data import _load_or_build_sequences
from .data import _read_required_parquet


def count_cache_versions(cache_dir: Path) -> dict[str, int]:
    counts: Counter[str] = Counter()
    missing = 0
    unreadable = 0
    for path in sorted(cache_dir.glob("*.npz")):
        try:
            with np.load(path, allow_pickle=False) as data:
                counts[str(data["version"])] += 1
        except Exception:
            unreadable += 1
    if missing:
        counts["missing"] = missing
    if unreadable:
        counts["unreadable"] = unreadable
    return dict(counts)


def selected_ids(limit: int | None, seed: int) -> np.ndarray:
    feature_matrix = _read_required_parquet(result_path("feature_matrix.parquet"))
    if limit is not None and limit > 0 and limit < len(feature_matrix):
        rng = np.random.default_rng(seed)
        selected = np.sort(rng.choice(len(feature_matrix), size=limit, replace=False))
        feature_matrix = feature_matrix.iloc[selected].copy()
    return feature_matrix.index.astype(str).to_numpy()


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): to_jsonable(val) for key, val in value.items()}
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default="foundation_jepa/sequence/artifacts/cache_5min_10d")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--skip-version-counts", action="store_true")
    parser.add_argument(
        "--output-json",
        default="foundation_jepa/sequence/artifacts/cache_5min_10d/warm_cache_summary.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    if args.num_shards <= 0:
        raise ValueError("--num-shards must be positive")
    if args.shard_index < 0 or args.shard_index >= args.num_shards:
        raise ValueError("--shard-index must satisfy 0 <= shard_index < num_shards")
    all_ids = selected_ids(args.limit, args.seed)
    ids = all_ids[args.shard_index :: args.num_shards]
    start = time.time()
    before = {} if args.skip_version_counts else count_cache_versions(cache_dir)
    print(
        f"Cache warm start: target_version={CACHE_VERSION} "
        f"participants={len(ids)} shard={args.shard_index}/{args.num_shards} "
        f"before={before}",
        flush=True,
    )

    for i, person_id in enumerate(ids, start=1):
        _load_or_build_sequences(str(person_id), cache_dir=cache_dir, use_cache=True)
        if i % 100 == 0 or i == len(ids):
            elapsed = time.time() - start
            print(
                f"Warmed sequence cache for {i}/{len(ids)} participants "
                f"elapsed_min={elapsed / 60:.1f}",
                flush=True,
            )

    after = {} if args.skip_version_counts else count_cache_versions(cache_dir)
    summary = {
        "target_version": CACHE_VERSION,
        "n_participants": int(len(ids)),
        "n_all_participants": int(len(all_ids)),
        "num_shards": int(args.num_shards),
        "shard_index": int(args.shard_index),
        "cache_dir": str(cache_dir),
        "before": before,
        "after": after,
        "elapsed_seconds": float(time.time() - start),
    }
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as handle:
        json.dump(to_jsonable(summary), handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"Cache warm complete: after={after} summary={output_json}", flush=True)


if __name__ == "__main__":
    main()
