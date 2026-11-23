"""WeChat tiles stay inside the detector's native side, and hits map back."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATHS = (
    _ROOT / "examples",
    _ROOT / "examples" / "qrdet_wechat",
    _ROOT / "examples" / "wechat_tiled",
)
for _path in _PATHS:
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

_PATH = _ROOT / "examples" / "wechat_tiled" / "scan.py"
_SPEC = importlib.util.spec_from_file_location("wechat_tiled_scan", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_SCAN = importlib.util.module_from_spec(_SPEC)
sys.modules["wechat_tiled_scan"] = _SCAN
_SPEC.loader.exec_module(_SCAN)

from cam_vision_bridge import detect_tiled  # noqa: E402
from cam_vision_bridge.protocol import Point, Quad  # noqa: E402


def test_grid_for_keeps_every_tile_within_the_native_side() -> None:
    rows, cols = _SCAN.grid_for(1080, 1920)
    image = np.zeros((1080, 1920, 3), dtype=np.uint8)
    from cam_vision_bridge import split_image

    tiles = split_image(image, rows=rows, cols=cols, overlap=_SCAN.OVERLAP)
    assert tiles
    assert all(tile.x1 - tile.x0 <= _SCAN.NATIVE_SIDE for tile in tiles)
    assert all(tile.y1 - tile.y0 <= _SCAN.NATIVE_SIDE for tile in tiles)


def test_native_tiles_map_a_corner_mark_onto_the_full_frame() -> None:
    image = np.full((1080, 1920, 3), 255, dtype=np.uint8)
    image[1000:1040, 1800:1860] = 0
    rows, cols = _SCAN.grid_for(1080, 1920)

    def detect(tile: np.ndarray) -> list[Quad]:
        dark = tile.mean(axis=2) < 128
        if not bool(dark.any()):
            return []
        ys, xs = np.nonzero(dark)
        height, width = tile.shape[:2]
        return [
            Quad(
                t="quad",
                points=[
                    Point(x=float(xs.min()) / width, y=float(ys.min()) / height),
                    Point(x=float(xs.max() + 1) / width, y=float(ys.min()) / height),
                    Point(x=float(xs.max() + 1) / width, y=float(ys.max() + 1) / height),
                    Point(x=float(xs.min()) / width, y=float(ys.max() + 1) / height),
                ],
                score=1.0,
            )
        ]

    found = detect_tiled(image, detect, rows=rows, cols=cols, overlap=_SCAN.OVERLAP)
    assert len(found) == 1
    xs = [point.x * 1920 for point in found[0].points]
    ys = [point.y * 1080 for point in found[0].points]
    assert min(xs) == pytest.approx(1800)
    assert max(xs) == pytest.approx(1860)
    assert min(ys) == pytest.approx(1000)
    assert max(ys) == pytest.approx(1040)
