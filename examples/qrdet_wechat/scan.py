"""Tiled qrdet plus tiled WeChat QR, each in its own color."""

from __future__ import annotations

from typing import Any

import numpy as np
from colors import QRDET
from items import quads_with_panel
from models import quads_in_tile
from numpy.typing import NDArray
from reader import quads_in_frame

from cam_vision_bridge import detect_tiled
from cam_vision_bridge.protocol.results import ResultItem


def scan(reader: Any, detector: Any, image: NDArray[np.uint8]) -> list[ResultItem]:
    """Run both detectors on the same 2×2 grid.

    Args:
        reader: QReader from :func:`reader.open_reader`.
        detector: WeChat detector from :func:`models.open_detector`.
        image: RGB ``uint8`` frame.

    Returns:
        Green qrdet quads and amber WeChat quads. Panel lines are prefixed
        with the detector name. The two detectors are not merged together.
    """
    qrdet = detect_tiled(
        image,
        lambda tile: quads_in_frame(reader, tile, color=QRDET),
        rows=2,
        cols=2,
        overlap=0.2,
    )
    wechat = detect_tiled(
        image,
        lambda tile: quads_in_tile(detector, tile),
        rows=2,
        cols=2,
        overlap=0.2,
    )
    return [
        *quads_with_panel(qrdet, prefix="qrdet"),
        *quads_with_panel(wechat, prefix="wechat"),
    ]
