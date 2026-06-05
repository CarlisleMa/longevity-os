"""Small cross-modal JEPA prototype with an aging-clock objective."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class MLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        dropout: float,
        final_norm: bool = True,
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = [
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
        ]
        if final_norm:
            layers.append(nn.LayerNorm(output_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class CrossModalJEPA(nn.Module):
    """Predict held-out modality latents from the remaining available modalities."""

    def __init__(
        self,
        input_dims: dict[str, int],
        latent_dim: int = 128,
        hidden_dim: int = 256,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.modality_names = list(input_dims.keys())
        self.encoders = nn.ModuleDict(
            {
                name: MLP(input_dim, hidden_dim, latent_dim, dropout)
                for name, input_dim in input_dims.items()
            }
        )
        self.predictors = nn.ModuleDict(
            {
                name: MLP(latent_dim, hidden_dim, latent_dim, dropout)
                for name in self.modality_names
            }
        )
        self.age_head = nn.Sequential(nn.LayerNorm(latent_dim), nn.Linear(latent_dim, 1))
        self.severity_head = nn.Sequential(
            nn.LayerNorm(latent_dim), nn.Linear(latent_dim, 4)
        )

    def encode(self, modalities: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        return {
            name: self.encoders[name](modalities[name])
            for name in self.modality_names
        }

    def pooled(
        self,
        latents: dict[str, torch.Tensor],
        availability: dict[str, torch.Tensor],
    ) -> torch.Tensor:
        weighted = []
        weights = []
        for name in self.modality_names:
            weight = availability[name].float().unsqueeze(-1)
            weighted.append(latents[name] * weight)
            weights.append(weight)
        numerator = torch.stack(weighted, dim=0).sum(dim=0)
        denominator = torch.stack(weights, dim=0).sum(dim=0).clamp_min(1.0)
        return numerator / denominator

    def forward(self, batch: dict[str, object]) -> dict[str, torch.Tensor | dict[str, torch.Tensor]]:
        latents = self.encode(batch["modalities"])
        pooled = self.pooled(latents, batch["availability"])
        return {
            "latents": latents,
            "pooled": pooled,
            "age_pred": self.age_head(pooled).squeeze(-1),
            "severity_logits": self.severity_head(pooled),
        }

    def losses(
        self,
        batch: dict[str, object],
        jepa_loss_weight: float = 1.0,
        age_loss_weight: float = 1.0,
        severity_loss_weight: float = 0.0,
    ) -> tuple[dict[str, torch.Tensor | dict[str, torch.Tensor]], dict[str, torch.Tensor]]:
        outputs = self.forward(batch)
        latents = outputs["latents"]
        availability = {
            name: batch["availability"][name].float()
            for name in self.modality_names
        }
        total_available = torch.stack(
            [availability[name] for name in self.modality_names], dim=0
        ).sum(dim=0)

        losses: dict[str, torch.Tensor] = {}
        jepa_terms = []
        for target in self.modality_names:
            target_mask = (availability[target] > 0.5) & (total_available >= 2.0)
            if not target_mask.any():
                continue

            source_weighted = []
            source_weights = []
            for source in self.modality_names:
                if source == target:
                    continue
                weight = availability[source].float().unsqueeze(-1)
                source_weighted.append(latents[source] * weight)
                source_weights.append(weight)

            context = torch.stack(source_weighted, dim=0).sum(dim=0)
            context = context / torch.stack(source_weights, dim=0).sum(dim=0).clamp_min(1.0)
            predicted = self.predictors[target](context)
            target_latent = latents[target].detach()
            target_loss = F.mse_loss(predicted[target_mask], target_latent[target_mask])
            losses[f"jepa_{target}"] = target_loss
            jepa_terms.append(target_loss)

        zero = outputs["pooled"].sum() * 0.0
        losses["jepa"] = torch.stack(jepa_terms).mean() if jepa_terms else zero

        age = batch["age"].float()
        age_mask = torch.isfinite(age)
        losses["age"] = (
            F.mse_loss(outputs["age_pred"][age_mask], age[age_mask])
            if age_mask.any()
            else zero
        )

        severity = batch["severity"].long()
        severity_mask = severity >= 0
        losses["severity"] = (
            F.cross_entropy(outputs["severity_logits"][severity_mask], severity[severity_mask])
            if severity_mask.any()
            else zero
        )

        losses["loss"] = (
            jepa_loss_weight * losses["jepa"]
            + age_loss_weight * losses["age"]
            + severity_loss_weight * losses["severity"]
        )
        return outputs, losses
