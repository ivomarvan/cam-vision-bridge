"""Phone demo: tiled qrdet and tiled WeChat QR, each in its own color.

.venv-qrdet/bin/python examples/qrdet_wechat/run_phone.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_EXAMPLES = Path(__file__).resolve().parents[1]
for _path in (_EXAMPLES, _EXAMPLES / "qrdet_demo", _EXAMPLES / "qrdet_wechat"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from models import open_detector  # noqa: E402
from reader import open_reader  # noqa: E402
from runtime import run_phone  # noqa: E402
from scan import scan  # noqa: E402


def main() -> int:
    """Pair the phone and publish both detectors.

    Returns:
        Process status code. ``0`` after the session closes.
    """
    reader = open_reader()
    detector = open_detector()
    return run_phone(
        lambda image: scan(reader, detector, image),
        capture_size=(1920, 1080),
    )


if __name__ == "__main__":
    sys.exit(main())
