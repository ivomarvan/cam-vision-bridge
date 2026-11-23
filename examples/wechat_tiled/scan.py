"""WeChat QR on tiles the detector can see without shrinking them.

The detector network is exported at 384×384. On a larger image WeChat scales
the whole frame down to about 400×400 (160000 pixels) before the network
runs, so a small code disappears. Tiles stay at or under 384 pixels on each
side. A hit is stored in that tile's coordinates; ``detect_tiled`` maps those
coordinates onto the full frame.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from items import quads_with_panel
from models import quads_in_tile
from numpy.typing import NDArray

from cam_vision_bridge import detect_tiled
from cam_vision_bridge.protocol.results import ResultItem

# Side of the square the WeChat detector was exported with.
NATIVE_SIDE = 384
OVERLAP = 0.2
_LOGGER = logging.getLogger("examples")
_seen: tuple[int, int, int, int] | None = None


def scan(detector: Any, image: NDArray[np.uint8]) -> list[ResultItem]:
    """Find QR codes on native-sized WeChat tiles.

    Args:
        detector: WeChat detector from :func:`models.open_detector`.
        image: RGB ``uint8`` frame, ideally the camera's largest picture.

    Returns:
        Amber quads in full-frame coordinates, plus a panel line each.
    """
    rows, cols = grid_for(int(image.shape[0]), int(image.shape[1]))
    _note_grid(int(image.shape[1]), int(image.shape[0]), rows, cols)
    quads = detect_tiled(
        image,
        lambda tile: quads_in_tile(detector, tile),
        rows=rows,
        cols=cols,
        overlap=OVERLAP,
    )
    return quads_with_panel(quads, prefix="wechat")


def grid_for(height: int, width: int) -> tuple[int, int]:
    """Choose a tile grid whose windows stay within :data:`NATIVE_SIDE`.

    Args:
        height: Frame height in pixels.
        width: Frame width in pixels.

    Returns:
        ``(rows, cols)`` for :func:`detect_tiled`.
    """
    return _parts(height), _parts(width)


def _parts(length: int) -> int:
    parts = 1
    while _window(length, parts) > NATIVE_SIDE and parts < length:
        parts += 1
    return parts


def _window(length: int, parts: int) -> int:
    if parts <= 1:
        return length
    return int(round(length / (parts - (parts - 1) * OVERLAP)))


def _note_grid(width: int, height: int, rows: int, cols: int) -> None:
    global _seen
    key = (width, height, rows, cols)
    if key == _seen:
        return
    _seen = key
    _LOGGER.info(
        "wechat tiles frame=%dx%d grid=%dx%d side<=%d",
        width,
        height,
        cols,
        rows,
        NATIVE_SIDE,
    )
