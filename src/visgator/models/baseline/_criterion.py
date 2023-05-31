##
##
##

import torch.nn.functional as F
from jaxtyping import Float
from torch import Tensor

from visgator.utils.bbox import BBoxes

from .._criterion import Criterion as BaseCriterion
from .._criterion import LossInfo


class Criterion(BaseCriterion[BBoxes]):
    def __init__(self) -> None:
        super().__init__()

    @property
    def losses(self) -> list[LossInfo]:
        return [LossInfo("l1_loss", 1.0)]

    def forward(self, output: BBoxes, target: BBoxes) -> dict[str, Float[Tensor, ""]]:
        output = output.to_xyxy().normalize()
        target = target.to_xyxy().normalize()
        loss = F.l1_loss(output.tensor, target.tensor)
        return {"l1_loss": loss}
