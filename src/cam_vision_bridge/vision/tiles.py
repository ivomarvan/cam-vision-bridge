"""Split a frame into overlapping tiles and merge quad detections.

A detector that resizes its input to a few hundred pixels misses a code that
is small in a 1920-wide frame. Tiles keep that code large. Coordinates that
come back are fractions of the tile; this module maps them onto the full frame
and drops duplicates that sit on an overlap.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from cam_vision_bridge.protocol import Point, Quad

DetectQuads = Callable[[NDArray[np.uint8]], Sequence[Quad]]


@dataclass(frozen=True)
class Tile:
    """One crop of a frame.

    ``image`` is a view of the source array. ``x0`` and ``y0`` are its top-left
    corner in that source, in pixels. ``x1`` and ``y1`` are the exclusive
    bottom-right corner.
    """

    image: NDArray[np.uint8]
    x0: int
    y0: int
    x1: int
    y1: int


def split_image(
    image: NDArray[np.uint8],
    *,
    rows: int = 2,
    cols: int = 2,
    overlap: float = 0.2,
) -> list[Tile]:
    """Cut ``image`` into a grid of overlapping crops.

    Args:
        image: RGB or BGR frame, shape ``(height, width, channels)``.
        rows: Number of vertical bands. At least 1.
        cols: Number of horizontal bands. At least 1.
        overlap: Fraction of a tile shared with the next one, from 0 up to
            but not including 1.

    Returns:
        Tiles in row-major order. Together they cover every pixel of ``image``.

    Raises:
        ValueError: If the grid, the overlap, or the image shape is unusable.
    """
    _check_grid(rows, cols, overlap)
    height, width = _frame_size(image)
    tiles: list[Tile] = []
    for y0, y1 in _spans(height, rows, overlap):
        for x0, x1 in _spans(width, cols, overlap):
            tiles.append(Tile(image=image[y0:y1, x0:x1], x0=x0, y0=y0, x1=x1, y1=y1))
    return tiles


def detect_tiled(
    image: NDArray[np.uint8],
    detect: DetectQuads,
    *,
    rows: int = 2,
    cols: int = 2,
    overlap: float = 0.2,
    iou_threshold: float = 0.3,
) -> list[Quad]:
    """Run ``detect`` on each tile and return quads in full-frame coordinates.

    Args:
        image: Frame passed to :func:`split_image`.
        detect: Maps one tile image to quads whose points are fractions of
            that tile, from 0 to 1.
        rows: Vertical tile count.
        cols: Horizontal tile count.
        overlap: Shared fraction between neighbouring tiles.
        iou_threshold: Overlaps at or above this value collapse into one quad.

    Returns:
        Merged quads. Points are fractions of ``image``.
    """
    height, width = _frame_size(image)
    found: list[Quad] = []
    for tile in split_image(image, rows=rows, cols=cols, overlap=overlap):
        found.extend(_remap(quad, tile, width, height) for quad in detect(tile.image))
    return merge_quads(found, iou_threshold=iou_threshold)


def merge_quads(quads: Sequence[Quad], *, iou_threshold: float = 0.3) -> list[Quad]:
    """Drop quads that cover the same code, keeping the more complete one.

    A code on a tile edge is seen whole by one tile and clipped by the
    neighbour. The clipped box sits inside the complete one. Keeping the
    higher score would leave the clipped box when the scores tie or the
    fragment scores higher, so the drawn rectangle misses the code.

    Args:
        quads: Quads already expressed in the same coordinate frame.
        iou_threshold: Minimum box overlap that counts as the same code.

    Returns:
        Quads that survived the overlap check. A box that contains another
        surviving box replaces it.

    Raises:
        ValueError: If ``iou_threshold`` is outside 0..1.
    """
    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("iou_threshold must be from 0 to 1")
    kept: list[Quad] = []
    for quad in sorted(quads, key=_score, reverse=True):
        _offer(kept, quad, iou_threshold)
    return kept


def _check_grid(rows: int, cols: int, overlap: float) -> None:
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be at least 1")
    if not 0.0 <= overlap < 1.0:
        raise ValueError("overlap must be from 0 up to but not including 1")


def _frame_size(image: NDArray[np.uint8]) -> tuple[int, int]:
    if image.ndim != 3 or image.shape[0] < 1 or image.shape[1] < 1:
        raise ValueError("image must have a positive height and width")
    return int(image.shape[0]), int(image.shape[1])


def _spans(length: int, parts: int, overlap: float) -> list[tuple[int, int]]:
    if parts == 1:
        return [(0, length)]
    window = int(round(length / (parts - (parts - 1) * overlap)))
    window = min(length, max(1, window))
    last = length - window
    spans: list[tuple[int, int]] = []
    for index in range(parts):
        start = last if index == parts - 1 else int(round(index * last / (parts - 1)))
        end = length if index == parts - 1 else start + window
        spans.append((start, end))
    return spans


def _remap(quad: Quad, tile: Tile, width: int, height: int) -> Quad:
    points = [
        Point(
            x=_unit((tile.x0 + point.x * (tile.x1 - tile.x0)) / width),
            y=_unit((tile.y0 + point.y * (tile.y1 - tile.y0)) / height),
        )
        for point in quad.points
    ]
    return quad.model_copy(update={"points": points})


def _unit(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


# A fragment is the same code when this much of it lies inside the other box.
_CONTAINED = 0.9


def _offer(kept: list[Quad], quad: Quad, iou_threshold: float) -> None:
    box = _box(quad)
    related = [other for other in kept if _same_code(box, _box(other), iou_threshold)]
    if not related:
        kept.append(quad)
        return
    if _already_covered(box, related):
        return
    if all(_coverage(_box(other), box) >= _CONTAINED for other in related):
        _replace(kept, related, quad)


def _already_covered(
    box: tuple[float, float, float, float],
    related: list[Quad],
) -> bool:
    return any(
        _coverage(box, _box(other)) >= _CONTAINED and _area(_box(other)) >= _area(box)
        for other in related
    )


def _replace(kept: list[Quad], related: list[Quad], quad: Quad) -> None:
    drop = {id(other) for other in related}
    kept[:] = [other for other in kept if id(other) not in drop]
    kept.append(quad)


def _same_code(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
    iou_threshold: float,
) -> bool:
    if _iou(left, right) >= iou_threshold:
        return True
    return _coverage(left, right) >= _CONTAINED or _coverage(right, left) >= _CONTAINED


def _coverage(
    inner: tuple[float, float, float, float],
    outer: tuple[float, float, float, float],
) -> float:
    """Return how much of ``inner`` lies inside ``outer``."""
    area = _area(inner)
    if area <= 0.0:
        return 0.0
    ix1 = max(inner[0], outer[0])
    iy1 = max(inner[1], outer[1])
    ix2 = min(inner[2], outer[2])
    iy2 = min(inner[3], outer[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    return inter / area


def _area(box: tuple[float, float, float, float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _score(quad: Quad) -> float:
    if quad.score is None:
        return 0.0
    return quad.score


def _box(quad: Quad) -> tuple[float, float, float, float]:
    xs = [point.x for point in quad.points]
    ys = [point.y for point in quad.points]
    return min(xs), min(ys), max(xs), max(ys)


def _iou(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> float:
    ix1 = max(left[0], right[0])
    iy1 = max(left[1], right[1])
    ix2 = min(left[2], right[2])
    iy2 = min(left[3], right[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0.0:
        return 0.0
    area_left = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    area_right = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = area_left + area_right - inter
    if union <= 0.0:
        return 0.0
    return inter / union
