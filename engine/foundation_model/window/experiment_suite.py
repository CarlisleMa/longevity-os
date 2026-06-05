"""Run and summarize window-level JEPA horizon/control suites."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_OUTPUT_ROOT = "foundation_jepa/window/artifacts/horizon_suite"
DEFAULT_CACHE_DIR = "foundation_jepa/sequence/artifacts/cache_5min_10d"
DEFAULT_CONTROLS = ("aligned", "wrong_day", "participant_shuffle")


def parse_int_list(values: list[str] | None, default: list[int]) -> list[int]:
    if not values:
        return default
    tokens: list[str] = []
    for value in values:
        tokens.extend(part.strip() for part in str(value).split(","))
    parsed = [int(token) for token in tokens if token]
    return parsed or default


def parse_str_list(values: list[str] | None, default: tuple[str, ...]) -> list[str]:
    if not values:
        return list(default)
    tokens: list[str] = []
    for value in values:
        tokens.extend(part.strip() for part in str(value).split(","))
    parsed = [token for token in tokens if token]
    return parsed or list(default)


def add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR)
    parser.add_argument("--seeds", nargs="*", default=["42", "43", "44"])
    parser.add_argument("--horizons", nargs="*", default=["0", "6", "12", "24"])
    parser.add_argument("--controls", nargs="*", default=list(DEFAULT_CONTROLS))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--context-len", type=int, default=24)
    parser.add_argument("--target-len", type=int, default=12)
    parser.add_argument("--window-stride", type=int, default=12)
    parser.add_argument("--max-windows-per-person", type=int, default=64)
    parser.add_argument("--min-context-coverage", type=float, default=0.05)
    parser.add_argument("--min-target-coverage", type=float, default=0.25)
    parser.add_argument("--target-modalities", nargs="*", default=None)
    parser.add_argument(
        "--event-modes",
        nargs="*",
        default=["random"],
        help="Comma/space separated event samplers: random, glucose_rise, activity_bout, sleep_transition, dawn_proxy, mixed_events.",
    )
    parser.add_argument("--cgm-rise-threshold", type=float, default=0.5)
    parser.add_argument("--activity-threshold", type=float, default=0.75)
    parser.add_argument("--sleep-change-threshold", type=float, default=0.5)
    parser.add_argument("--event-fallback-random", action="store_true")
    parser.add_argument("--latent-dim", type=int, default=128)
    parser.add_argument("--model-dim", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--patch-len", type=int, default=12)
    parser.add_argument("--patch-stride", type=int, default=6)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--static-align-weight", type=float, default=0.0)
    parser.add_argument("--contrastive-weight", type=float, default=1.0)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--teacher-tau", type=float, default=0.99)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--save-checkpoint", action="store_true")


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
        "--context-len",
        str(record["context_len"]),
        "--target-len",
        str(record["target_len"]),
        "--horizon",
        str(record["horizon"]),
        "--window-stride",
        str(record["window_stride"]),
        "--max-windows-per-person",
        str(record["max_windows_per_person"]),
        "--min-context-coverage",
        str(record["min_context_coverage"]),
        "--min-target-coverage",
        str(record["min_target_coverage"]),
        "--control",
        record["control"],
        "--event-mode",
        record["event_mode"],
        "--cgm-rise-threshold",
        str(record["cgm_rise_threshold"]),
        "--activity-threshold",
        str(record["activity_threshold"]),
        "--sleep-change-threshold",
        str(record["sleep_change_threshold"]),
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
        "--patch-stride",
        str(record["patch_stride"]),
        "--dropout",
        str(record["dropout"]),
        "--lr",
        str(record["lr"]),
        "--weight-decay",
        str(record["weight_decay"]),
        "--static-align-weight",
        str(record["static_align_weight"]),
        "--contrastive-weight",
        str(record["contrastive_weight"]),
        "--temperature",
        str(record["temperature"]),
        "--teacher-tau",
        str(record["teacher_tau"]),
        "--device",
        record["device"],
    ]
    if record.get("limit") is not None:
        args.extend(["--limit", str(record["limit"])])
    if record.get("target_modalities"):
        args.append("--target-modalities")
        args.extend(record["target_modalities"])
    if record.get("event_fallback_random"):
        args.append("--event-fallback-random")
    if record.get("save_checkpoint"):
        args.append("--save-checkpoint")
    return args


def build_records(args: argparse.Namespace) -> list[dict[str, Any]]:
    seeds = parse_int_list(args.seeds, [42, 43, 44])
    horizons = parse_int_list(args.horizons, [0, 6, 12, 24])
    controls = parse_str_list(args.controls, DEFAULT_CONTROLS)
    event_modes = parse_str_list(args.event_modes, ("random",))
    output_root = Path(args.output_root)
    target_modalities = parse_str_list(args.target_modalities, ()) if args.target_modalities else []

    records: list[dict[str, Any]] = []
    for horizon in horizons:
        for seed in seeds:
            for event_mode in event_modes:
                for control in controls:
                    horizon_minutes = horizon * 5
                    event_prefix = event_mode if event_mode != "random" else "random_windows"
                    record = {
                        "output_root": args.output_root,
                        "cache_dir": args.cache_dir,
                        "seed": seed,
                        "horizon": horizon,
                        "horizon_minutes": horizon_minutes,
                        "control": control,
                        "event_mode": event_mode,
                        "output_dir": str(
                            output_root
                            / event_prefix
                            / f"horizon_{horizon_minutes:03d}min"
                            / f"seed_{seed}"
                            / control
                        ),
                        "limit": args.limit,
                        "epochs": args.epochs,
                        "batch_size": args.batch_size,
                        "context_len": args.context_len,
                        "target_len": args.target_len,
                        "window_stride": args.window_stride,
                        "max_windows_per_person": args.max_windows_per_person,
                        "min_context_coverage": args.min_context_coverage,
                        "min_target_coverage": args.min_target_coverage,
                        "target_modalities": target_modalities,
                        "cgm_rise_threshold": args.cgm_rise_threshold,
                        "activity_threshold": args.activity_threshold,
                        "sleep_change_threshold": args.sleep_change_threshold,
                        "event_fallback_random": args.event_fallback_random,
                        "latent_dim": args.latent_dim,
                        "model_dim": args.model_dim,
                        "hidden_dim": args.hidden_dim,
                        "layers": args.layers,
                        "heads": args.heads,
                        "patch_len": args.patch_len,
                        "patch_stride": args.patch_stride,
                        "dropout": args.dropout,
                        "lr": args.lr,
                        "weight_decay": args.weight_decay,
                        "static_align_weight": args.static_align_weight,
                        "contrastive_weight": args.contrastive_weight,
                        "temperature": args.temperature,
                        "teacher_tau": args.teacher_tau,
                        "device": args.device,
                        "save_checkpoint": args.save_checkpoint,
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
    Path(record["output_dir"]).mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-u", "-m", "foundation_jepa.window.train"]
    command.extend(record.get("train_args") or train_args_for_record(record))
    print(
        "Running "
        f"horizon={record['horizon_minutes']}min seed={record['seed']} "
        f"event={record.get('event_mode', 'random')} "
        f"control={record['control']} -> {record['output_dir']}",
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
    controls = summary.get("controls", {})
    row: dict[str, Any] = {
        "summary_path": str(path),
        "output_dir": output_dir,
        "seed": record.get("seed", summary.get("args", {}).get("seed")),
        "control": record.get("control", controls.get("control")),
        "event_mode": record.get("event_mode", controls.get("event_mode", "random")),
        "horizon": record.get("horizon", controls.get("horizon")),
        "horizon_minutes": record.get(
            "horizon_minutes",
            int(controls.get("horizon", 0)) * 5 if controls.get("horizon") is not None else None,
        ),
        "n_windows": summary.get("n_windows"),
        "n_participants": summary.get("n_participants"),
    }
    for split in ["train", "val", "test"]:
        for key in [
            "jepa",
            "jepa_cgm",
            "jepa_wearable",
            "jepa_environment",
            "jepa_mse_cgm",
            "jepa_mse_wearable",
            "jepa_mse_environment",
            "jepa_contrastive_cgm",
            "jepa_contrastive_wearable",
            "jepa_contrastive_environment",
            "static_align",
        ]:
            row[f"{split}_{key}"] = metric_value(summary, ("final_metrics", split, key))
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

    manifest_parser = subparsers.add_parser("make-manifest")
    add_shared_args(manifest_parser)
    manifest_parser.add_argument(
        "--manifest",
        default="foundation_jepa/window/artifacts/horizon_suite/manifest.jsonl",
    )

    run_one_parser = subparsers.add_parser("run-one")
    run_one_parser.add_argument("--manifest", required=True)
    run_one_parser.add_argument("--index", type=int, required=True)

    summarize_parser = subparsers.add_parser("summarize")
    summarize_parser.add_argument("paths", nargs="*", default=[DEFAULT_OUTPUT_ROOT])
    summarize_parser.add_argument("--manifest", default=None)
    summarize_parser.add_argument(
        "--output-csv",
        default="foundation_jepa/window/artifacts/horizon_suite/summary.csv",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
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
    if args.command == "summarize":
        frame = summarize(
            [Path(path) for path in args.paths],
            Path(args.manifest) if args.manifest else None,
            Path(args.output_csv),
        )
        print(f"Wrote {len(frame)} rows to {args.output_csv}")
        if len(frame):
            columns = [
                "horizon_minutes",
                "seed",
                "control",
                "event_mode",
                "test_jepa",
                "test_jepa_cgm",
                "test_jepa_wearable",
                "test_jepa_environment",
            ]
            print(frame[[col for col in columns if col in frame.columns]].to_string(index=False))
        return


if __name__ == "__main__":
    main()
