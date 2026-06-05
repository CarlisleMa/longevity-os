"""Run and summarize next-stage sequence JEPA experiments."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_CACHE_DIR = "foundation_jepa/sequence/artifacts/cache_5min_10d"
DEFAULT_OUTPUT_ROOT = "foundation_jepa/sequence/artifacts/next_stage"


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    description: str
    drop_modalities: tuple[str, ...] = ()
    shuffle_modalities: tuple[str, ...] = ()
    jepa_loss_weight: float = 1.0
    age_loss_weight: float = 1.0
    severity_loss_weight: float | None = None


CORE_CONFIGS = (
    ExperimentConfig(
        name="full_joint",
        description="All modalities aligned; JEPA plus aging-clock and severity heads.",
    ),
    ExperimentConfig(
        name="shuffle_all_joint",
        description="All modalities shuffled within split as a negative control.",
        shuffle_modalities=("all",),
    ),
    ExperimentConfig(
        name="shuffle_sequences_joint",
        description="Only CGM/wearable/environment sequences shuffled; static modalities stay aligned.",
        shuffle_modalities=("cgm", "wearable", "environment"),
    ),
    ExperimentConfig(
        name="drop_clinical_joint",
        description="Clinical table removed; tests dependence on tabular clinical shortcuts.",
        drop_modalities=("clinical",),
    ),
    ExperimentConfig(
        name="drop_imaging_joint",
        description="RETFound and ECGFounder embeddings removed.",
        drop_modalities=("retinal", "cardiac"),
    ),
    ExperimentConfig(
        name="sequence_only_joint",
        description="Only 10-day CGM/wearable/environment streams retained.",
        drop_modalities=("clinical", "retinal", "cardiac"),
    ),
    ExperimentConfig(
        name="static_only_joint",
        description="Only clinical/retinal/cardiac static modalities retained.",
        drop_modalities=("cgm", "wearable", "environment"),
    ),
)

OBJECTIVE_CONFIGS = (
    ExperimentConfig(
        name="full_pure_jepa",
        description="All modalities aligned; no supervised age or severity loss.",
        age_loss_weight=0.0,
        severity_loss_weight=0.0,
    ),
    ExperimentConfig(
        name="sequence_only_pure_jepa",
        description="Sequence-only JEPA; no supervised age or severity loss.",
        drop_modalities=("clinical", "retinal", "cardiac"),
        age_loss_weight=0.0,
        severity_loss_weight=0.0,
    ),
    ExperimentConfig(
        name="full_age_only",
        description="Supervised age/severity baseline with no JEPA alignment loss.",
        jepa_loss_weight=0.0,
    ),
)

SUITES = {
    "core": CORE_CONFIGS,
    "objective": OBJECTIVE_CONFIGS,
    "next_stage": CORE_CONFIGS + OBJECTIVE_CONFIGS,
}


def parse_int_list(values: list[str] | None) -> list[int]:
    if not values:
        return [42, 43, 44]
    tokens: list[str] = []
    for value in values:
        tokens.extend(part.strip() for part in value.split(","))
    return [int(token) for token in tokens if token]


def add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--suite", choices=sorted(SUITES), default="next_stage")
    parser.add_argument("--seeds", nargs="*", default=["42", "43", "44"])
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--latent-dim", type=int, default=128)
    parser.add_argument("--model-dim", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--patch-len", type=int, default=24)
    parser.add_argument("--stride", type=int, default=12)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--severity-loss-weight", type=float, default=0.2)
    parser.add_argument("--probe-ridge-alpha", type=float, default=1.0)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--save-checkpoint", action="store_true")
    parser.add_argument("--save-embeddings", action="store_true")


def train_args_for_record(record: dict[str, Any]) -> list[str]:
    args = [
        "--output-dir",
        record["output_dir"],
        "--cache-dir",
        record["cache_dir"],
        "--seed",
        str(record["seed"]),
        "--epochs",
        str(record["epochs"]),
        "--batch-size",
        str(record["batch_size"]),
        "--latent-dim",
        str(record["latent_dim"]),
        "--model-dim",
        str(record["model_dim"]),
        "--hidden-dim",
        str(record["hidden_dim"]),
        "--layers",
        str(record["layers"]),
        "--heads",
        str(record["heads"]),
        "--patch-len",
        str(record["patch_len"]),
        "--stride",
        str(record["stride"]),
        "--dropout",
        str(record["dropout"]),
        "--lr",
        str(record["lr"]),
        "--weight-decay",
        str(record["weight_decay"]),
        "--jepa-loss-weight",
        str(record["jepa_loss_weight"]),
        "--age-loss-weight",
        str(record["age_loss_weight"]),
        "--severity-loss-weight",
        str(record["severity_loss_weight"]),
        "--probe-ridge-alpha",
        str(record["probe_ridge_alpha"]),
        "--device",
        record["device"],
        "--linear-probe",
    ]
    if record.get("limit") is not None:
        args.extend(["--limit", str(record["limit"])])
    if record["drop_modalities"]:
        args.append("--drop-modalities")
        args.extend(record["drop_modalities"])
    if record["shuffle_modalities"]:
        args.append("--shuffle-modalities")
        args.extend(record["shuffle_modalities"])
    if record.get("save_checkpoint"):
        args.append("--save-checkpoint")
    if record.get("save_embeddings"):
        args.append("--save-embeddings")
    return args


def build_records(args: argparse.Namespace) -> list[dict[str, Any]]:
    seeds = parse_int_list(args.seeds)
    output_root = Path(args.output_root)
    records: list[dict[str, Any]] = []
    for config in SUITES[args.suite]:
        for seed in seeds:
            severity_weight = (
                args.severity_loss_weight
                if config.severity_loss_weight is None
                else config.severity_loss_weight
            )
            record = {
                "suite": args.suite,
                "config": config.name,
                "description": config.description,
                "seed": seed,
                "output_dir": str(output_root / config.name / f"seed_{seed}"),
                "cache_dir": args.cache_dir,
                "limit": args.limit,
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "latent_dim": args.latent_dim,
                "model_dim": args.model_dim,
                "hidden_dim": args.hidden_dim,
                "layers": args.layers,
                "heads": args.heads,
                "patch_len": args.patch_len,
                "stride": args.stride,
                "dropout": args.dropout,
                "lr": args.lr,
                "weight_decay": args.weight_decay,
                "jepa_loss_weight": config.jepa_loss_weight,
                "age_loss_weight": config.age_loss_weight,
                "severity_loss_weight": severity_weight,
                "probe_ridge_alpha": args.probe_ridge_alpha,
                "drop_modalities": list(config.drop_modalities),
                "shuffle_modalities": list(config.shuffle_modalities),
                "device": args.device,
                "save_checkpoint": args.save_checkpoint,
                "save_embeddings": args.save_embeddings,
            }
            record["train_args"] = train_args_for_record(record)
            records.append(record)
    return records


def write_manifest(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")


def read_manifest(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def run_record(record: dict[str, Any]) -> None:
    output_dir = Path(record["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-u", "-m", "foundation_jepa.sequence.train"]
    command.extend(record.get("train_args") or train_args_for_record(record))
    print(
        f"Running {record['config']} seed={record['seed']} -> {record['output_dir']}",
        flush=True,
    )
    subprocess.run(command, check=True)


def metric_value(summary: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = summary
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def summary_row(path: Path, manifest_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summary = json.loads(path.read_text(encoding="utf-8"))
    output_dir = str(path.parent)
    record = manifest_lookup.get(output_dir, {})
    args = summary.get("args", {})
    controls = summary.get("controls", {})
    row: dict[str, Any] = {
        "suite": record.get("suite"),
        "config": record.get("config", path.parent.name),
        "seed": record.get("seed", args.get("seed")),
        "summary_path": str(path),
        "n": summary.get("n"),
        "drop_modalities": ",".join(controls.get("drop_modalities", [])),
        "shuffle_modalities": ",".join(controls.get("shuffle_modalities", [])),
        "jepa_loss_weight": metric_value(summary, ("loss_weights", "jepa_loss_weight")),
        "age_loss_weight": metric_value(summary, ("loss_weights", "age_loss_weight")),
        "severity_loss_weight": metric_value(summary, ("loss_weights", "severity_loss_weight")),
    }
    for split in ["train", "val", "test"]:
        prefix = ("final_metrics", "by_split", split)
        row[f"{split}_age_mae"] = metric_value(summary, prefix + ("mae",))
        row[f"{split}_age_r2"] = metric_value(summary, prefix + ("r2",))
        row[f"{split}_age_corr"] = metric_value(summary, prefix + ("corr",))
        row[f"{split}_severity_acc"] = metric_value(summary, prefix + ("severity_acc",))
        row[f"{split}_probe_age_mae"] = metric_value(summary, ("linear_probe", "age", split, "mae"))
        row[f"{split}_probe_age_r2"] = metric_value(summary, ("linear_probe", "age", split, "r2"))
        row[f"{split}_probe_severity_acc"] = metric_value(
            summary, ("linear_probe", "severity", split, "severity_acc")
        )
    return row


def summarize(paths: list[Path], manifest_path: Path | None, output_csv: Path) -> pd.DataFrame:
    manifest_lookup: dict[str, dict[str, Any]] = {}
    if manifest_path is not None and manifest_path.exists():
        for record in read_manifest(manifest_path):
            manifest_lookup[str(Path(record["output_dir"]))] = record

    summary_paths: list[Path] = []
    for path in paths:
        if path.is_file() and path.name == "summary.json":
            summary_paths.append(path)
        elif path.is_dir():
            summary_paths.extend(sorted(path.glob("**/summary.json")))
    rows = [
        summary_row(path, manifest_lookup)
        for path in sorted(set(summary_paths), key=lambda item: str(item))
    ]
    frame = pd.DataFrame(rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False)
    return frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available suites.")
    list_parser.add_argument("--suite", choices=sorted(SUITES), default=None)

    manifest_parser = subparsers.add_parser("make-manifest", help="Write a JSONL run manifest.")
    add_shared_args(manifest_parser)
    manifest_parser.add_argument(
        "--manifest",
        default="foundation_jepa/sequence/artifacts/next_stage/manifest.jsonl",
    )

    run_one_parser = subparsers.add_parser("run-one", help="Run one manifest row by index.")
    run_one_parser.add_argument("--manifest", required=True)
    run_one_parser.add_argument("--index", type=int, required=True)

    run_all_parser = subparsers.add_parser("run-all", help="Run all suite rows sequentially.")
    add_shared_args(run_all_parser)

    summarize_parser = subparsers.add_parser("summarize", help="Aggregate summary JSON files.")
    summarize_parser.add_argument(
        "paths",
        nargs="*",
        default=[DEFAULT_OUTPUT_ROOT],
        help="Summary JSON files or directories to scan.",
    )
    summarize_parser.add_argument("--manifest", default=None)
    summarize_parser.add_argument(
        "--output-csv",
        default="foundation_jepa/sequence/artifacts/next_stage/summary.csv",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "list":
        suites = [args.suite] if args.suite else sorted(SUITES)
        for suite in suites:
            print(f"{suite}:")
            for config in SUITES[suite]:
                print(f"  {config.name}: {config.description}")
        return

    if args.command == "make-manifest":
        records = build_records(args)
        write_manifest(records, Path(args.manifest))
        print(f"Wrote {len(records)} runs to {args.manifest}")
        return

    if args.command == "run-one":
        records = read_manifest(Path(args.manifest))
        if args.index < 0 or args.index >= len(records):
            raise IndexError(f"Manifest index {args.index} outside 0..{len(records) - 1}")
        run_record(records[args.index])
        return

    if args.command == "run-all":
        for record in build_records(args):
            run_record(record)
        return

    if args.command == "summarize":
        frame = summarize(
            [Path(path) for path in args.paths],
            Path(args.manifest) if args.manifest else None,
            Path(args.output_csv),
        )
        print(f"Wrote {len(frame)} rows to {args.output_csv}")
        if len(frame):
            columns = [
                "config",
                "seed",
                "test_age_mae",
                "test_probe_age_mae",
                "test_severity_acc",
                "test_probe_severity_acc",
            ]
            print(frame[[col for col in columns if col in frame.columns]].to_string(index=False))
        return


if __name__ == "__main__":
    main()
