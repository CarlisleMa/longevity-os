"""Collect JEPA sweep summary.json files into a compact CSV."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def flatten(prefix: str, value: Any, row: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            flatten(f"{prefix}{key}_", nested, row)
    else:
        row[prefix[:-1]] = value


def row_from_summary(path: Path) -> dict[str, Any]:
    summary = json.loads(path.read_text(encoding="utf-8"))
    row: dict[str, Any] = {
        "run_dir": str(path.parent),
        "run_name": path.parent.name,
        "n": summary.get("n"),
    }
    controls = summary.get("controls", {})
    row["drop_modalities"] = ",".join(controls.get("drop_modalities") or [])
    row["shuffle_modalities"] = ",".join(controls.get("shuffle_modalities") or [])
    row["shuffle_scope"] = controls.get("shuffle_scope")

    args = summary.get("args", {})
    for key in [
        "seed",
        "epochs",
        "latent_dim",
        "hidden_dim",
        "jepa_loss_weight",
        "age_loss_weight",
        "severity_loss_weight",
    ]:
        row[key] = args.get(key)

    flatten("all_", summary.get("final_metrics", {}).get("all", {}), row)
    for split, metrics in summary.get("final_metrics", {}).get("by_split", {}).items():
        flatten(f"{split}_", metrics, row)
    return row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sweep_root", help="Directory containing per-run subdirectories.")
    parser.add_argument(
        "--output",
        default=None,
        help="CSV output path. Defaults to <sweep_root>/sweep_summary.csv.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.sweep_root)
    summaries = sorted(root.glob("*/summary.json"))
    if not summaries:
        raise SystemExit(f"No summary.json files found under {root}")

    frame = pd.DataFrame(row_from_summary(path) for path in summaries)
    output = Path(args.output) if args.output else root / "sweep_summary.csv"
    frame.sort_values(["run_name"]).to_csv(output, index=False)
    print(f"Wrote {len(frame)} rows to {output}")


if __name__ == "__main__":
    main()
