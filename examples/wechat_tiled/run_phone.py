"""Phone demo: WeChat QR on native-sized tiles of the largest phone frame.

.venv-qrdet/bin/python examples/wechat_tiled/run_phone.py
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

from models import open_detector  # noqa: E402
from runtime import run_phone  # noqa: E402
from scan import scan  # noqa: E402


def main() -> int:
    """Pair the phone and publish tiled WeChat QR.

    Returns:
        Process status code. ``0`` after the session closes.
    """
    detector = open_detector()
    # 1920×1080 is the largest frame the phone page will send.
    return run_phone(lambda image: scan(detector, image), capture_size=(1920, 1080))


if __name__ == "__main__":
    sys.exit(main())
