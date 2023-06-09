##
##
##

import enum
import os
import random
from typing import Optional

import torch
from jaxtyping import Bool, Num
from torch import Tensor
from typing_extensions import Self


def init_torch(seed: int, debug: bool) -> None:
    """Initializes torch with the specified seed and debug mode."""
    torch.set_default_dtype(torch.float32)
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.enabled = True

    if debug:
        torch.backends.cudnn.benchmark = False
        torch.use_deterministic_algorithms(True, warn_only=True)
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    else:
        torch.backends.cudnn.benchmark = True
        torch.use_deterministic_algorithms(False)
        os.environ.pop("CUBLAS_WORKSPACE_CONFIG", None)
        # just to be sure
        os.unsetenv("CUBLAS_WORKSPACE_CONFIG")


# ------------------------------------------------------------------------------
# Device
# ------------------------------------------------------------------------------


class DeviceType(enum.Enum):
    CPU = "cpu"
    CUDA = "cuda"

    @classmethod
    def from_str(cls, value: str) -> Self:
        return cls[value.upper().strip()]

    def __str__(self) -> str:
        return self.value


class Device:
    def __init__(self, type: str, id: Optional[int] = None) -> None:
        self._type = DeviceType.from_str(type)
        self._id = None
        if self._type == DeviceType.CUDA:
            if id is None:
                id = 0

            if id < 0:
                raise ValueError(f"Invalid CUDA device ID {id}. Must be >= 0.")
            if id >= torch.cuda.device_count():
                raise ValueError(
                    f"Invalid CUDA device ID {id}. "
                    f"Only {torch.cuda.device_count()} devices available."
                )

            self._id = id

    @classmethod
    def from_str(cls, value: str) -> Self:
        parts = value.split(":")
        if len(parts) == 1:
            return cls(parts[0])
        return cls(parts[0], int(parts[1]))

    @classmethod
    def default(cls) -> Self:
        if torch.cuda.is_available():
            return cls("cuda")
        return cls("cpu")

    @property
    def is_cuda(self) -> bool:
        return self._type == DeviceType.CUDA

    def to_torch(self) -> torch.device:
        return torch.device(str(self))

    def __str__(self) -> str:
        if self._type == DeviceType.CPU:
            return str(self._type)
        return f"{self._type}:{self._id}"


# ------------------------------------------------------------------------------
# Nested tensors
# ------------------------------------------------------------------------------


class Nested3DTensor:
    """A collection of 2D tensors with different sizes."""

    def __init__(
        self,
        tensor: Num[Tensor, "N L D"],
        sizes: list[int],
        mask: Optional[Bool[Tensor, "N L"]] = None,
    ) -> None:
        if tensor.shape[0] != len(sizes):
            raise ValueError("Number of tensors must match number of sizes.")

        self._tensor = tensor
        self._sizes = sizes
        self._mask = mask

    @classmethod
    def from_tensors(
        cls,
        tensors: list[Num[Tensor, "L D"]],
        pad_value: float = 0.0,
    ) -> Self:
        """Returns a Nested3DTensor from a list of 2D tensors."""
        sizes = [tensor.shape[0] for tensor in tensors]
        tensor = torch.nn.utils.rnn.pad_sequence(
            tensors,
            batch_first=True,
            padding_value=pad_value,
        )

        return cls(tensor, sizes)

    @property
    def tensor(self) -> Num[Tensor, "N L D"]:
        """Returns the tensor with padding."""
        return self._tensor

    @property
    def sizes(self) -> list[int]:
        """Returns the sizes of the tensors without padding."""
        return self._sizes

    @property
    def mask(self) -> Bool[Tensor, "N L"]:
        """Returns the padding mask where True indicates padding."""
        if self._mask is not None:
            return self._mask

        size = (self._tensor.shape[0], self._tensor.shape[1])
        mask = self._tensor.new_ones(size, dtype=torch.bool)
        for i, length in enumerate(self._sizes):
            mask[i, :length] = False

        self._mask = mask
        return mask

    @property
    def device(self) -> torch.device:
        """Returns the device of the tensor."""
        return self._tensor.device

    @property
    def shape(self) -> tuple[int, int, int]:
        """Returns the shape of the padded tensor."""
        return tuple(self._tensor.shape)  # type: ignore

    def to(self, device: torch.device) -> Self:
        """Returns a Nested3DTensor on the specified device."""
        return self.__class__(
            self._tensor.to(device),
            self._sizes,
            self._mask.to(device) if self._mask is not None else None,
        )

    def to_list(self) -> list[Num[Tensor, "L D"]]:
        """Returns a list of 2D tensors without padding."""
        return [self._tensor[i, :length] for i, length in enumerate(self._sizes)]

    def __len__(self) -> int:
        return len(self._sizes)


class Nested4DTensor:
    """A collection of images with different sizes."""

    def __init__(
        self,
        tensor: Num[Tensor, "N C H W"],
        sizes: list[tuple[int, int]],
        mask: Optional[Bool[Tensor, "N H W"]] = None,
    ) -> None:
        if tensor.shape[0] != len(sizes):
            raise ValueError("Number of images must match number of sizes.")

        self._tensor = tensor
        self._sizes = sizes
        self._mask = mask

    @classmethod
    def from_tensors(
        cls,
        tensors: list[Num[Tensor, "C H W"]],
        pad_value: float = 0.0,
    ) -> Self:
        """Returns a Nested4DTensor from a list of 3D tensors."""
        sizes = [(tensor.shape[-2], tensor.shape[-1]) for tensor in tensors]
        max_height, max_width = 0, 0
        for height, width in sizes:
            max_height = max(max_height, height)
            max_width = max(max_width, width)

        size = (len(tensors), tensors[0].shape[0], max_height, max_width)
        tensor = tensors[0].new_full(size, pad_value)

        for i, (height, width) in enumerate(sizes):
            tensor[i, :, :height, :width].copy_(tensors[i])

        return cls(tensor, sizes)

    @property
    def tensor(self) -> Num[Tensor, "N C H W"]:
        """Returns the tensor with padding."""
        return self._tensor

    @property
    def sizes(self) -> list[tuple[int, int]]:
        """Returns the sizes of the tensors without padding."""
        return self._sizes

    @property
    def mask(self) -> Bool[Tensor, "N H W"]:
        """Returns the padding mask where True indicates padding."""
        if self._mask is not None:
            return self._mask

        size = (self._tensor.shape[0], self._tensor.shape[-2], self._tensor.shape[-1])
        mask = self._tensor.new_ones(size, dtype=torch.bool)
        for i, (height, width) in enumerate(self._sizes):
            mask[i, :height, :width] = False

        self._mask = mask
        return mask

    @property
    def device(self) -> torch.device:
        """Returns the device of the tensor."""
        return self._tensor.device

    @property
    def shape(self) -> tuple[int, int, int, int]:
        """Returns the shape of the padded tensor."""
        return tuple(self._tensor.shape)  # type: ignore

    def to(self, device: torch.device) -> Self:
        """Returns a Nested4DTensor on the specified device."""
        return self.__class__(
            self._tensor.to(device),
            self._sizes,
            self._mask.to(device) if self._mask is not None else None,
        )

    def to_list(self) -> list[Num[Tensor, "C H W"]]:
        """Returns a list of 3D tensors without padding."""
        return [
            self._tensor[i, :, :height, :width]
            for i, (height, width) in enumerate(self._sizes)
        ]

    def flatten(self) -> Nested3DTensor:
        """Returns a Nested3DTensor with the same data."""
        tensor = self._tensor.flatten(2).transpose(1, 2)  # (N HW C)
        sizes = [size[0] * size[1] for size in self._sizes]

        if self._mask is not None:
            mask = self._mask.flatten(1)  # (N HW)
        else:
            mask = None

        return Nested3DTensor(tensor, sizes, mask)

    def __len__(self) -> int:
        return len(self._sizes)
