"""Webcam demo: WeChat QR alone, drawn in a window on this PC.

.venv-qrdet/bin/python examples/wechat_qr/run_webcam.py --camera 4
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_EXAMPLES = _HERE.parent
for _path in (_EXAMPLES, _EXAMPLES / "qrdet_wechat", _HERE):
    _text = str(_path)
    if _text in sys.path:
        sys.path.remove(_text)
    sys.path.insert(0, _text)

from cameras import prepare_webcam  # noqa: E402
from models import open_detector  # noqa: E402
from runtime import run_webcam  # noqa: E402
from wechat_scan import scan  # noqa: E402


def main() -> int:
    """Open the webcam and draw WeChat QR.

    Returns:
        Process status code. ``0`` after the window closes.
    """
    camera = prepare_webcam()
    detector = open_detector()
    return run_webcam(
        lambda image: scan(detector, image),
        camera_index=camera,
        window="wechat-qr",
    )


if __name__ == "__main__":
    sys.exit(main())
