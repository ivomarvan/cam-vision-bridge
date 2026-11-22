"""Public synchronous API: ``PhoneCamera`` with ``frames()``, ``publish()``, and ``run()``.

Runs an asyncio event loop on a background thread behind a thread-safe façade (DECISIONS #1).
"""

from cam_vision_bridge.api.pairing import local_page_url, show_pairing_qr
from cam_vision_bridge.api.phone_camera import (
    ConnectionTimeout,
    PhoneCamera,
    TransportNotConfigured,
)

__all__ = [
    "ConnectionTimeout",
    "PhoneCamera",
    "TransportNotConfigured",
    "local_page_url",
    "show_pairing_qr",
]
