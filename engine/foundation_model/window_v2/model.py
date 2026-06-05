"""Target-token temporal JEPA model.

The v1 window model predicts one pooled target-window latent per modality. This
version follows the I-JEPA/V-JEPA pattern more closely: a student context
encoder sees only observed temporal context, an EMA teacher encodes target-window
patch tokens, and a predictor maps context tokens plus target queries to the
teacher's stopped target-token embeddings.
"""

from __future__ import annotations

import copy

import torch
from torch import nn
from torch.nn import functional as F


class PatchTokenEmbed(nn.Module):
    """Embed fixed-length temporal patches plus missingness indicators."""

    def __init__(
        self,
        n_channels: int,
        model_dim: int,
        patch_len: int,
        stride: int,
    ) -> None:
        super().__init__()
        if patch_len <= 0 or stride <= 0:
            raise ValueError("patch_len and stride must be positive")
        self.patch_len = patch_len
        self.stride = stride
        self.proj = nn.Linear(n_channels * 2 * patch_len, model_dim)

    def forward(
        self,
        values: torch.Tensor,
        masks: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if values.ndim != 3 or masks.ndim != 3:
            raise ValueError("values and masks must be [batch, time, channels]")
        if values.shape != masks.shape:
            raise ValueError("values and masks must have identical shapes")
        if values.shape[1] < self.patch_len:
            raise ValueError("sequence length must be >= patch_len")

        x = torch.cat([values, masks.float()], dim=-1)
        patches = x.unfold(dimension=1, size=self.patch_len, step=self.stride)
        patches = patches.transpose(2, 3).contiguous()
        patches = patches.reshape(patches.shape[0], patches.shape[1], -1)

        point_valid = masks.any(dim=-1).float()
        patch_valid = point_valid.unfold(1, self.patch_len, self.stride).any(dim=-1)
        return self.proj(patches), patch_valid


class TemporalTokenEncoder(nn.Module):
    """Transformer encoder that returns per-patch modality tokens."""

    def __init__(
        self,
        sequence_dims: dict[str, int],
        max_len: int,
        latent_dim: int = 128,
        model_dim: int = 128,
        patch_len: int = 6,
        stride: int = 3,
        layers: int = 2,
        heads: int = 4,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if not sequence_dims:
            raise ValueError("At least one sequence modality is required")
        if max_len < patch_len:
            raise ValueError("max_len must be >= patch_len")
        if model_dim % heads != 0:
            raise ValueError("model_dim must be divisible by heads")

        self.sequence_names = list(sequence_dims)
        self.name_to_id = {name: i for i, name in enumerate(self.sequence_names)}
        self.patch_embeds = nn.ModuleDict(
            {
                name: PatchTokenEmbed(n_channels, model_dim, patch_len, stride)
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
        self.latent = nn.Sequential(
            nn.Linear(model_dim, latent_dim),
            nn.LayerNorm(latent_dim),
        )
        nn.init.normal_(self.pos_emb, std=0.02)
        nn.init.normal_(self.modality_emb.weight, std=0.02)

    def encode_tokens(
        self,
        values: dict[str, torch.Tensor],
        masks: dict[str, torch.Tensor],
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        token_parts: list[torch.Tensor] = []
        valid_parts: list[torch.Tensor] = []
        for name in self.sequence_names:
            if name not in values:
                continue
            tokens, valid = self.patch_embeds[name](values[name], masks[name])
            if tokens.shape[1] > self.pos_emb.shape[1]:
                raise ValueError(
                    f"Too many patches for {name}: {tokens.shape[1]} > "
                    f"{self.pos_emb.shape[1]}"
                )
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

        tokens = torch.cat(token_parts, dim=1)
        valid = torch.cat(valid_parts, dim=1)
        attention_valid = valid.clone()
        no_valid = ~attention_valid.any(dim=1)
        if no_valid.any():
            attention_valid[no_valid, 0] = True

        encoded = self.transformer(tokens, src_key_padding_mask=~attention_valid)
        return self.norm(encoded), valid, attention_valid

    def project_tokens(self, tokens: torch.Tensor) -> torch.Tensor:
        return self.latent(tokens)

    def pool_project(self, tokens: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
        pool_valid = valid.clone()
        no_valid = ~pool_valid.any(dim=1)
        if no_valid.any():
            pool_valid[no_valid, 0] = True
        weights = pool_valid.float().unsqueeze(-1)
        pooled = (tokens * weights).sum(dim=1) / weights.sum(dim=1).clamp_min(1.0)
        return self.latent(pooled)


def _valid_latent_std(latents: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
    selected = latents[valid]
    if selected.shape[0] < 2:
        return latents.sum() * 0.0
    return selected.std(dim=0, unbiased=False).mean()


def _variance_floor_loss(
    latents: torch.Tensor,
    valid: torch.Tensor,
    floor: float = 1.0,
    eps: float = 1e-4,
) -> torch.Tensor:
    selected = latents[valid]
    if selected.shape[0] < 2:
        return latents.sum() * 0.0
    std = torch.sqrt(selected.var(dim=0, unbiased=False) + eps)
    return F.relu(floor - std).mean()


class WindowV2JEPA(nn.Module):
    """Temporal target-token JEPA with a student encoder and EMA teacher."""

    def __init__(
        self,
        sequence_dims: dict[str, int],
        context_len: int,
        target_len: int,
        target_names: tuple[str, ...],
        latent_dim: int = 128,
        model_dim: int = 128,
        patch_len: int = 6,
        stride: int = 3,
        layers: int = 2,
        heads: int = 4,
        predictor_layers: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if target_len < patch_len:
            raise ValueError("target_len must be >= patch_len")
        missing_targets = sorted(set(target_names) - set(sequence_dims))
        if missing_targets:
            raise ValueError(f"Target modalities missing from sequence_dims: {missing_targets}")
        if model_dim % heads != 0:
            raise ValueError("model_dim must be divisible by heads")

        self.sequence_names = list(sequence_dims)
        self.target_names = list(target_names)
        self.target_to_id = {name: i for i, name in enumerate(self.target_names)}
        self.context_len = context_len
        self.target_len = target_len
        self.patch_len = patch_len
        self.stride = stride
        self.max_target_patches = 1 + (target_len - patch_len) // stride

        self.context_encoder = TemporalTokenEncoder(
            sequence_dims=sequence_dims,
            max_len=max(context_len, target_len),
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

        self.target_modality_query = nn.Embedding(len(self.target_names), model_dim)
        self.target_pos_query = nn.Embedding(self.max_target_patches, model_dim)
        self.query_norm = nn.LayerNorm(model_dim)
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=model_dim,
            nhead=heads,
            dim_feedforward=model_dim * 4,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.predictor = nn.TransformerDecoder(decoder_layer, num_layers=predictor_layers)
        self.predictor_head = nn.Sequential(
            nn.LayerNorm(model_dim),
            nn.Linear(model_dim, latent_dim),
            nn.LayerNorm(latent_dim),
        )
        nn.init.normal_(self.target_modality_query.weight, std=0.02)
        nn.init.normal_(self.target_pos_query.weight, std=0.02)

    @torch.no_grad()
    def update_teacher(self, tau: float = 0.99) -> None:
        for teacher, student in zip(
            self.target_encoder.parameters(),
            self.context_encoder.parameters(),
            strict=True,
        ):
            teacher.data.mul_(tau).add_(student.data, alpha=1.0 - tau)

    def encode_context_tokens(
        self,
        batch: dict[str, object],
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.context_encoder.encode_tokens(
            batch["context_values"],
            batch["context_masks"],
        )

    def encode_context(self, batch: dict[str, object]) -> torch.Tensor:
        tokens, valid, _ = self.encode_context_tokens(batch)
        return self.context_encoder.pool_project(tokens, valid)

    def _queries(
        self,
        batch_size: int,
        target_i: int,
        n_patches: int,
        device: torch.device,
    ) -> torch.Tensor:
        if n_patches > self.max_target_patches:
            raise ValueError(
                f"n_patches={n_patches} exceeds max_target_patches="
                f"{self.max_target_patches}"
            )
        modality_ids = torch.full(
            (batch_size, n_patches),
            target_i,
            dtype=torch.long,
            device=device,
        )
        pos_ids = torch.arange(n_patches, device=device).view(1, n_patches)
        query = self.target_modality_query(modality_ids) + self.target_pos_query(pos_ids)
        return self.query_norm(query)

    def predict_target_tokens(
        self,
        context_tokens: torch.Tensor,
        context_attention_valid: torch.Tensor,
        target_i: int,
        n_patches: int,
    ) -> torch.Tensor:
        query = self._queries(
            batch_size=context_tokens.shape[0],
            target_i=target_i,
            n_patches=n_patches,
            device=context_tokens.device,
        )
        decoded = self.predictor(
            tgt=query,
            memory=context_tokens,
            memory_key_padding_mask=~context_attention_valid,
        )
        return self.predictor_head(decoded)

    @staticmethod
    def _token_loss(
        predicted: torch.Tensor,
        target: torch.Tensor,
        valid: torch.Tensor,
        loss_type: str,
    ) -> torch.Tensor:
        pred = F.normalize(predicted, dim=-1)
        tgt = F.normalize(target.detach(), dim=-1)
        if loss_type == "mse":
            return F.mse_loss(pred[valid], tgt[valid])
        if loss_type == "smooth_l1":
            return F.smooth_l1_loss(pred[valid], tgt[valid])
        raise ValueError("loss_type must be 'mse' or 'smooth_l1'")

    def losses(
        self,
        batch: dict[str, object],
        jepa_loss_weight: float = 1.0,
        variance_weight: float = 0.0,
        loss_type: str = "smooth_l1",
    ) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        context_tokens, context_valid, context_attention_valid = self.encode_context_tokens(batch)
        context_latent = self.context_encoder.pool_project(context_tokens, context_valid)
        outputs: dict[str, torch.Tensor] = {"context_latent": context_latent}

        target_ids = batch["target_modality_id"].long()
        zero = context_tokens.sum() * 0.0
        jepa_terms: list[torch.Tensor] = []
        variance_terms: list[torch.Tensor] = []
        losses: dict[str, torch.Tensor] = {}

        for target_i, target_name in enumerate(self.target_names):
            row_mask = target_ids == target_i
            if not row_mask.any():
                continue

            target_values = {target_name: batch["target_values"][target_name][row_mask]}
            target_masks = {target_name: batch["target_masks"][target_name][row_mask]}
            with torch.no_grad():
                teacher_tokens, target_valid, _ = self.target_encoder.encode_tokens(
                    target_values,
                    target_masks,
                )
                target_latent = self.target_encoder.project_tokens(teacher_tokens)

            if not target_valid.any():
                losses[f"jepa_{target_name}"] = zero
                losses[f"target_std_{target_name}"] = zero
                losses[f"pred_std_{target_name}"] = zero
                continue

            predicted = self.predict_target_tokens(
                context_tokens=context_tokens[row_mask],
                context_attention_valid=context_attention_valid[row_mask],
                target_i=target_i,
                n_patches=target_latent.shape[1],
            )
            term = self._token_loss(
                predicted=predicted,
                target=target_latent,
                valid=target_valid,
                loss_type=loss_type,
            )
            losses[f"jepa_{target_name}"] = term
            losses[f"target_std_{target_name}"] = _valid_latent_std(
                target_latent.detach(),
                target_valid,
            )
            losses[f"pred_std_{target_name}"] = _valid_latent_std(predicted, target_valid)
            jepa_terms.append(term)
            variance_terms.append(_variance_floor_loss(predicted, target_valid))

        losses["jepa"] = torch.stack(jepa_terms).mean() if jepa_terms else zero
        losses["variance"] = (
            torch.stack(variance_terms).mean() if variance_terms else zero
        )
        losses["loss"] = (
            jepa_loss_weight * losses["jepa"]
            + variance_weight * losses["variance"]
        )
        return outputs, losses

