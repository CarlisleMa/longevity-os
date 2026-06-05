"""Window-level temporal JEPA model."""

from __future__ import annotations

import copy

import torch
from torch import nn
from torch.nn import functional as F


def in_batch_contrastive_loss(
    predicted: torch.Tensor,
    target: torch.Tensor,
    temperature: float,
) -> torch.Tensor:
    if predicted.shape[0] < 2:
        return predicted.sum() * 0.0
    pred_norm = F.normalize(predicted, dim=-1)
    target_norm = F.normalize(target, dim=-1)
    logits = pred_norm @ target_norm.T / max(temperature, 1e-6)
    labels = torch.arange(predicted.shape[0], device=predicted.device)
    return F.cross_entropy(logits, labels)


class MLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
            nn.LayerNorm(output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class PatchEmbed(nn.Module):
    def __init__(
        self,
        n_channels: int,
        model_dim: int,
        patch_len: int,
        stride: int,
    ) -> None:
        super().__init__()
        self.patch_len = patch_len
        self.stride = stride
        self.proj = nn.Linear(n_channels * 2 * patch_len, model_dim)

    def forward(
        self,
        values: torch.Tensor,
        masks: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        x = torch.cat([values, masks.float()], dim=-1)
        patches = x.unfold(dimension=1, size=self.patch_len, step=self.stride)
        patches = patches.transpose(2, 3).contiguous()
        patches = patches.reshape(patches.shape[0], patches.shape[1], -1)

        point_valid = masks.any(dim=-1).float()
        patch_valid = point_valid.unfold(1, self.patch_len, self.stride).any(dim=-1)
        no_valid = ~patch_valid.any(dim=1)
        if no_valid.any():
            patch_valid = patch_valid.clone()
            patch_valid[no_valid, 0] = True

        return self.proj(patches), patch_valid


class TemporalBackbone(nn.Module):
    """Shared transformer over modality-specific temporal patch embeddings."""

    def __init__(
        self,
        sequence_dims: dict[str, int],
        max_len: int,
        latent_dim: int = 128,
        model_dim: int = 128,
        patch_len: int = 12,
        stride: int = 6,
        layers: int = 2,
        heads: int = 4,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if max_len < patch_len:
            raise ValueError("max_len must be >= patch_len")
        self.sequence_names = list(sequence_dims)
        self.name_to_id = {name: i for i, name in enumerate(self.sequence_names)}
        self.patch_embeds = nn.ModuleDict(
            {
                name: PatchEmbed(n_channels, model_dim, patch_len, stride)
                for name, n_channels in sequence_dims.items()
            }
        )
        max_patches = 1 + (max_len - patch_len) // stride
        self.pos_emb = nn.Parameter(torch.zeros(1, max_patches, model_dim))
        self.modality_emb = nn.Embedding(len(self.sequence_names), model_dim)

        layer = nn.TransformerEncoderLayer(
            d_model=model_dim,
            nhead=heads,
            dim_feedforward=model_dim * 4,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=layers)
        self.norm = nn.LayerNorm(model_dim)
        self.out = nn.Sequential(
            nn.Linear(model_dim, latent_dim),
            nn.LayerNorm(latent_dim),
        )
        nn.init.normal_(self.pos_emb, std=0.02)
        nn.init.normal_(self.modality_emb.weight, std=0.02)

    def encode(
        self,
        values: dict[str, torch.Tensor],
        masks: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        token_parts = []
        valid_parts = []
        for name in self.sequence_names:
            if name not in values:
                continue
            tokens, valid = self.patch_embeds[name](values[name], masks[name])
            modality_id = torch.full(
                (tokens.shape[0], tokens.shape[1]),
                self.name_to_id[name],
                dtype=torch.long,
                device=tokens.device,
            )
            tokens = (
                tokens
                + self.pos_emb[:, : tokens.shape[1]]
                + self.modality_emb(modality_id)
            )
            token_parts.append(tokens)
            valid_parts.append(valid)

        if not token_parts:
            raise ValueError("No temporal modalities were provided")

        encoded = torch.cat(token_parts, dim=1)
        valid_tokens = torch.cat(valid_parts, dim=1)
        no_valid = ~valid_tokens.any(dim=1)
        if no_valid.any():
            valid_tokens = valid_tokens.clone()
            valid_tokens[no_valid, 0] = True

        encoded = self.transformer(encoded, src_key_padding_mask=~valid_tokens)
        weights = valid_tokens.float().unsqueeze(-1)
        pooled = (encoded * weights).sum(dim=1) / weights.sum(dim=1).clamp_min(1.0)
        return self.out(self.norm(pooled))


class WindowJEPA(nn.Module):
    def __init__(
        self,
        sequence_dims: dict[str, int],
        static_dims: dict[str, int],
        max_len: int,
        target_names: tuple[str, ...],
        latent_dim: int = 128,
        model_dim: int = 128,
        hidden_dim: int = 256,
        patch_len: int = 12,
        stride: int = 6,
        layers: int = 2,
        heads: int = 4,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.sequence_names = list(sequence_dims)
        self.target_names = list(target_names)
        self.context_encoder = TemporalBackbone(
            sequence_dims=sequence_dims,
            max_len=max_len,
            latent_dim=latent_dim,
            model_dim=model_dim,
            patch_len=patch_len,
            stride=stride,
            layers=layers,
            heads=heads,
            dropout=dropout,
        )
        self.target_encoder = copy.deepcopy(self.context_encoder)
        for parameter in self.target_encoder.parameters():
            parameter.requires_grad_(False)

        self.target_query = nn.Embedding(len(self.target_names), latent_dim)
        self.predictors = nn.ModuleDict(
            {
                name: MLP(latent_dim * 2, hidden_dim, latent_dim, dropout)
                for name in self.target_names
            }
        )
        self.static_projectors = nn.ModuleDict(
            {
                name: MLP(n_features, hidden_dim, latent_dim, dropout)
                for name, n_features in static_dims.items()
            }
        )

    @torch.no_grad()
    def update_teacher(self, tau: float = 0.99) -> None:
        for teacher, student in zip(
            self.target_encoder.parameters(),
            self.context_encoder.parameters(),
            strict=True,
        ):
            teacher.data.mul_(tau).add_(student.data, alpha=1.0 - tau)

    def encode_context(self, batch: dict[str, object]) -> torch.Tensor:
        return self.context_encoder.encode(batch["context_values"], batch["context_masks"])

    def losses(
        self,
        batch: dict[str, object],
        jepa_loss_weight: float = 1.0,
        static_align_weight: float = 0.0,
        contrastive_weight: float = 1.0,
        temperature: float = 0.1,
    ) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        context_latent = self.encode_context(batch)
        outputs: dict[str, torch.Tensor] = {"context_latent": context_latent}

        target_ids = batch["target_modality_id"].long()
        jepa_terms = []
        losses: dict[str, torch.Tensor] = {}
        zero = context_latent.sum() * 0.0

        for target_i, target_name in enumerate(self.target_names):
            mask = target_ids == target_i
            if not mask.any():
                continue

            target_values = {
                target_name: batch["target_values"][target_name][mask],
            }
            target_masks = {
                target_name: batch["target_masks"][target_name][mask],
            }
            with torch.no_grad():
                target_latent = self.target_encoder.encode(target_values, target_masks)

            query = self.target_query(
                torch.full(
                    (int(mask.sum()),),
                    target_i,
                    dtype=torch.long,
                    device=context_latent.device,
                )
            )
            predicted = self.predictors[target_name](
                torch.cat([context_latent[mask], query], dim=-1)
            )
            mse_term = F.mse_loss(
                F.normalize(predicted, dim=-1),
                F.normalize(target_latent, dim=-1),
            )
            contrastive_term = in_batch_contrastive_loss(
                predicted,
                target_latent,
                temperature=temperature,
            )
            term = mse_term + contrastive_weight * contrastive_term
            losses[f"jepa_mse_{target_name}"] = mse_term
            losses[f"jepa_contrastive_{target_name}"] = contrastive_term
            losses[f"jepa_{target_name}"] = term
            jepa_terms.append(term)

        losses["jepa"] = torch.stack(jepa_terms).mean() if jepa_terms else zero

        static_terms = []
        for name, projector in self.static_projectors.items():
            if name not in batch["static"]:
                continue
            available = batch["static_availability"][name].float() > 0.5
            if not available.any():
                continue
            static_latent = projector(batch["static"][name][available])
            dynamic_target = context_latent.detach()[available]
            term = F.mse_loss(
                F.normalize(static_latent, dim=-1),
                F.normalize(dynamic_target, dim=-1),
            )
            losses[f"static_align_{name}"] = term
            static_terms.append(term)

        losses["static_align"] = (
            torch.stack(static_terms).mean() if static_terms else zero
        )
        losses["loss"] = (
            jepa_loss_weight * losses["jepa"]
            + static_align_weight * losses["static_align"]
        )
        return outputs, losses
