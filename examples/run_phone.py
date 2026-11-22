"""Pair a camera by QR code and print each received frame size.

One command is enough. The script starts the phone page when port 5173 is
closed, asks the library for this computer's LAN address, and prints a QR code
of that URL. Scan it with the phone or with a PC camera. The peer id is inside
the code.
"""

from __future__ import annotations

import argparse
import logging
import socket
import subprocess
import sys
import time
from pathlib import Path

from cam_vision_bridge import PhoneCamera, local_page_url, show_pairing_qr
from cam_vision_bridge.api.pairing import DEV_PAGE_PORT
from cam_vision_bridge.protocol import Box

_PAGE_WAIT_S = 60.0


def main(argv: list[str] | None = None) -> int:
    """Start one session, show its QR, and publish a fixed box for every frame.

    Args:
        argv: Arguments without the program name. ``None`` reads the process
            command line.

    Returns:
        Process status code. ``0`` after the session closes.
    """
    args = _parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    _ensure_page()
    page_url = args.page_url if args.page_url is not None else local_page_url()
    camera = PhoneCamera(page_url=page_url, capture_size=(args.width, args.height))
    try:
        show_pairing_qr(camera.start())
        for frame in camera.frames():
            print(
                f"frame_id={frame.frame_id} width={frame.width} height={frame.height}",
                flush=True,
            )
            camera.publish(frame, [Box(t="box", x=0.2, y=0.2, w=0.4, h=0.3, label="pc")])
    finally:
        camera.close()
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse an optional page override and the size requested in ``welcome``.

    Args:
        argv: Arguments without the program name.

    Returns:
        Parsed arguments. ``page_url`` is ``None`` when the LAN address should be used.
    """
    parser = argparse.ArgumentParser(description="Show a pairing QR and print frame sizes.")
    parser.add_argument(
        "--page-url",
        default=None,
        help="Override the page address. By default the LAN address of this PC is used.",
    )
    parser.add_argument("--width", type=int, default=640, help="Requested capture width.")
    parser.add_argument("--height", type=int, default=480, help="Requested capture height.")
    return parser.parse_args(argv)


def _ensure_page() -> None:
    """Start the Vite page when nothing is listening on its port.

    Raises:
        SystemExit: If Docker does not bring the port up in time.
    """
    if _port_open(DEV_PAGE_PORT):
        return
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["docker", "compose", "up", "-d", "web"], cwd=root, check=True)
    deadline = time.monotonic() + _PAGE_WAIT_S
    while time.monotonic() < deadline:
        if _port_open(DEV_PAGE_PORT):
            return
        time.sleep(0.5)
    raise SystemExit(f"phone page did not open port {DEV_PAGE_PORT}")


def _port_open(port: int) -> bool:
    """Return whether this computer accepts TCP connections on ``port``."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


if __name__ == "__main__":
    sys.exit(main())
