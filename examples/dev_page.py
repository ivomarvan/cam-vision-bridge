"""Start the local phone page used by the examples."""

from __future__ import annotations

import socket
import subprocess
import time
from pathlib import Path

from cam_vision_bridge.api.pairing import DEV_PAGE_PORT

_PAGE_WAIT_S = 60.0


def ensure_page() -> None:
    """Start the Vite page when nothing is listening on its port.

    Raises:
        SystemExit: If Docker does not bring the port up in time.
    """
    if port_open(DEV_PAGE_PORT):
        return
    root = Path(__file__).resolve().parents[1]
    subprocess.run(["docker", "compose", "up", "-d", "web"], cwd=root, check=True)
    deadline = time.monotonic() + _PAGE_WAIT_S
    while time.monotonic() < deadline:
        if port_open(DEV_PAGE_PORT):
            return
        time.sleep(0.5)
    raise SystemExit(f"phone page did not open port {DEV_PAGE_PORT}")


def port_open(port: int) -> bool:
    """Return whether this computer accepts TCP connections on ``port``."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0
