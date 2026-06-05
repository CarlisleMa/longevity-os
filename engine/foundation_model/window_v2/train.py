"""Train target-token window JEPA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from foundation_jepa.window.train import WindowIndexDataset
from foundation_jepa.window.train import make_collate
from foundation_jepa.window.train import make_loader
from foundation_jepa.window.train import move_batch
from foundation_jepa.window.train import to_jsonable

from .data import WindowV2PreparedData, build_window_v2_data, split_window_indices
from .model import WindowV2JEPA


def _format_metric(value: Any) -> str:
    if isinstance(value, (float, int, np.floating, np.integer)):
        return f"{float(value):.4f}"
    return "NA"


def train_one_epoch(
    model: WindowV2JEPA,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    loss_kwargs: dict[str, Any],
    teacher_tau: float,
) -> dict[str, float]:
    model.train()
    sums: dict[str, float] = {}
    n = 0
    for raw_batch in loader:
        batch = move_batch(raw_batch, device)
        optimizer.zero_grad(set_to_none=True)
        _, losses = model.losses(batch, **loss_kwargs)
        losses["loss"].backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()
        model.update_teacher(teacher_tau)

        batch_n = int(raw_batch["indices"].numel())
        n += batch_n
        for key, value in losses.items():
            sums[key] = sums.get(key, 0.0) + float(value.detach().cpu()) * batch_n
    return {key: value / max(n, 1) for key, value in sums.items()}


@torch.no_grad()
def evaluate(
    model: WindowV2JEPA,
    loader: DataLoader,
    device: torch.device,
    loss_kwargs: dict[str, Any],
) -> dict[str, float]:
    model.eval()
    sums: dict[str, float] = {}
    n = 0
    target_counts: dict[str, int] = {name: 0 for name in model.target_names}
    for raw_batch in loader:
        batch = move_batch(raw_batch, device)
        _, losses = model.losses(batch, **loss_kwargs)
        batch_n = int(raw_batch["indices"].numel())
        n += batch_n
        for key, value in losses.items():
            sums[key] = sums.get(key, 0.0) + float(value.detach().cpu()) * batch_n
        target_ids = raw_batch["target_modality_id"].numpy()
        for target_i, target_name in enumerate(model.target_names):
            target_counts[target_name] += int((target_ids == target_i).sum())

    averaged = {key: value / max(n, 1) for key, value in sums.items()}
    averaged["n_windows"] = float(n)
    for name, count in target_counts.items():
        averaged[f"n_target_{name}"] = float(count)
    return averaged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="foundation_jepa/window_v2/artifacts/prototype")
    parser.add_argument("--cache-dir", default="foundation_jepa/sequence/artifacts/cache_5min_10d")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--context-len", type=int, default=24)
    parser.add_argument("--target-len", type=int, default=12)
    parser.add_argument("--horizon", type=int, default=0)
    parser.add_argument("--window-stride", type=int, default=12)
    parser.add_argument("--max-windows-per-person", type=int, default=96)
    parser.add_argument("--min-context-coverage", type=float, default=0.05)
    parser.add_argument("--min-target-coverage", type=float, default=0.25)
    parser.add_argument(
        "--target-modalities",
        nargs="*",
        default=None,
        help="Target temporal modalities. Defaults to all temporal modalities.",
    )
    parser.add_argument(
        "--control",
        choices=["aligned", "participant_shuffle", "wrong_day"],
        default="aligned",
    )
    parser.add_argument(
        "--event-mode",
        choices=[
            "random",
            "glucose_rise",
            "activity_bout",
            "sleep_transition",
            "dawn_proxy",
            "mixed_events",
        ],
        default="random",
    )
    parser.add_argument("--cgm-rise-threshold", type=float, default=0.5)
    parser.add_argument("--activity-threshold", type=float, default=0.75)
    parser.add_argument("--sleep-change-threshold", type=float, default=0.5)
    parser.add_argument("--event-fallback-random", action="store_true")
    parser.add_argument(
        "--include-static",
        action="store_true",
        help="Carry static tensors through batches for compatibility; they are not used by v2 pretraining.",
    )
    parser.add_argument("--latent-dim", type=int, default=128)
    parser.add_argument("--model-dim", type=int, default=128)
    parser.add_argument("--patch-len", type=int, default=6)
    parser.add_argument("--patch-stride", type=int, default=3)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--predictor-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--jepa-loss-weight", type=float, default=1.0)
    parser.add_argument("--variance-weight", type=float, default=0.0)
    parser.add_argument("--loss-type", choices=["smooth_l1", "mse"], default="smooth_l1")
    parser.add_argument("--teacher-tau", type=float, default=0.99)
    parser.add_argument("--physiology-probes", action="store_true")
    parser.add_argument("--probe-ridge-alpha", type=float, default=1.0)
    parser.add_argument("--save-embeddings", action="store_true")
    parser.add_argument("--save-checkpoint", action="store_true")
    return parser.parse_args()


def build_loaders(
    data: WindowV2PreparedData,
    batch_size: int,
    seed: int,
) -> tuple[dict[str, DataLoader], DataLoader]:
    dataset = WindowIndexDataset(data.windows)
    collate = make_collate(data.windows)
    splits = split_window_indices(data)
    loaders = {
        split: make_loader(
            dataset,
            indices,
            collate,
            batch_size,
            shuffle=(split == "train"),
            seed=seed,
        )
        for split, indices in splits.items()
    }
    full_loader = make_loader(
        dataset,
        np.arange(len(data.windows.person_idx), dtype=np.int64),
        collate,
        batch_size,
        shuffle=False,
        seed=seed,
    )
    return loaders, full_loader


def main() -> None:
    args = parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = build_window_v2_data(
        limit=args.limit,
        seed=args.seed,
        cache_dir=args.cache_dir,
        use_cache=not args.no_cache,
        context_len=args.context_len,
        target_len=args.target_len,
        horizon=args.horizon,
        stride=args.window_stride,
        target_modalities=args.target_modalities,
        max_windows_per_person=args.max_windows_per_person,
        min_context_coverage=args.min_context_coverage,
        min_target_coverage=args.min_target_coverage,
        control=args.control,
        include_static=args.include_static,
        event_mode=args.event_mode,
        cgm_rise_threshold=args.cgm_rise_threshold,
        activity_threshold=args.activity_threshold,
        sleep_change_threshold=args.sleep_change_threshold,
        event_fallback_random=args.event_fallback_random,
        patch_len=args.patch_len,
        patch_stride=args.patch_stride,
    )
    windows = data.windows
    if len(windows.person_idx) == 0:
        raise ValueError("No valid windows were sampled")

    loaders, full_loader = build_loaders(data, args.batch_size, args.seed)
    sequence_dims = {
        name: windows.base.specs[name].n_features
        for name in windows.sequence_names
    }
    device = torch.device(args.device)
    model = WindowV2JEPA(
        sequence_dims=sequence_dims,
        context_len=windows.context_len,
        target_len=windows.target_len,
        target_names=windows.target_names,
        latent_dim=args.latent_dim,
        model_dim=args.model_dim,
        patch_len=args.patch_len,
        stride=args.patch_stride,
        layers=args.layers,
        heads=args.heads,
        predictor_layers=args.predictor_layers,
        dropout=args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=args.lr,
        weight_decay=args.weight_decay,
    )
    loss_kwargs: dict[str, Any] = {
        "jepa_loss_weight": args.jepa_loss_weight,
        "variance_weight": args.variance_weight,
        "loss_type": args.loss_type,
    }

    history: list[dict[str, Any]] = []
    for epoch in range(1, args.epochs + 1):
        train_losses = train_one_epoch(
            model,
            loaders["train"],
            optimizer,
            device,
            loss_kwargs,
            teacher_tau=args.teacher_tau,
        )
        row: dict[str, Any] = {
            "epoch": epoch,
            **{f"train_{key}": value for key, value in train_losses.items()},
        }
        for split, loader in loaders.items():
            metrics = evaluate(model, loader, device, loss_kwargs)
            for key, value in metrics.items():
                row[f"{split}_{key}"] = value
        history.append(row)
        print(
            f"epoch={epoch:03d} "
            f"train_loss={_format_metric(train_losses.get('loss'))} "
            f"val_jepa={_format_metric(row.get('val_jepa'))} "
            f"test_jepa={_format_metric(row.get('test_jepa'))}",
            flush=True,
        )

    final_metrics = {
        split: evaluate(model, loader, device, loss_kwargs)
        for split, loader in loaders.items()
    }
    splits = split_window_indices(data)
    summary = {
        "version": "window_v2_target_token_jepa",
        "n_windows": int(len(windows.person_idx)),
        "n_participants": int(len(windows.base.ids)),
        "window_splits": {split: int(len(indices)) for split, indices in splits.items()},
        "event_counts": {
            str(event_type): int((windows.event_type == event_type).sum())
            for event_type in sorted(set(windows.event_type.astype(str)))
        },
        "participant_splits": {
            split: int((windows.base.splits == split).sum())
            for split in sorted(set(windows.base.splits.astype(str)))
        },
        "sequence_modalities": list(windows.sequence_names),
        "target_modalities": list(windows.target_names),
        "static_modalities": list(windows.static_names),
        "controls": data.controls,
        "objective": {
            "student_view": "context temporal patch tokens",
            "teacher_view": "target-window patch tokens for the held-out target modality",
            "teacher_update": "EMA",
            "labels_in_pretraining": False,
            "contrastive_loss": False,
            "loss_kwargs": loss_kwargs,
        },
        "args": vars(args),
        "final_metrics": final_metrics,
    }

    if args.physiology_probes or args.save_embeddings:
        from foundation_jepa.window.probes import run_physiology_probes

        summary["physiology_probes"] = run_physiology_probes(
            model=model,
            loader=full_loader,
            data=windows,
            device=device,
            output_dir=output_dir,
            ridge_alpha=args.probe_ridge_alpha,
            save_embeddings=args.save_embeddings,
        )

    pd.DataFrame(history).to_csv(output_dir / "history.csv", index=False)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(to_jsonable(summary), handle, indent=2)
        handle.write("\n")

    if args.save_checkpoint:
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "args": vars(args),
                "version": "window_v2_target_token_jepa",
                "sequence_modalities": list(windows.sequence_names),
                "target_modalities": list(windows.target_names),
                "context_len": int(windows.context_len),
                "target_len": int(windows.target_len),
                "patch_len": int(args.patch_len),
                "patch_stride": int(args.patch_stride),
            },
            output_dir / "model.pt",
        )


if __name__ == "__main__":
    main()

