"""WeChat QR on the whole frame, without qrdet and without tiles."""

from __future__ import annotations

from typing import Any

import numpy as np
from items import quads_with_panel
from models import quads_in_tile
from numpy.typing import NDArray

from cam_vision_bridge.protocol.results import ResultItem


def scan(detector: Any, image: NDArray[np.uint8]) -> list[ResultItem]:
    """Find QR codes with one WeChat pass.

    Args:
        detector: WeChat detector from :func:`models.open_detector`.
        image: RGB ``uint8`` frame.

    Returns:
        Amber quads in frame coordinates, plus a panel line each.
    """
    return quads_with_panel(quads_in_tile(detector, image), prefix="wechat")
