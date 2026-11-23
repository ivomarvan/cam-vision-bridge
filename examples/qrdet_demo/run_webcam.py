"""Run the qrdet demo on a webcam and show the annotated frame on this PC.

.venv-qrdet/bin/python examples/qrdet_demo/run_webcam.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_DEMO = Path(__file__).resolve().parent
_EXAMPLES = _DEMO.parent
for _path in (_DEMO, _EXAMPLES):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from cameras import prepare_webcam  # noqa: E402
from colors import QRDET  # noqa: E402
from reader import open_reader, scan_frame  # noqa: E402
from runtime import run_webcam  # noqa: E402


def main() -> int:
    """Open the webcam, draw qrdet quads, and wait until the window closes.

    Returns:
        Process status code. ``0`` after the window closes.
    """
    camera = prepare_webcam()
    reader = open_reader()
    return run_webcam(
        lambda image: scan_frame(reader, image, color=QRDET),
        camera_index=camera,
        window="qrdet",
    )


if __name__ == "__main__":
    sys.exit(main())
