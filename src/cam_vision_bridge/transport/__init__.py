"""Transport layer: ``Transport``, ``PeerJsWebRtcTransport``, and ``FakeTransport``.

WebRTC data moves JPEG chunks and JSON. ``FakeTransport`` supports in-memory tests.
``PeerJsWebRtcTransport`` is the default network peer used by ``PhoneCamera``.
"""

from cam_vision_bridge.transport.base import Transport
from cam_vision_bridge.transport.fake import FakeTransport
from cam_vision_bridge.transport.peerjs import PeerJsWebRtcTransport, SignalingError

__all__ = ["FakeTransport", "PeerJsWebRtcTransport", "SignalingError", "Transport"]
