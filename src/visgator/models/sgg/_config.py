##
##
##

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import serde
from typing_extensions import Self

from .._config import Config as _Config


@serde.serde(type_check=serde.Strict)
@dataclass(frozen=True)
class EncodersConfig:
    """Configuration for encoders."""

    hidden_dim: int
    model: str = "ViT-B-32"
    pretrained: str = "laion2b_s34b_b79k"

    @classmethod
    def from_dict(cls, cfg: dict[str, Any]) -> Self:
        return serde.from_dict(cls, cfg)

    def to_dict(self) -> dict[str, Any]:
        return serde.to_dict(self)


@serde.serde(type_check=serde.Strict)
@dataclass(frozen=True)
class DetectorConfig:
    """Configuration for object detector."""

    weights: Path
    config: Path
    box_threshold: float = serde.field(default=0.35)
    text_threshold: float = serde.field(default=0.25)

    @classmethod
    def from_dict(cls, cfg: dict[str, Any]) -> Self:
        return serde.from_dict(cls, cfg)

    def to_dict(self) -> dict[str, Any]:
        return serde.to_dict(self)


@serde.serde(type_check=serde.Strict)
@dataclass(frozen=True)
class DecoderConfig:
    """Configuration for decoder."""

    hidden_dim: int
    num_layers: int
    num_heads: int = 8
    dropout: float = 0.1

    def __post_init__(self) -> None:
        if self.num_layers < 1:
            raise ValueError("num_layers must be positive.")

        if self.num_heads < 1:
            raise ValueError("num_heads must be positive.")

        if self.hidden_dim % self.num_heads != 0:
            raise ValueError("hidden_dim must be divisible by num_heads.")

        if self.dropout < 0 or self.dropout > 1:
            raise ValueError("dropout must be between 0 and 1.")

    @classmethod
    def from_dict(cls, cfg: dict[str, Any]) -> Self:
        return serde.from_dict(cls, cfg)

    def to_dict(self) -> dict[str, Any]:
        return serde.to_dict(self)


@serde.serde(type_check=serde.Strict)
@dataclass(frozen=True)
class Config(_Config):
    """Configuration for SceneGraphGrounder model."""

    encoders: EncodersConfig = serde.field(
        serializer=EncodersConfig.to_dict,
        deserializer=EncodersConfig.from_dict,
    )
    detector: DetectorConfig = serde.field(
        serializer=DetectorConfig.to_dict,
        deserializer=DetectorConfig.from_dict,
    )
    decoder: DecoderConfig = serde.field(
        serializer=DecoderConfig.to_dict,
        deserializer=DecoderConfig.from_dict,
    )

    @classmethod
    def from_dict(cls, cfg: dict[str, Any]) -> Self:
        hidden_dim = cfg.get("hidden_dim", None)
        if hidden_dim is None:
            raise ValueError("hidden_dim must be provided.")

        cfg["encoder"]["hidden_dim"] = hidden_dim
        cfg["decoder"]["hidden_dim"] = hidden_dim

        return serde.from_dict(cls, cfg)

    def to_dict(self) -> dict[str, Any]:
        cfg = serde.to_dict(self)
        cfg["hidden_dim"] = self.encoders.hidden_dim
        return cfg