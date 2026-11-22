"""Transport contract for moving JSON and binary data with the phone peer."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Transport(Protocol):
    """Async bridge between ``PhoneCamera`` and a WebRTC (or fake) data channel."""

    async def start(self) -> None:
        """Open signaling and listen for the browser data channel.

        Returns when registration has succeeded, not when the phone has
        connected. ``send_json`` waits until that channel is open.
        """
        ...

    async def send_json(self, payload: dict[str, object]) -> None:
        """Send one protocol JSON object to the phone."""
        ...

    async def receive_bytes(self) -> bytes | None:
        """Receive the next data-channel message.

        Binary payloads are unchanged. Text payloads are UTF-8 bytes.
        ``None`` means the current channel closed.
        """
        ...
