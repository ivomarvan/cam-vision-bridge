"""Detect QR codes on the phone camera and send quads plus decoded text.

Install the demo dependencies into a separate environment first. They pull in
torch and are not part of ``cam_vision_bridge``.

    python3.12 -m venv .venv-qrdet
    .venv-qrdet/bin/pip install -e .
    .venv-qrdet/bin/pip install -r examples/qrdet_demo/requirements.txt
    .venv-qrdet/bin/python examples/qrdet_demo/run_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_DEMO = Path(__file__).resolve().parent
_EXAMPLES = _DEMO.parent
for _path in (_DEMO, _EXAMPLES):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from colors import QRDET  # noqa: E402
from reader import open_reader, scan_frame  # noqa: E402
from runtime import run_phone  # noqa: E402


def main() -> int:
    """Pair by QR, then publish one result per phone frame.

    Returns:
        Process status code. ``0`` after the session closes.
    """
    reader = open_reader()
    return run_phone(
        lambda image: scan_frame(reader, image, color=QRDET),
        capture_size=(1280, 720),
    )


if __name__ == "__main__":
    sys.exit(main())
