##
##
##

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import wandb
from typing_extensions import Self


@dataclass(frozen=True)
class Checkpoint:
    epoch: int
    pipeline: dict[str, Any]
    optimizer: dict[str, Any]
    lr_scheduler: dict[str, Any]
    scaler: dict[str, Any]
    metrics_tracker: dict[str, Any]
    losses_tracker: dict[str, Any]

    def save(self, checkpoint_file: Path, wandb_save: bool) -> None:
        torch.save(self.__dict__, checkpoint_file)
        if wandb_save:
            wandb.save(checkpoint_file)

    @classmethod
    def from_file(cls, checkpoint_file: Path, device: torch.device) -> Self:
        checkpoint = torch.load(checkpoint_file, map_location=device)
        return cls(**checkpoint)
