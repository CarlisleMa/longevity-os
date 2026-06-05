"""Combine sharded coupling feature parquet files and run basic validation."""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

import pandas as pd

from scripts.config import RESULTS_DIR, result_path


DEFAULT_GLOB = str(RESULTS_DIR / "shards" / "coupling_features" / "coupling_features_*.parquet")
DEFAULT_OUTPUT = result_path("coupling_features.parquet")


def combine_shards(input_glob: str = DEFAULT_GLOB, output: Path = DEFAULT_OUTPUT) -> pd.DataFrame:
    paths = [Path(p) for p in sorted(glob.glob(input_glob))]
    if not paths:
        raise FileNotFoundError(f"No shard files matched {input_glob}")

    frames = []
    for path in paths:
        df = pd.read_parquet(path)
        if "person_id" in df.columns:
            df = df.set_index("person_id")
        df.index = df.index.astype(str)
        frames.append(df)

    combined = pd.concat(frames, axis=0)
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output)
    print(f"Combined {len(paths)} shards into {combined.shape[0]} x {combined.shape[1]} at {output}")
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-glob", type=str, default=DEFAULT_GLOB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    combine_shards(args.input_glob, args.output)


if __name__ == "__main__":
    main()
