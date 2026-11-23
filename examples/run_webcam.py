"""Show the fixed box from ``run_phone.py`` on a webcam window.

    .venv-qrdet/bin/python examples/run_webcam.py

The library environment uses headless OpenCV, which cannot open a window.
Use an environment that has ``opencv-python`` or ``opencv-contrib-python``.
"""

from __future__ import annotations

import sys

from cameras import prepare_webcam
from runtime import run_webcam

from cam_vision_bridge.protocol import Box


def main() -> int:
    """Draw one box on every webcam frame.

    Returns:
        Process status code. ``0`` after the window closes.
    """
    camera = prepare_webcam()
    box = Box(t="box", x=0.2, y=0.2, w=0.4, h=0.3, label="pc", color="#00e5ff")
    return run_webcam(lambda _image: [box], camera_index=camera, window="phone-box")


if __name__ == "__main__":
    sys.exit(main())
