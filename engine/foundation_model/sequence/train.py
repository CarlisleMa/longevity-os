"""Train raw 10-day sequence JEPA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset, Subset

from .data import SEQ_LEN, SequencePreparedData, build_sequence_data
from .model import SequenceJEPA


class IndexDataset(Dataset):
    def __init__(self, data: SequencePreparedData) -> None:
        self.data = data

    def __len__(self) -> int:
        return len(self.data.ids)

    def __getitem__(self, index: int) -> int:
        return int(index)


def make_collate(data: SequencePreparedData):
    def collate(indices: list[int]) -> dict[str, Any]:
        idx = np.asarray(indices, dtype=np.int64)
        return {
            "sequences": {
                name: torch.from_numpy(values[idx])
                for name, values in data.sequences.items()
            },
            "sequence_masks": {
                name: torch.from_numpy(values[idx])
                for name, values in data.sequence_masks.items()
            },
            "static": {
                name: torch.from_numpy(values[idx])
                for name, values in data.static.items()
            },
            "availability": {
                name: torch.from_numpy(flags[idx].astype(np.float32))
                for name, flags in data.availability.items()
            },
            "age": torch.from_numpy(data.age_z[idx].astype(np.float32)),
            "age_raw": torch.from_numpy(data.ages[idx].astype(np.float32)),
            "severity": torch.from_numpy(data.severity[idx].astype(np.int64)),
            "indices": torch.from_numpy(idx),
        }

    return collate


def move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {
        "sequences": {
            name: tensor.to(device) for name, tensor in batch["sequences"].items()
        },
        "sequence_masks": {
            name: tensor.to(device) for name, tensor in batch["sequence_masks"].items()
        },
        "static": {
            name: tensor.to(device) for name, tensor in batch["static"].items()
        },
        "availability": {
            name: tensor.to(device) for name, tensor in batch["availability"].items()
        },
        "age": batch["age"].to(device),
        "age_raw": batch["age_raw"].to(device),
        "severity": batch["severity"].to(device),
        "indices": batch["indices"].to(device),
    }


def split_indices(data: SequencePreparedData) -> dict[str, np.ndarray]:
    splits = {}
    for split in ["train", "val", "test"]:
        idx = np.flatnonzero(data.splits == split)
        if len(idx):
            splits[split] = idx
    for split in sorted(set(data.splits) - set(splits)):
        idx = np.flatnonzero(data.splits == split)
        if len(idx):
            splits[split] = idx
    if "train" not in splits:
        splits["train"] = np.arange(len(data.ids), dtype=np.int64)
    return splits


def make_loader(
    dataset: IndexDataset,
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
    model: SequenceJEPA,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    loss_kwargs: dict[str, float],
) -> float:
    model.train()
    total = 0.0
    n = 0
    for raw_batch in loader:
        batch = move_batch(raw_batch, device)
        optimizer.zero_grad(set_to_none=True)
        _, losses = model.losses(batch, **loss_kwargs)
        losses["loss"].backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()

        batch_n = int(raw_batch["indices"].numel())
        total += float(losses["loss"].detach().cpu()) * batch_n
        n += batch_n
    return total / max(n, 1)


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if mask.sum() == 0:
        return {"n": 0, "mae": None, "rmse": None, "r2": None, "corr": None}
    true = y_true[mask]
    pred = y_pred[mask]
    err = pred - true
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err * err)))
    ss_res = float(np.sum(err * err))
    ss_tot = float(np.sum((true - true.mean()) ** 2))
    r2 = None if ss_tot <= 1e-12 else float(1.0 - ss_res / ss_tot)
    if len(true) < 2 or np.std(true) < 1e-12 or np.std(pred) < 1e-12:
        corr = None
    else:
        corr = float(np.corrcoef(true, pred)[0, 1])
    return {"n": int(mask.sum()), "mae": mae, "rmse": rmse, "r2": r2, "corr": corr}


def severity_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    valid = frame["severity"].to_numpy() >= 0
    if valid.sum() == 0:
        return {"severity_n": 0, "severity_acc": None}
    actual = frame.loc[valid, "severity"].to_numpy()
    predicted = frame.loc[valid, "pred_severity"].to_numpy()
    return {
        "severity_n": int(valid.sum()),
        "severity_acc": float(np.mean(actual == predicted)),
    }


def severity_array_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    valid = y_true >= 0
    if valid.sum() == 0:
        return {"severity_n": 0, "severity_acc": None}
    return {
        "severity_n": int(valid.sum()),
        "severity_acc": float(np.mean(y_true[valid] == y_pred[valid])),
    }


@torch.no_grad()
def collect_predictions(
    model: SequenceJEPA,
    loader: DataLoader,
    data: SequencePreparedData,
    device: torch.device,
    loss_kwargs: dict[str, float],
) -> tuple[pd.DataFrame, dict[str, float]]:
    model.eval()
    rows: list[dict[str, Any]] = []
    loss_sums: dict[str, float] = {}
    n = 0
    for raw_batch in loader:
        batch = move_batch(raw_batch, device)
        outputs, losses = model.losses(batch, **loss_kwargs)
        idx = raw_batch["indices"].numpy()
        batch_n = int(len(idx))
        n += batch_n
        for key, value in losses.items():
            loss_sums[key] = loss_sums.get(key, 0.0) + float(value.cpu()) * batch_n

        age_pred_z = outputs["age_pred"].detach().cpu().numpy()
        age_pred = age_pred_z * data.age_std + data.age_mean
        severity_probs = torch.softmax(outputs["severity_logits"], dim=1).cpu().numpy()
        pred_severity = severity_probs.argmax(axis=1)
        severity_score = severity_probs @ np.arange(4, dtype=np.float32)

        for local_i, row_i in enumerate(idx):
            row = {
                "person_id": data.ids[row_i],
                "split": data.splits[row_i],
                "study_group": data.study_group[row_i],
                "age": float(data.ages[row_i]),
                "age_pred": float(age_pred[local_i]),
                "age_pred_z": float(age_pred_z[local_i]),
                "severity": int(data.severity[row_i]),
                "pred_severity": int(pred_severity[local_i]),
                "pred_severity_score": float(severity_score[local_i]),
            }
            for name in data.specs:
                row[f"available_{name}"] = bool(data.availability[name][row_i])
            rows.append(row)

    averaged_losses = {key: value / max(n, 1) for key, value in loss_sums.items()}
    return pd.DataFrame(rows), averaged_losses


@torch.no_grad()
def collect_embeddings(
    model: SequenceJEPA,
    loader: DataLoader,
    data: SequencePreparedData,
    device: torch.device,
) -> tuple[np.ndarray, pd.DataFrame]:
    model.eval()
    embeddings: list[np.ndarray] = []
    rows: list[dict[str, Any]] = []
    for raw_batch in loader:
        batch = move_batch(raw_batch, device)
        outputs = model(batch)
        pooled = outputs["pooled"].detach().cpu().numpy().astype(np.float32)
        idx = raw_batch["indices"].numpy()
        embeddings.append(pooled)
        for local_i, row_i in enumerate(idx):
            row = {
                "person_id": data.ids[row_i],
                "split": data.splits[row_i],
                "study_group": data.study_group[row_i],
                "age": float(data.ages[row_i]),
                "severity": int(data.severity[row_i]),
            }
            for name in data.specs:
                row[f"available_{name}"] = bool(data.availability[name][row_i])
            row["embedding_row"] = int(len(rows))
            rows.append(row)

    if embeddings:
        return np.concatenate(embeddings, axis=0), pd.DataFrame(rows)
    return np.zeros((0, 0), dtype=np.float32), pd.DataFrame(rows)


def evaluate_frame(frame: pd.DataFrame, losses: dict[str, float]) -> dict[str, Any]:
    metrics = regression_metrics(
        frame["age"].to_numpy(dtype=np.float32),
        frame["age_pred"].to_numpy(dtype=np.float32),
    )
    metrics.update(severity_metrics(frame))
    metrics.update({f"loss_{key}": value for key, value in losses.items()})
    return metrics


def _standardize_probe_features(
    train_x: np.ndarray,
    all_x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    mean = train_x.mean(axis=0, keepdims=True)
    std = train_x.std(axis=0, keepdims=True)
    std[(std < 1e-6) | ~np.isfinite(std)] = 1.0
    mean[~np.isfinite(mean)] = 0.0
    standardized = (all_x - mean) / std
    standardized[~np.isfinite(standardized)] = 0.0
    return standardized.astype(np.float64), mean.astype(np.float32), std.astype(np.float32)


def _fit_ridge(
    x: np.ndarray,
    y: np.ndarray,
    alpha: float,
) -> np.ndarray:
    x_aug = np.concatenate(
        [x, np.ones((x.shape[0], 1), dtype=x.dtype)],
        axis=1,
    )
    reg = np.eye(x_aug.shape[1], dtype=x_aug.dtype) * float(alpha)
    reg[-1, -1] = 0.0
    lhs = x_aug.T @ x_aug + reg
    rhs = x_aug.T @ y
    try:
        return np.linalg.solve(lhs, rhs)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(lhs) @ rhs


def _predict_ridge(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    x_aug = np.concatenate(
        [x, np.ones((x.shape[0], 1), dtype=x.dtype)],
        axis=1,
    )
    return x_aug @ weights


def linear_probe_evaluation(
    embeddings: np.ndarray,
    metadata: pd.DataFrame,
    alpha: float = 1.0,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Fit frozen linear probes on train embeddings and evaluate by split."""

    predictions = metadata.copy()
    predictions["probe_age_pred"] = np.nan
    predictions["probe_severity"] = -1

    if len(predictions) == 0 or embeddings.shape[0] != len(predictions):
        return {"ridge_alpha": alpha, "age": {}, "severity": {}}, predictions

    split_values = list(dict.fromkeys(["train", "val", "test"] + sorted(predictions["split"].unique())))
    train_mask = predictions["split"].to_numpy() == "train"

    age = predictions["age"].to_numpy(dtype=np.float32)
    age_train_mask = train_mask & np.isfinite(age)
    if age_train_mask.sum() >= 2:
        x_age, _, _ = _standardize_probe_features(
            embeddings[age_train_mask].astype(np.float64),
            embeddings.astype(np.float64),
        )
        weights = _fit_ridge(x_age[age_train_mask], age[age_train_mask].astype(np.float64), alpha)
        predictions["probe_age_pred"] = _predict_ridge(x_age, weights).astype(np.float32)

    severity = predictions["severity"].to_numpy(dtype=np.int64)
    severity_train_mask = train_mask & (severity >= 0)
    if severity_train_mask.sum() >= 2:
        x_sev, _, _ = _standardize_probe_features(
            embeddings[severity_train_mask].astype(np.float64),
            embeddings.astype(np.float64),
        )
        y_onehot = np.zeros((severity_train_mask.sum(), 4), dtype=np.float64)
        train_labels = severity[severity_train_mask].clip(0, 3)
        y_onehot[np.arange(len(train_labels)), train_labels] = 1.0
        weights = _fit_ridge(x_sev[severity_train_mask], y_onehot, alpha)
        scores = _predict_ridge(x_sev, weights)
        predictions["probe_severity"] = scores.argmax(axis=1).astype(np.int64)

    metrics: dict[str, Any] = {"ridge_alpha": alpha, "age": {}, "severity": {}}
    age_pred = predictions["probe_age_pred"].to_numpy(dtype=np.float32)
    severity_pred = predictions["probe_severity"].to_numpy(dtype=np.int64)
    for split in split_values:
        mask = predictions["split"].to_numpy() == split
        if not mask.any():
            continue
        metrics["age"][split] = regression_metrics(age[mask], age_pred[mask])
        metrics["severity"][split] = severity_array_metrics(severity[mask], severity_pred[mask])

    metrics["age"]["all"] = regression_metrics(age, age_pred)
    metrics["severity"]["all"] = severity_array_metrics(severity, severity_pred)
    return metrics, predictions


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): to_jsonable(val) for key, val in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="foundation_jepa/sequence/artifacts/prototype")
    parser.add_argument("--cache-dir", default="foundation_jepa/sequence/artifacts/cache_5min_10d")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--latent-dim", type=int, default=128)
    parser.add_argument("--model-dim", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--patch-len", type=int, default=24)
    parser.add_argument("--stride", type=int, default=12)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--jepa-loss-weight", type=float, default=1.0)
    parser.add_argument("--age-loss-weight", type=float, default=1.0)
    parser.add_argument("--severity-loss-weight", type=float, default=0.0)
    parser.add_argument("--min-coverage", type=float, default=0.05)
    parser.add_argument("--drop-modalities", nargs="*", default=None)
    parser.add_argument("--shuffle-modalities", nargs="*", default=None)
    parser.add_argument("--linear-probe", action="store_true")
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

    data = build_sequence_data(
        limit=args.limit,
        seed=args.seed,
        cache_dir=args.cache_dir,
        use_cache=not args.no_cache,
        drop_modalities=args.drop_modalities,
        shuffle_modalities=args.shuffle_modalities,
        min_coverage=args.min_coverage,
    )
    dataset = IndexDataset(data)
    collate = make_collate(data)
    splits = split_indices(data)

    sequence_dims = {
        name: spec.n_features
        for name, spec in data.specs.items()
        if spec.kind == "sequence"
    }
    static_dims = {
        name: spec.n_features
        for name, spec in data.specs.items()
        if spec.kind == "static"
    }

    device = torch.device(args.device)
    model = SequenceJEPA(
        sequence_dims=sequence_dims,
        static_dims=static_dims,
        seq_len=SEQ_LEN,
        latent_dim=args.latent_dim,
        model_dim=args.model_dim,
        hidden_dim=args.hidden_dim,
        patch_len=args.patch_len,
        stride=args.stride,
        layers=args.layers,
        heads=args.heads,
        dropout=args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    loss_kwargs = {
        "jepa_loss_weight": args.jepa_loss_weight,
        "age_loss_weight": args.age_loss_weight,
        "severity_loss_weight": args.severity_loss_weight,
    }

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

    history: list[dict[str, Any]] = []
    for epoch in range(1, args.epochs + 1):
        train_loss = train_one_epoch(
            model, loaders["train"], optimizer, device, loss_kwargs
        )
        row: dict[str, Any] = {"epoch": epoch, "train_objective": train_loss}
        for split, loader in loaders.items():
            pred_frame, losses = collect_predictions(
                model, loader, data, device, loss_kwargs
            )
            metrics = evaluate_frame(pred_frame, losses)
            for key, value in metrics.items():
                row[f"{split}_{key}"] = value
        history.append(row)
        print(
            f"epoch={epoch:03d} train_loss={train_loss:.4f} "
            f"val_mae={row.get('val_mae', 'NA')} "
            f"test_mae={row.get('test_mae', 'NA')}",
            flush=True,
        )

    full_loader = make_loader(
        dataset,
        np.arange(len(data.ids), dtype=np.int64),
        collate,
        args.batch_size,
        shuffle=False,
        seed=args.seed,
    )
    predictions, full_losses = collect_predictions(
        model, full_loader, data, device, loss_kwargs
    )
    split_metrics: dict[str, Any] = {}
    for split, loader in loaders.items():
        split_predictions, split_losses = collect_predictions(
            model, loader, data, device, loss_kwargs
        )
        split_metrics[split] = evaluate_frame(split_predictions, split_losses)

    summary = {
        "n": int(len(data.ids)),
        "splits": {split: int(len(indices)) for split, indices in splits.items()},
        "age_mean_train": data.age_mean,
        "age_std_train": data.age_std,
        "controls": data.controls,
        "modalities": {
            name: {
                "kind": spec.kind,
                "n_features": spec.n_features,
                "available_n": int(data.availability[name].sum()),
            }
            for name, spec in data.specs.items()
        },
        "loss_weights": loss_kwargs,
        "args": vars(args),
        "final_metrics": {
            "all": evaluate_frame(predictions, full_losses),
            "by_split": split_metrics,
        },
    }

    if args.linear_probe:
        embeddings, embedding_metadata = collect_embeddings(model, full_loader, data, device)
        probe_metrics, probe_predictions = linear_probe_evaluation(
            embeddings,
            embedding_metadata,
            alpha=args.probe_ridge_alpha,
        )
        summary["linear_probe"] = probe_metrics
        probe_predictions.to_csv(output_dir / "probe_predictions.csv", index=False)
        if args.save_embeddings:
            np.save(output_dir / "pooled_embeddings.npy", embeddings)
            embedding_metadata.to_csv(output_dir / "embedding_metadata.csv", index=False)

    pd.DataFrame(history).to_csv(output_dir / "history.csv", index=False)
    predictions.to_csv(output_dir / "predictions.csv", index=False)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(to_jsonable(summary), handle, indent=2)
        handle.write("\n")

    if args.save_checkpoint:
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "args": vars(args),
                "modalities": {
                    name: {"kind": spec.kind, "columns": spec.columns}
                    for name, spec in data.specs.items()
                },
            },
            output_dir / "model.pt",
        )


if __name__ == "__main__":
    main()
