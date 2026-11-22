"""Immutable camera frame delivered to application code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class Frame:
    """One complete camera image plus capture metadata.

    Args:
        image: RGB pixels, shape ``(height, width, 3)``, dtype ``uint8``.
        frame_id: Monotonic frame counter from the phone.
        captured_at: ISO 8601 capture timestamp from the wire header.
        width: Declared frame width in pixels (matches header ``w``).
        height: Declared frame height in pixels (matches header ``h``).
        camera: Facing from the phone handshake, when known.
    """

    image: NDArray[np.uint8]
    frame_id: int
    captured_at: str
    width: int
    height: int
    camera: Literal["user", "environment"] | None = None
