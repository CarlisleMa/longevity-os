"""Train window-level temporal JEPA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset, Subset

from .data import WindowPreparedData, build_window_data, split_window_indices
from .model import WindowJEPA


class WindowIndexDataset(Dataset):
    def __init__(self, data: WindowPreparedData) -> None:
        self.data = data

    def __len__(self) -> int:
        return len(self.data.person_idx)

    def __getitem__(self, index: int) -> int:
        return int(index)


def make_collate(data: WindowPreparedData):
    def collate(indices: list[int]) -> dict[str, Any]:
        idx = np.asarray(indices, dtype=np.int64)
        person_idx = data.person_idx[idx]
        target_person_idx = data.target_person_idx[idx]
        context_start = data.context_start[idx]
        target_start = data.target_start[idx]
        target_modality_id = data.target_modality_id[idx]

        context_values: dict[str, list[np.ndarray]] = {name: [] for name in data.sequence_names}
        context_masks: dict[str, list[np.ndarray]] = {name: [] for name in data.sequence_names}
        target_values: dict[str, list[np.ndarray]] = {name: [] for name in data.target_names}
        target_masks: dict[str, list[np.ndarray]] = {name: [] for name in data.target_names}

        for local_i, window_i in enumerate(idx):
            person_i = int(person_idx[local_i])
            target_person_i = int(target_person_idx[local_i])
            c_start = int(context_start[local_i])
            t_start = int(target_start[local_i])
            target_id = int(target_modality_id[local_i])
            target_name = data.target_names[target_id]

            for name in data.sequence_names:
                context_values[name].append(
                    data.base.sequences[name][person_i, c_start : c_start + data.context_len]
                )
                context_masks[name].append(
                    data.base.sequence_masks[name][person_i, c_start : c_start + data.context_len]
                )

            for name in data.target_names:
                n_features = data.base.sequences[name].shape[-1]
                if name == target_name:
                    target_values[name].append(
                        data.base.sequences[name][
                            target_person_i, t_start : t_start + data.target_len
                        ]
                    )
                    target_masks[name].append(
                        data.base.sequence_masks[name][
                            target_person_i, t_start : t_start + data.target_len
                        ]
                    )
                else:
                    target_values[name].append(
                        np.zeros((data.target_len, n_features), dtype=np.float32)
                    )
                    target_masks[name].append(
                        np.zeros((data.target_len, n_features), dtype=np.float32)
                    )

        batch: dict[str, Any] = {
            "context_values": {
                name: torch.from_numpy(np.stack(values).astype(np.float32))
                for name, values in context_values.items()
            },
            "context_masks": {
                name: torch.from_numpy(np.stack(values).astype(np.float32))
                for name, values in context_masks.items()
            },
            "target_values": {
                name: torch.from_numpy(np.stack(values).astype(np.float32))
                for name, values in target_values.items()
            },
            "target_masks": {
                name: torch.from_numpy(np.stack(values).astype(np.float32))
                for name, values in target_masks.items()
            },
            "target_modality_id": torch.from_numpy(target_modality_id.astype(np.int64)),
            "person_idx": torch.from_numpy(person_idx.astype(np.int64)),
            "target_person_idx": torch.from_numpy(target_person_idx.astype(np.int64)),
            "context_start": torch.from_numpy(context_start.astype(np.int64)),
            "target_start": torch.from_numpy(target_start.astype(np.int64)),
            "indices": torch.from_numpy(idx.astype(np.int64)),
            "event_type": data.event_type[idx],
        }

        batch["static"] = {
            name: torch.from_numpy(data.base.static[name][person_idx].astype(np.float32))
            for name in data.static_names
        }
        batch["static_availability"] = {
            name: torch.from_numpy(
                data.base.availability[name][person_idx].astype(np.float32)
            )
            for name in data.static_names
        }
        return batch

    return collate


def move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    moved = {
        "context_values": {
            name: tensor.to(device) for name, tensor in batch["context_values"].items()
        },
        "context_masks": {
            name: tensor.to(device) for name, tensor in batch["context_masks"].items()
        },
        "target_values": {
            name: tensor.to(device) for name, tensor in batch["target_values"].items()
        },
        "target_masks": {
            name: tensor.to(device) for name, tensor in batch["target_masks"].items()
        },
        "target_modality_id": batch["target_modality_id"].to(device),
        "person_idx": batch["person_idx"].to(device),
        "target_person_idx": batch["target_person_idx"].to(device),
        "context_start": batch["context_start"].to(device),
        "target_start": batch["target_start"].to(device),
        "indices": batch["indices"].to(device),
        "event_type": batch["event_type"],
        "static": {name: tensor.to(device) for name, tensor in batch["static"].items()},
        "static_availability": {
            name: tensor.to(device)
            for name, tensor in batch["static_availability"].items()
        },
    }
    return moved


def make_loader(
    dataset: WindowIndexDataset,
    indices: np.ndarray,
    collate,
    batch_size: int,
    shuffle: bool,
    seed: int,
) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        Subset(dataset, indices.tolist()),
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=collate,
        generator=generator,
        num_workers=0,
    )


def train_one_epoch(
    model: WindowJEPA,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    loss_kwargs: dict[str, float],
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
    model: WindowJEPA,
    loader: DataLoader,
    device: torch.device,
    loss_kwargs: dict[str, float],
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


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): to_jsonable(val) for key, val in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="foundation_jepa/window/artifacts/prototype")
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
    parser.add_argument("--no-static", action="store_true")
    parser.add_argument("--latent-dim", type=int, default=128)
    parser.add_argument("--model-dim", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--patch-len", type=int, default=12)
    parser.add_argument("--patch-stride", type=int, default=6)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--jepa-loss-weight", type=float, default=1.0)
    parser.add_argument("--static-align-weight", type=float, default=0.0)
    parser.add_argument("--contrastive-weight", type=float, default=1.0)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--teacher-tau", type=float, default=0.99)
    parser.add_argument("--physiology-probes", action="store_true")
    parser.add_argument("--probe-ridge-alpha", type=float, default=1.0)
    parser.add_argument("--save-embeddings", action="store_true")
    parser.add_argument("--save-checkpoint", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = build_window_data(
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
        include_static=not args.no_static,
        event_mode=args.event_mode,
        cgm_rise_threshold=args.cgm_rise_threshold,
        activity_threshold=args.activity_threshold,
        sleep_change_threshold=args.sleep_change_threshold,
        event_fallback_random=args.event_fallback_random,
    )
    if len(data.person_idx) == 0:
        raise ValueError("No valid windows were sampled")

    dataset = WindowIndexDataset(data)
    collate = make_collate(data)
    splits = split_window_indices(data)
    loaders = {
        split: make_loader(
            dataset,
            indices,
            collate,
            args.batch_size,
            shuffle=(split == "train"),
            seed=args.seed,
        )
        for split, indices in splits.items()
    }

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
        max_len=max(args.context_len, args.target_len),
        target_names=data.target_names,
        latent_dim=args.latent_dim,
        model_dim=args.model_dim,
        hidden_dim=args.hidden_dim,
        patch_len=args.patch_len,
        stride=args.patch_stride,
        layers=args.layers,
        heads=args.heads,
        dropout=args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=args.lr,
        weight_decay=args.weight_decay,
    )
    loss_kwargs = {
        "jepa_loss_weight": args.jepa_loss_weight,
        "static_align_weight": args.static_align_weight,
        "contrastive_weight": args.contrastive_weight,
        "temperature": args.temperature,
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
            f"train_loss={train_losses.get('loss', float('nan')):.4f} "
            f"val_jepa={row.get('val_jepa', 'NA')} "
            f"test_jepa={row.get('test_jepa', 'NA')}",
            flush=True,
        )

    final_metrics = {
        split: evaluate(model, loader, device, loss_kwargs)
        for split, loader in loaders.items()
    }
    full_loader = make_loader(
        dataset,
        np.arange(len(data.person_idx), dtype=np.int64),
        collate,
        args.batch_size,
        shuffle=False,
        seed=args.seed,
    )
    summary = {
        "n_windows": int(len(data.person_idx)),
        "n_participants": int(len(data.base.ids)),
        "window_splits": {split: int(len(indices)) for split, indices in splits.items()},
        "event_counts": {
            str(event_type): int((data.event_type == event_type).sum())
            for event_type in sorted(set(data.event_type.astype(str)))
        },
        "participant_splits": {
            split: int((data.base.splits == split).sum())
            for split in sorted(set(data.base.splits.astype(str)))
        },
        "sequence_modalities": list(data.sequence_names),
        "target_modalities": list(data.target_names),
        "static_modalities": list(data.static_names),
        "controls": data.controls,
        "loss_weights": loss_kwargs,
        "args": vars(args),
        "final_metrics": final_metrics,
    }

    if args.physiology_probes or args.save_embeddings:
        from .probes import run_physiology_probes

        summary["physiology_probes"] = run_physiology_probes(
            model=model,
            loader=full_loader,
            data=data,
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
                "sequence_modalities": list(data.sequence_names),
                "target_modalities": list(data.target_names),
                "static_modalities": list(data.static_names),
            },
            output_dir / "model.pt",
        )


if __name__ == "__main__":
    main()
