"""Webcam demo: qrdet on overlapping tiles, drawn in a window on this PC.

.venv-qrdet/bin/python examples/qrdet_tiled/run_webcam.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_EXAMPLES = Path(__file__).resolve().parents[1]
for _path in (_EXAMPLES, _EXAMPLES / "qrdet_demo", _EXAMPLES / "qrdet_tiled"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from cameras import prepare_webcam  # noqa: E402
from reader import open_reader  # noqa: E402
from runtime import run_webcam  # noqa: E402
from scan import scan  # noqa: E402


def main() -> int:
    """Open the webcam and draw tiled qrdet quads.

    Returns:
        Process status code. ``0`` after the window closes.
    """
    camera = prepare_webcam()
    reader = open_reader()
    return run_webcam(
        lambda image: scan(reader, image),
        camera_index=camera,
        window="qrdet-tiled",
    )


if __name__ == "__main__":
    sys.exit(main())
