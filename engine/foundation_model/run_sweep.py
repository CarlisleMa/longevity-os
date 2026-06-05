"""Run predefined JEPA controls and ablations.

This entrypoint is Slurm-array friendly. Each array task maps to one concrete
training run and writes to a unique directory under foundation_jepa/artifacts/.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_SEEDS = [42, 43, 44]


@dataclass(frozen=True)
class ExperimentSpec:
    name: str
    description: str
    extra_args: list[str] = field(default_factory=list)


BASE_EXPERIMENTS = [
    ExperimentSpec(
        name="full_jepa_age",
        description="All modalities, JEPA plus age objective.",
    ),
    ExperimentSpec(
        name="full_jepa_age_severity",
        description="All modalities, JEPA plus age and diabetes-severity objectives.",
        extra_args=["--severity-loss-weight", "0.2"],
    ),
    ExperimentSpec(
        name="age_only_all_modalities",
        description="All modalities, age objective only; tests whether JEPA adds value.",
        extra_args=["--jepa-loss-weight", "0.0"],
    ),
    ExperimentSpec(
        name="shuffle_all_modalities",
        description="Negative control: shuffle every modality within split.",
        extra_args=["--shuffle-modalities", "all"],
    ),
    ExperimentSpec(
        name="shuffle_imaging",
        description="Negative control: break retinal/cardiac alignment only.",
        extra_args=["--shuffle-modalities", "retinal", "cardiac"],
    ),
    ExperimentSpec(
        name="shuffle_wearable_cgm_env",
        description="Negative control: break synchronized wearable/CGM/environment alignment.",
        extra_args=["--shuffle-modalities", "wearable", "cgm", "environment"],
    ),
    ExperimentSpec(
        name="drop_clinical",
        description="Ablation: remove clinical labs/questionnaires to test non-clinical signal.",
        extra_args=["--drop-modalities", "clinical"],
    ),
    ExperimentSpec(
        name="drop_retinal",
        description="Ablation: remove RETFound retinal embeddings.",
        extra_args=["--drop-modalities", "retinal"],
    ),
    ExperimentSpec(
        name="drop_cardiac",
        description="Ablation: remove ECGFounder cardiac embeddings.",
        extra_args=["--drop-modalities", "cardiac"],
    ),
    ExperimentSpec(
        name="drop_cgm",
        description="Ablation: remove CGM summary features.",
        extra_args=["--drop-modalities", "cgm"],
    ),
    ExperimentSpec(
        name="drop_wearable",
        description="Ablation: remove wearable summary features.",
        extra_args=["--drop-modalities", "wearable"],
    ),
    ExperimentSpec(
        name="drop_environment",
        description="Ablation: remove environment summary features.",
        extra_args=["--drop-modalities", "environment"],
    ),
]


def parse_seeds(raw: str | None) -> list[int]:
    if not raw:
        return list(DEFAULT_SEEDS)
    return [int(token) for token in raw.replace(",", " ").split()]


def build_manifest(seeds: list[int]) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for seed in seeds:
        for spec in BASE_EXPERIMENTS:
            manifest.append(
                {
                    "name": f"{spec.name}_seed{seed}",
                    "base_name": spec.name,
                    "seed": seed,
                    "description": spec.description,
                    "extra_args": list(spec.extra_args),
                }
            )
    return manifest


def command_for_run(args: argparse.Namespace, run: dict[str, Any]) -> list[str]:
    output_dir = Path(args.output_root) / run["name"]
    command = [
        sys.executable,
        "-m",
        "foundation_jepa.train",
        "--output-dir",
        str(output_dir),
        "--seed",
        str(run["seed"]),
        "--epochs",
        str(args.epochs),
        "--batch-size",
        str(args.batch_size),
        "--latent-dim",
        str(args.latent_dim),
        "--hidden-dim",
        str(args.hidden_dim),
        "--dropout",
        str(args.dropout),
        "--lr",
        str(args.lr),
        "--weight-decay",
        str(args.weight_decay),
        "--jepa-loss-weight",
        str(args.jepa_loss_weight),
        "--age-loss-weight",
        str(args.age_loss_weight),
        "--severity-loss-weight",
        str(args.severity_loss_weight),
        "--device",
        args.device,
    ]
    if args.limit is not None:
        command.extend(["--limit", str(args.limit)])
    command.extend(run["extra_args"])
    return command


def write_manifest(manifest: list[dict[str, Any]], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    pd.DataFrame(manifest).to_csv(output_root / "manifest.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="foundation_jepa/artifacts/sweeps/manual")
    parser.add_argument("--seeds", default=os.environ.get("JEPA_SEEDS"))
    parser.add_argument("--array-index", type=int, default=None)
    parser.add_argument("--run-all", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--latent-dim", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--jepa-loss-weight", type=float, default=1.0)
    parser.add_argument("--age-loss-weight", type=float, default=1.0)
    parser.add_argument("--severity-loss-weight", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seeds = parse_seeds(args.seeds)
    manifest = build_manifest(seeds)
    output_root = Path(args.output_root)
    write_manifest(manifest, output_root)

    if args.list:
        for idx, run in enumerate(manifest):
            print(f"{idx:03d}\t{run['name']}\t{run['description']}")
        return

    array_index = args.array_index
    if array_index is None and "SLURM_ARRAY_TASK_ID" in os.environ:
        array_index = int(os.environ["SLURM_ARRAY_TASK_ID"])

    if args.run_all:
        selected = list(enumerate(manifest))
    elif array_index is not None:
        if array_index < 0 or array_index >= len(manifest):
            raise SystemExit(
                f"Array index {array_index} outside manifest size {len(manifest)}"
            )
        selected = [(array_index, manifest[array_index])]
    else:
        raise SystemExit("Provide --array-index, set SLURM_ARRAY_TASK_ID, or use --run-all")

    for idx, run in selected:
        command = command_for_run(args, run)
        output_dir = Path(args.output_root) / run["name"]
        output_dir.mkdir(parents=True, exist_ok=True)
        with (output_dir / "run_metadata.json").open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "array_index": idx,
                    "run": run,
                    "command": command,
                    "command_string": shlex.join(command),
                },
                handle,
                indent=2,
            )
            handle.write("\n")

        print(f"[{idx:03d}] {run['name']}")
        print(shlex.join(command))
        if not args.dry_run:
            subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
