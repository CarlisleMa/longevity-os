"""Run physiology probes from a saved window-JEPA checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .data import build_window_data
from .model import WindowJEPA
from .probes import run_physiology_probes
from .train import WindowIndexDataset, make_collate, make_loader, to_jsonable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--probe-ridge-alpha", type=float, default=None)
    parser.add_argument("--save-embeddings", action="store_true")
    return parser.parse_args()


def _arg(saved_args: dict[str, Any], name: str, default: Any = None) -> Any:
    return saved_args.get(name, default)


def main() -> None:
    args = parse_args()
    checkpoint_path = Path(args.checkpoint)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    saved_args = dict(checkpoint.get("args", {}))
    seed = int(_arg(saved_args, "seed", 42))
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.backends.cuda.matmul.allow_tf32 = True

    data = build_window_data(
        limit=_arg(saved_args, "limit"),
        seed=seed,
        cache_dir=_arg(saved_args, "cache_dir", "foundation_jepa/sequence/artifacts/cache_5min_10d"),
        use_cache=not bool(_arg(saved_args, "no_cache", False)),
        context_len=int(_arg(saved_args, "context_len", 24)),
        target_len=int(_arg(saved_args, "target_len", 12)),
        horizon=int(_arg(saved_args, "horizon", 0)),
        stride=int(_arg(saved_args, "window_stride", 12)),
        target_modalities=_arg(saved_args, "target_modalities"),
        max_windows_per_person=int(_arg(saved_args, "max_windows_per_person", 96)),
        min_context_coverage=float(_arg(saved_args, "min_context_coverage", 0.05)),
        min_target_coverage=float(_arg(saved_args, "min_target_coverage", 0.25)),
        control=str(_arg(saved_args, "control", "aligned")),
        include_static=not bool(_arg(saved_args, "no_static", False)),
        event_mode=str(_arg(saved_args, "event_mode", "random")),
        cgm_rise_threshold=float(_arg(saved_args, "cgm_rise_threshold", 0.5)),
        activity_threshold=float(_arg(saved_args, "activity_threshold", 0.75)),
        sleep_change_threshold=float(_arg(saved_args, "sleep_change_threshold", 0.5)),
        event_fallback_random=bool(_arg(saved_args, "event_fallback_random", False)),
    )
    if len(data.person_idx) == 0:
        raise ValueError("No valid windows were sampled")

    sequence_dims = {
        name: data.base.specs[name].n_features
        for name in data.sequence_names
    }
    static_dims = {
        name: data.base.specs[name].n_features
        for name in data.static_names
    }
    device = torch.device(args.device)
    model = WindowJEPA(
        sequence_dims=sequence_dims,
        static_dims=static_dims,
        max_len=max(int(_arg(saved_args, "context_len", 24)), int(_arg(saved_args, "target_len", 12))),
        target_names=data.target_names,
        latent_dim=int(_arg(saved_args, "latent_dim", 128)),
        model_dim=int(_arg(saved_args, "model_dim", 128)),
        hidden_dim=int(_arg(saved_args, "hidden_dim", 256)),
        patch_len=int(_arg(saved_args, "patch_len", 12)),
        stride=int(_arg(saved_args, "patch_stride", 6)),
        layers=int(_arg(saved_args, "layers", 2)),
        heads=int(_arg(saved_args, "heads", 4)),
        dropout=float(_arg(saved_args, "dropout", 0.1)),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])

    dataset = WindowIndexDataset(data)
    loader = make_loader(
        dataset,
        np.arange(len(data.person_idx), dtype=np.int64),
        make_collate(data),
        args.batch_size or int(_arg(saved_args, "batch_size", 256)),
        shuffle=False,
        seed=seed,
    )
    probe_summary = run_physiology_probes(
        model=model,
        loader=loader,
        data=data,
        device=device,
        output_dir=output_dir,
        ridge_alpha=float(args.probe_ridge_alpha or _arg(saved_args, "probe_ridge_alpha", 1.0)),
        save_embeddings=args.save_embeddings,
    )
    summary = {
        "checkpoint": str(checkpoint_path),
        "n_windows": int(len(data.person_idx)),
        "n_participants": int(len(data.base.ids)),
        "event_counts": {
            str(event_type): int((data.event_type == event_type).sum())
            for event_type in sorted(set(data.event_type.astype(str)))
        },
        "controls": data.controls,
        "checkpoint_args": saved_args,
        "physiology_probes": probe_summary,
    }
    with (output_dir / "probe_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(to_jsonable(summary), handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
