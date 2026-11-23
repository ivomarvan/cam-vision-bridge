"""Webcam demo: WeChat QR on native-sized tiles of the camera's largest frame.

.venv-qrdet/bin/python examples/wechat_tiled/run_webcam.py --camera 4
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_EXAMPLES = _HERE.parent
# The script directory is already on sys.path, so a plain insert would leave
# qrdet_wechat in front and `import scan` would load that example's scan.py.
for _path in (_EXAMPLES, _EXAMPLES / "qrdet_wechat", _HERE):
    _text = str(_path)
    if _text in sys.path:
        sys.path.remove(_text)
    sys.path.insert(0, _text)

from cameras import maximum_frame_size, prepare_webcam  # noqa: E402
from models import open_detector  # noqa: E402
from runtime import run_webcam  # noqa: E402
from scan import scan  # noqa: E402


def main() -> int:
    """Open the webcam at its largest size and draw tiled WeChat QR.

    Returns:
        Process status code. ``0`` after the window closes.
    """
    camera = prepare_webcam()
    width, height = maximum_frame_size(camera)
    print(f"webcam frame {width}x{height}", flush=True)
    detector = open_detector()
    return run_webcam(
        lambda image: scan(detector, image),
        camera_index=camera,
        window="wechat-tiled",
        capture_size=(width, height),
    )


if __name__ == "__main__":
    sys.exit(main())
