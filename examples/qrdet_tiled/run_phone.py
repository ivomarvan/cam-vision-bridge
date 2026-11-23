"""Phone demo: qrdet on overlapping tiles at 1920×1080.

.venv-qrdet/bin/python examples/qrdet_tiled/run_phone.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_EXAMPLES = Path(__file__).resolve().parents[1]
for _path in (_EXAMPLES, _EXAMPLES / "qrdet_demo", _EXAMPLES / "qrdet_tiled"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from reader import open_reader  # noqa: E402
from runtime import run_phone  # noqa: E402
from scan import scan  # noqa: E402


def main() -> int:
    """Pair the phone and detect on tiles.

    Returns:
        Process status code. ``0`` after the session closes.
    """
    reader = open_reader()
    return run_phone(lambda image: scan(reader, image), capture_size=(1920, 1080))


if __name__ == "__main__":
    sys.exit(main())
