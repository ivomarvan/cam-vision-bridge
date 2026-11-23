"""Camera selection stays explicit when several webcams return a frame."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "examples" / "cameras.py"
_SPEC = importlib.util.spec_from_file_location("example_cameras", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_CAMERAS = importlib.util.module_from_spec(_SPEC)
sys.modules["example_cameras"] = _CAMERAS
_SPEC.loader.exec_module(_CAMERAS)


def _info(index: int, *, frame: bool) -> object:
    return _CAMERAS.CameraInfo(
        index,
        f"camera {index}",
        640 if frame else None,
        480 if frame else None,
    )


def test_choose_camera_uses_the_only_working_device() -> None:
    chosen = _CAMERAS.choose_camera([_info(0, frame=False), _info(2, frame=True)], None)
    assert chosen.index == 2


def test_choose_camera_requires_an_index_when_several_work() -> None:
    cameras = [_info(0, frame=True), _info(2, frame=True)]
    with pytest.raises(SystemExit, match="--camera"):
        _CAMERAS.choose_camera(cameras, None)


def test_choose_camera_rejects_an_index_without_a_frame() -> None:
    with pytest.raises(SystemExit, match="did not return a frame"):
        _CAMERAS.choose_camera([_info(0, frame=True)], 4)
