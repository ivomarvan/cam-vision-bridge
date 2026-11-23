"""qrdet on overlapping tiles, then one set of quads for the whole frame."""

from __future__ import annotations

from typing import Any

import numpy as np
from colors import QRDET
from items import quads_with_panel
from numpy.typing import NDArray
from reader import quads_in_frame

from cam_vision_bridge import detect_tiled
from cam_vision_bridge.protocol.results import ResultItem


def scan(reader: Any, image: NDArray[np.uint8]) -> list[ResultItem]:
    """Find QR codes on a 2×2 overlap grid.

    Args:
        reader: QReader from :func:`reader.open_reader`.
        image: RGB ``uint8`` frame.

    Returns:
        Green quads in full-frame coordinates, plus a panel line each.
    """
    quads = detect_tiled(
        image,
        lambda tile: quads_in_frame(reader, tile, color=QRDET),
        rows=2,
        cols=2,
        overlap=0.2,
    )
    return quads_with_panel(quads, prefix="qrdet")
