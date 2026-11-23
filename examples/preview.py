"""Draw result items onto a BGR frame for the webcam window."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from cam_vision_bridge.protocol.results import ResultItem

_DEFAULT_BGR = (255, 229, 0)


def draw_items(image_bgr: NDArray[np.uint8], items: Sequence[ResultItem]) -> None:
    """Paint boxes, quads, and positioned text onto ``image_bgr``.

    Args:
        image_bgr: OpenCV frame, modified in place.
        items: Protocol items in normalized coordinates of this frame.
    """
    cv2 = _cv2()
    height, width = image_bgr.shape[:2]
    for item in items:
        color = _bgr(getattr(item, "color", None))
        if item.t == "box":
            corners = np.array(
                [
                    [item.x * width, item.y * height],
                    [(item.x + item.w) * width, item.y * height],
                    [(item.x + item.w) * width, (item.y + item.h) * height],
                    [item.x * width, (item.y + item.h) * height],
                ],
                dtype=np.int32,
            )
            cv2.polylines(image_bgr, [corners], True, color, 2)
        elif item.t in {"quad", "polygon", "polyline"}:
            corners = np.array(
                [[point.x * width, point.y * height] for point in item.points],
                dtype=np.int32,
            )
            cv2.polylines(image_bgr, [corners], item.t != "polyline", color, 2)
        elif item.t == "text" and item.x is not None and item.y is not None:
            cv2.putText(
                image_bgr,
                item.text,
                (int(item.x * width), int(item.y * height)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv2.LINE_AA,
            )


def _bgr(color: object) -> tuple[int, int, int]:
    if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
        return _DEFAULT_BGR
    try:
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
    except ValueError:
        return _DEFAULT_BGR
    return (blue, green, red)


def _cv2() -> object:
    try:
        import cv2
    except ImportError as exc:
        raise SystemExit("OpenCV is required to draw the webcam window.") from exc
    return cv2
