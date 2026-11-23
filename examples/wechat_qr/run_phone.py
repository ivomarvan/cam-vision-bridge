"""Phone demo: WeChat QR alone, on the whole frame.

.venv-qrdet/bin/python examples/wechat_qr/run_phone.py
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

from models import open_detector  # noqa: E402
from runtime import run_phone  # noqa: E402
from wechat_scan import scan  # noqa: E402


def main() -> int:
    """Pair the phone and publish WeChat QR.

    Returns:
        Process status code. ``0`` after the session closes.
    """
    detector = open_detector()
    return run_phone(lambda image: scan(detector, image), capture_size=(1280, 720))


if __name__ == "__main__":
    sys.exit(main())
