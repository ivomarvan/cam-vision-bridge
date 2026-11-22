"""Binary frame codec for protocol v1.

One data-channel message is::

    [uint32 big-endian header_len][UTF-8 JSON FrameHeader][JPEG bytes of this part]

``header_len``, ``parts``, ``part``, and ``total_bytes`` are enforced here.
JPEG bytes are not decoded in this module.
"""

from __future__ import annotations

import json
import logging
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import ValidationError

from cam_vision_bridge.protocol.messages import FrameHeader

logger = logging.getLogger(__name__)

HEADER_LEN_MAX = 4096
PARTS_MIN = 1
PARTS_MAX = 256
TOTAL_BYTES_MAX = 8 * 1024 * 1024
INCOMPLETE_FRAME_TTL_S = 2.0
_LENGTH_PREFIX = struct.Struct(">I")


class FrameProtocolError(Exception):
    """A binary frame chunk broke a codec limit.

    Args:
        reason: Stable cause code. Safe to forward to the peer.
        frame_id: Frame the failure belongs to, when the header identified one.
    """

    def __init__(self, reason: str, frame_id: int | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.frame_id = frame_id


def pack_chunk(header: FrameHeader, payload: bytes) -> bytes:
    """Serialize one frame chunk into the length-prefixed wire layout.

    Args:
        header: Chunk metadata. Numeric limits are applied here, not by the model.
        payload: JPEG bytes of this part only.

    Returns:
        The length-prefixed message, ready to send.

    Raises:
        FrameProtocolError: If the header or this payload breaks a codec limit.
    """
    _enforce_chunk_limits(header)
    if len(payload) > header.total_bytes:
        raise FrameProtocolError("payload_sum", frame_id=header.frame_id)
    body = _encode_header(header)
    if len(body) > HEADER_LEN_MAX:
        raise FrameProtocolError("header_too_long", frame_id=header.frame_id)
    return _LENGTH_PREFIX.pack(len(body)) + body + payload


def unpack_chunk(data: bytes) -> tuple[FrameHeader, bytes]:
    """Parse one data-channel message into a header and a payload.

    Args:
        data: Raw binary message. Treated as untrusted.

    Returns:
        The parsed header and this part's payload. The payload is not decoded.

    Raises:
        FrameProtocolError: If the message is shorter than 4 bytes, the header
            exceeds the length limit, the JSON is invalid, or a numeric limit fails.
    """
    if len(data) < _LENGTH_PREFIX.size:
        raise FrameProtocolError("message_too_short")
    header_len = int(_LENGTH_PREFIX.unpack_from(data)[0])
    if header_len > HEADER_LEN_MAX:
        raise FrameProtocolError("header_too_long")
    header_end = _LENGTH_PREFIX.size + header_len
    if len(data) < header_end:
        raise FrameProtocolError("header_truncated")
    header = _decode_header(data[_LENGTH_PREFIX.size : header_end])
    payload = data[header_end:]
    if len(payload) > header.total_bytes:
        raise FrameProtocolError("payload_sum", frame_id=header.frame_id)
    return header, payload


def split_jpeg(
    jpeg: bytes,
    *,
    frame_id: int,
    captured_at: str,
    w: int,
    h: int,
    chunk_bytes: int,
) -> list[bytes]:
    """Split one JPEG into packed chunks.

    Args:
        jpeg: Complete JPEG bytes. Not decoded.
        frame_id: Frame counter carried in every chunk header.
        captured_at: Capture timestamp carried in every chunk header.
        w: Frame width in pixels. Must satisfy ``FrameHeader``.
        h: Frame height in pixels. Must satisfy ``FrameHeader``.
        chunk_bytes: Maximum payload size of one part. ``0`` sends the JPEG
            as a single part.

    Returns:
        Packed wire messages, part 0 first. A length that is an exact multiple
        of ``chunk_bytes`` does not add an empty trailing part.

    Raises:
        ValueError: If ``chunk_bytes`` is negative.
        FrameProtocolError: If the resulting header or part count breaks a limit.
        ValidationError: If ``frame_id``, ``w``, or ``h`` cannot build ``FrameHeader``.
    """
    if chunk_bytes < 0:
        raise ValueError("chunk_bytes must be >= 0")
    slices = _jpeg_slices(jpeg, chunk_bytes)
    parts = len(slices)
    total_bytes = len(jpeg)
    messages: list[bytes] = []
    for part, payload in enumerate(slices):
        header = FrameHeader(
            v=1,
            t="frame",
            frame_id=frame_id,
            captured_at=captured_at,
            w=w,
            h=h,
            part=part,
            parts=parts,
            total_bytes=total_bytes,
        )
        messages.append(pack_chunk(header, payload))
    return messages


class FrameAssembler:
    """Join unordered chunks that share one ``frame_id`` into a JPEG.

    The clock is injected so tests can expire a partial frame without sleeping.
    An incomplete frame older than two seconds is dropped on the next ``add``
    and is not returned.

    Args:
        now: Returns the current time in seconds. Defaults to ``time.monotonic``.
    """

    def __init__(self, now: Callable[[], float] | None = None) -> None:
        self._now = time.monotonic if now is None else now
        self._partials: dict[int, _PartialFrame] = {}

    def add(self, header: FrameHeader, payload: bytes) -> bytes | None:
        """Store one chunk and return the JPEG when every part has arrived.

        A repeated ``part`` is ignored, so a duplicate does not change the
        assembled bytes. The running sum is checked before a new part is
        stored. On error the in-progress frame for this ``frame_id`` is dropped.

        Args:
            header: Chunk metadata.
            payload: JPEG bytes of this part.

        Returns:
            The concatenated JPEG, or ``None`` when parts are still missing.

        Raises:
            FrameProtocolError: On a limit violation, metadata that disagrees
                with an earlier part, or a finished frame whose payload sum is
                not ``total_bytes``.
        """
        self._drop_expired()
        try:
            return self._add_within_limits(header, payload)
        except FrameProtocolError:
            self._partials.pop(header.frame_id, None)
            raise

    def _add_within_limits(self, header: FrameHeader, payload: bytes) -> bytes | None:
        _enforce_chunk_limits(header)
        partial = self._partial_for(header)
        if header.part not in partial.payloads:
            _store_part(partial, header, payload)
        if len(partial.payloads) < partial.parts:
            return None
        self._partials.pop(header.frame_id, None)
        return _join_exact(partial, header.frame_id)

    def _partial_for(self, header: FrameHeader) -> _PartialFrame:
        current = self._partials.get(header.frame_id)
        if current is None:
            created = _PartialFrame(
                parts=header.parts,
                total_bytes=header.total_bytes,
                started_at=self._now(),
            )
            self._partials[header.frame_id] = created
            return created
        if current.parts != header.parts or current.total_bytes != header.total_bytes:
            raise FrameProtocolError("inconsistent_frame", frame_id=header.frame_id)
        return current

    def _drop_expired(self) -> None:
        now = self._now()
        expired = [
            frame_id
            for frame_id, partial in self._partials.items()
            if now - partial.started_at > INCOMPLETE_FRAME_TTL_S
        ]
        for frame_id in expired:
            partial = self._partials.pop(frame_id)
            logger.warning(
                "frame_discarded reason=incomplete_timeout frame_id=%s age_s=%.3f",
                frame_id,
                now - partial.started_at,
            )


@dataclass
class _PartialFrame:
    """Chunks of one frame still waiting for the rest."""

    parts: int
    total_bytes: int
    started_at: float
    payloads: dict[int, bytes] = field(default_factory=dict)


def _store_part(partial: _PartialFrame, header: FrameHeader, payload: bytes) -> None:
    """Append ``payload`` only when the running sum still fits.

    The length check happens before the assignment so a rejected part is never
    retained. One frame must not hold ``parts * total_bytes``.

    Args:
        partial: In-progress frame. Not updated when the check fails.
        header: Chunk metadata. ``frame_id`` is copied onto the error.
        payload: JPEG bytes of this new part.

    Raises:
        FrameProtocolError: If the stored sum plus ``payload`` exceeds ``total_bytes``.
    """
    running = _payload_length_sum(partial.payloads) + len(payload)
    if running > partial.total_bytes:
        raise FrameProtocolError("payload_sum", frame_id=header.frame_id)
    partial.payloads[header.part] = payload


def _join_exact(partial: _PartialFrame, frame_id: int) -> bytes:
    """Return the JPEG when the stored sum equals ``total_bytes``.

    Args:
        partial: Frame whose every part index is present.
        frame_id: Frame copied onto the error when the sum does not match.

    Returns:
        Parts concatenated in index order.

    Raises:
        FrameProtocolError: If the stored sum is not ``total_bytes``.
    """
    if _payload_length_sum(partial.payloads) != partial.total_bytes:
        raise FrameProtocolError("payload_sum", frame_id=frame_id)
    return b"".join(partial.payloads[index] for index in range(partial.parts))


def _payload_length_sum(payloads: dict[int, bytes]) -> int:
    """Return the byte count of stored parts without concatenating them."""
    return sum(len(chunk) for chunk in payloads.values())


def _jpeg_slices(jpeg: bytes, chunk_bytes: int) -> list[bytes]:
    """Split ``jpeg`` into parts. ``chunk_bytes == 0`` keeps a single part."""
    if chunk_bytes == 0 or len(jpeg) == 0:
        return [jpeg]
    return [jpeg[start : start + chunk_bytes] for start in range(0, len(jpeg), chunk_bytes)]


def _encode_header(header: FrameHeader) -> bytes:
    """Serialize ``header`` as compact UTF-8 JSON."""
    encoded: str = json.dumps(
        header.model_dump(mode="json"),
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return encoded.encode("utf-8")


def _decode_header(raw: bytes) -> FrameHeader:
    """Parse and limit-check the JSON header bytes.

    Args:
        raw: Exactly ``header_len`` bytes from the wire.

    Returns:
        A header that already satisfies the numeric codec limits.

    Raises:
        FrameProtocolError: If the bytes are not a v1 frame header inside the limits.
    """
    try:
        parsed: object = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrameProtocolError("invalid_json") from exc
    if not isinstance(parsed, dict):
        raise FrameProtocolError("invalid_json")
    try:
        header = FrameHeader.model_validate(parsed)
    except ValidationError as exc:
        raise FrameProtocolError("invalid_header") from exc
    _enforce_chunk_limits(header)
    return header


def _enforce_chunk_limits(header: FrameHeader) -> None:
    """Reject ``parts``, ``part``, and ``total_bytes`` outside the codec limits.

    Args:
        header: Header already accepted by the model. The model does not apply
            these ranges.

    Raises:
        FrameProtocolError: If a numeric limit fails.
    """
    if not PARTS_MIN <= header.parts <= PARTS_MAX:
        raise FrameProtocolError("parts_out_of_range", frame_id=header.frame_id)
    if not 0 <= header.part < header.parts:
        raise FrameProtocolError("part_out_of_range", frame_id=header.frame_id)
    if header.total_bytes < 0 or header.total_bytes > TOTAL_BYTES_MAX:
        raise FrameProtocolError("total_bytes_out_of_range", frame_id=header.frame_id)
