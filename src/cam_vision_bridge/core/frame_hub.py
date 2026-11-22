"""Asynchronous hub that keeps only the newest complete frame."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Literal

import cv2
import numpy as np

from cam_vision_bridge.core.frame import Frame
from cam_vision_bridge.protocol.frame_codec import (
    FrameAssembler,
    FrameProtocolError,
    unpack_chunk,
)
from cam_vision_bridge.protocol.messages import FrameHeader

logger = logging.getLogger(__name__)

ProtocolErrorCallback = Callable[[str, int | None], None]


class FrameHubClosed(Exception):
    """Raised when ``wait_frame`` is unblocked because the hub was closed."""


class FrameHub:
    """Assembles JPEG chunks and exposes only the latest complete ``Frame``.

    Invalid wire data is logged and forwarded through ``on_protocol_error``; it is
    never passed to ``cv2.imdecode``. When a newer complete frame arrives before the
    current pending one is consumed, the older pending frame is discarded.

    Args:
        on_protocol_error: Optional hook for codec failures.
        camera: Camera facing from the phone handshake, copied onto each ``Frame``.
    """

    def __init__(
        self,
        *,
        on_protocol_error: ProtocolErrorCallback | None = None,
        camera: Literal["user", "environment"] | None = None,
    ) -> None:
        self._on_protocol_error = on_protocol_error
        self._camera = camera
        self._assembler = FrameAssembler()
        self._pending: Frame | None = None
        self._closed = False
        self._ready = asyncio.Event()

    @property
    def camera(self) -> Literal["user", "environment"] | None:
        """Camera facing from the handshake; propagated to decoded frames."""
        return self._camera

    @camera.setter
    def camera(self, value: Literal["user", "environment"] | None) -> None:
        self._camera = value

    def ingest_chunk(self, data: bytes) -> None:
        """Parse one binary chunk and publish a frame when the JPEG is complete.

        Args:
            data: Raw length-prefixed frame message from the transport.
        """
        try:
            header, payload = unpack_chunk(data)
        except FrameProtocolError as exc:
            self._notify_protocol_error(exc.reason, exc.frame_id)
            return

        try:
            jpeg = self._assembler.add(header, payload)
        except FrameProtocolError as exc:
            self._notify_protocol_error(exc.reason, exc.frame_id)
            return

        if jpeg is None:
            return

        try:
            frame = self._decode_jpeg(jpeg, header)
        except FrameProtocolError as exc:
            self._notify_protocol_error(exc.reason, exc.frame_id)
            return

        self._publish_pending(frame)

    async def wait_frame(self) -> Frame:
        """Return the newest complete frame that has not been handed out yet.

        Returns:
            The next unclaimed ``Frame``.

        Raises:
            FrameHubClosed: After ``close()`` when no frame is pending.
        """
        while True:
            if self._closed and self._pending is None:
                raise FrameHubClosed()
            if self._pending is not None:
                frame = self._pending
                self._pending = None
                if self._pending is None:
                    self._ready.clear()
                return frame
            await self._ready.wait()

    def close(self) -> None:
        """Shut down the hub and unblock any task waiting in ``wait_frame``."""
        self._closed = True
        self._ready.set()

    def _publish_pending(self, frame: Frame) -> None:
        self._pending = frame
        self._ready.set()

    def _notify_protocol_error(self, reason: str, frame_id: int | None) -> None:
        logger.warning(
            "frame_protocol_error reason=%s frame_id=%s",
            reason,
            frame_id,
        )
        if self._on_protocol_error is not None:
            self._on_protocol_error(reason, frame_id)

    def _decode_jpeg(self, jpeg: bytes, header: FrameHeader) -> Frame:
        """Decode complete JPEG bytes into an immutable RGB ``Frame``.

        Args:
            jpeg: Concatenated JPEG from ``FrameAssembler``.
            header: Metadata for the assembled frame.

        Returns:
            A frozen ``Frame`` with an RGB ndarray.

        Raises:
            FrameProtocolError: When OpenCV cannot decode the buffer.
        """
        buffer = np.frombuffer(jpeg, dtype=np.uint8)
        bgr = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if bgr is None:
            raise FrameProtocolError("invalid_jpeg", frame_id=header.frame_id)
        rgb = np.asarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)
        return Frame(
            image=rgb,
            frame_id=header.frame_id,
            captured_at=header.captured_at,
            width=header.w,
            height=header.h,
            camera=self._camera,
        )
