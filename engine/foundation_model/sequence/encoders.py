"""Encoders for raw sequence and static modalities."""

from __future__ import annotations

import torch
from torch import nn


class MLPEncoder(nn.Module):
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


class PatchTransformerEncoder(nn.Module):
    """PatchTST-style encoder for fixed-length multichannel time series."""

    def __init__(
        self,
        n_channels: int,
        seq_len: int,
        latent_dim: int,
        model_dim: int = 128,
        patch_len: int = 24,
        stride: int = 12,
        layers: int = 2,
        heads: int = 4,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if seq_len < patch_len:
            raise ValueError("seq_len must be >= patch_len")
        self.n_channels = n_channels
        self.seq_len = seq_len
        self.patch_len = patch_len
        self.stride = stride
        self.n_patches = 1 + (seq_len - patch_len) // stride

        self.patch_proj = nn.Linear(n_channels * 2 * patch_len, model_dim)
        self.pos_emb = nn.Parameter(torch.zeros(1, self.n_patches, model_dim))
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

    def forward(self, values: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        x = torch.cat([values, masks.float()], dim=-1)
        patches = x.unfold(dimension=1, size=self.patch_len, step=self.stride)
        # unfold returns B x patches x channels x patch_len.
        patches = patches.transpose(2, 3).contiguous()
        patches = patches.reshape(patches.shape[0], patches.shape[1], -1)

        point_valid = masks.any(dim=-1).float()
        patch_valid = point_valid.unfold(1, self.patch_len, self.stride).any(dim=-1)
        no_valid = ~patch_valid.any(dim=1)
        if no_valid.any():
            patch_valid = patch_valid.clone()
            patch_valid[no_valid, 0] = True

        encoded = self.patch_proj(patches) + self.pos_emb[:, : patches.shape[1]]
        encoded = self.transformer(encoded, src_key_padding_mask=~patch_valid)

        weights = patch_valid.float().unsqueeze(-1)
        pooled = (encoded * weights).sum(dim=1) / weights.sum(dim=1).clamp_min(1.0)
        return self.out(self.norm(pooled))
