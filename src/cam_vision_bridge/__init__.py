"""``cam_vision_bridge`` — phone camera bridge for computer-vision experiments on PC.

The library pairs a mobile browser with a Python process, delivers the latest JPEG
frame over WebRTC, and accepts structured overlay results for the phone display.
"""

from cam_vision_bridge.api import (
    ConnectionTimeout,
    PhoneCamera,
    TransportNotConfigured,
    local_page_url,
    show_pairing_qr,
)

__version__ = "0.1.0"

__all__ = [
    "ConnectionTimeout",
    "PhoneCamera",
    "TransportNotConfigured",
    "__version__",
    "local_page_url",
    "show_pairing_qr",
]
