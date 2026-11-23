"""Tiling maps tile-local quads back onto the full frame and drops duplicates."""

from __future__ import annotations

import numpy as np
import pytest

from cam_vision_bridge.protocol import Point, Quad
from cam_vision_bridge.vision import detect_tiled, merge_quads, split_image

pytestmark = pytest.mark.unit


def _quad(x0: float, y0: float, x1: float, y1: float, score: float | None = None) -> Quad:
    return Quad(
        t="quad",
        points=[
            Point(x=x0, y=y0),
            Point(x=x1, y=y0),
            Point(x=x1, y=y1),
            Point(x=x0, y=y1),
        ],
        score=score,
        label="code",
    )


def test_split_image_covers_the_frame_and_overlaps() -> None:
    image = np.zeros((80, 100, 3), dtype=np.uint8)
    tiles = split_image(image, rows=2, cols=2, overlap=0.2)
    assert len(tiles) == 4
    assert min(tile.x0 for tile in tiles) == 0
    assert min(tile.y0 for tile in tiles) == 0
    assert max(tile.x1 for tile in tiles) == 100
    assert max(tile.y1 for tile in tiles) == 80
    assert tiles[0].x1 > tiles[1].x0


def test_detect_tiled_maps_the_last_tile_onto_the_frame() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    seen = 0

    def detect(_tile: np.ndarray) -> list[Quad]:
        nonlocal seen
        seen += 1
        # Row-major order puts the bottom-right crop last when overlap is 0.
        if seen < 4:
            return []
        return [_quad(0.0, 0.0, 1.0, 1.0)]

    found = detect_tiled(image, detect, rows=2, cols=2, overlap=0.0)
    assert seen == 4
    assert len(found) == 1
    assert found[0].points[0].x == pytest.approx(0.5)
    assert found[0].points[0].y == pytest.approx(0.5)
    assert found[0].points[2].x == pytest.approx(1.0)
    assert found[0].points[2].y == pytest.approx(1.0)


def test_detect_tiled_keeps_the_mark_that_one_tile_sees_whole() -> None:
    image = np.full((54, 96, 3), 255, dtype=np.uint8)
    image[25:33, 40:48] = 0

    def detect(tile: np.ndarray) -> list[Quad]:
        dark = tile.mean(axis=2) < 128
        if not bool(dark.any()):
            return []
        rows, cols = np.nonzero(dark)
        height, width = tile.shape[:2]
        return [
            _quad(
                float(cols.min()) / width,
                float(rows.min()) / height,
                float(cols.max() + 1) / width,
                float(rows.max() + 1) / height,
                score=1.0,
            )
        ]

    found = detect_tiled(image, detect, rows=2, cols=2, overlap=0.2)
    assert len(found) == 1
    xs = [point.x * 96 for point in found[0].points]
    ys = [point.y * 54 for point in found[0].points]
    assert min(xs) == pytest.approx(40)
    assert max(xs) == pytest.approx(48)
    assert min(ys) == pytest.approx(25)
    assert max(ys) == pytest.approx(33)


def test_merge_quads_replaces_a_clipped_fragment_with_the_complete_box() -> None:
    fragment = _quad(0.40, 0.46, 0.60, 0.55, score=0.95)
    complete = _quad(0.40, 0.46, 0.60, 0.70, score=0.80)
    merged = merge_quads([fragment, complete], iou_threshold=0.3)
    assert len(merged) == 1
    assert max(point.y for point in merged[0].points) == pytest.approx(0.70)


def test_merge_quads_drops_every_fragment_when_the_code_crosses_both_seams() -> None:
    sliver = _quad(1050 / 1920, 580 / 1080, 1067 / 1920, 600 / 1080, score=1)
    top = _quad(1050 / 1920, 580 / 1080, 1150 / 1920, 600 / 1080, score=1)
    left = _quad(1050 / 1920, 580 / 1080, 1067 / 1920, 670 / 1080, score=1)
    complete = _quad(1050 / 1920, 580 / 1080, 1150 / 1920, 670 / 1080, score=1)
    merged = merge_quads([sliver, top, left, complete], iou_threshold=0.3)
    assert len(merged) == 1
    assert max(point.x for point in merged[0].points) == pytest.approx(1150 / 1920)
    assert max(point.y for point in merged[0].points) == pytest.approx(670 / 1080)


def test_merge_quads_keeps_the_higher_score() -> None:
    low = _quad(0.1, 0.1, 0.4, 0.4, score=0.2)
    high = _quad(0.12, 0.12, 0.42, 0.42, score=0.9)
    other = _quad(0.7, 0.7, 0.9, 0.9, score=0.4)
    merged = merge_quads([low, high, other], iou_threshold=0.3)
    assert len(merged) == 2
    assert merged[0].score == pytest.approx(0.9)


def test_split_image_rejects_an_overlap_of_one() -> None:
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="overlap"):
        split_image(image, overlap=1.0)
