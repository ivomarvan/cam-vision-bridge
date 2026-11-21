"""Binary chunk codec for JPEG frames on a WebRTC DataChannel.

Wire format (one DataChannel message)::

    [uint32 big-endian header_len][UTF-8 JSON header][JPEG payload of this part]

The header object is ``t``, ``run_id``, ``frame_id``, ``part``, ``parts``,
``total_bytes``. Limits match the spike contract: untrusted phone input is
rejected here, before any JPEG decode.
"""

from __future__ import annotations

import json
import logging
import re
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

HEADER_LEN_MAX = 4096
PARTS_MIN = 1
PARTS_MAX = 256
TOTAL_BYTES_MAX = 8 * 1024 * 1024
INCOMPLETE_FRAME_TTL_S = 2.0
_HEADER_PREFIX = struct.Struct(">I")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class FrameProtocolError(Exception):
    """A binary frame message violated a spike protocol limit.

    Args:
        reason: Stable machine-readable cause, safe to send to the peer.
        frame_id: Frame the failure belongs to, when the header parsed that far.
    """

    def __init__(self, reason: str, frame_id: int | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.frame_id = frame_id


@dataclass(frozen=True)
class ChunkHeader:
    """Parsed JSON header of one JPEG chunk.

    Attributes:
        run_id: Measurement run identifier. Restricted to a path-safe alphabet.
        frame_id: Frame counter within the run.
        part: Zero-based index of this chunk.
        parts: Total number of chunks. ``1`` means the JPEG was not split.
        total_bytes: Size of the complete JPEG, not of this chunk.
    """

    run_id: str
    frame_id: int
    part: int
    parts: int
    total_bytes: int


def ensure_run_id(run_id: object) -> str:
    """Return ``run_id`` when it cannot escape the results directory.

    Args:
        run_id: Value taken from an untrusted message.

    Returns:
        The same string when it matches ``[A-Za-z0-9_-]{1,64}``.

    Raises:
        ValueError: If ``run_id`` is not a safe path component.
    """
    if type(run_id) is not str or RUN_ID_RE.fullmatch(run_id) is None:
        raise ValueError(f"invalid run_id: {run_id!r}")
    return run_id


def pack_chunk(header: ChunkHeader, payload: bytes) -> bytes:
    """Serialize one chunk into the DataChannel binary layout.

    Args:
        header: Chunk metadata. Must already satisfy the protocol limits.
        payload: JPEG bytes belonging to this part only.

    Returns:
        The length-prefixed message, ready to send.

    Raises:
        FrameProtocolError: If the header or payload breaks a limit.
    """
    _validate_header_fields(
        run_id=header.run_id,
        frame_id=header.frame_id,
        part=header.part,
        parts=header.parts,
        total_bytes=header.total_bytes,
    )
    if len(payload) > header.total_bytes:
        raise FrameProtocolError("payload_size", frame_id=header.frame_id)
    body = _encode_header(header)
    if len(body) > HEADER_LEN_MAX:
        raise FrameProtocolError("header_too_long", frame_id=header.frame_id)
    return _HEADER_PREFIX.pack(len(body)) + body + payload


def unpack_chunk(data: bytes) -> tuple[ChunkHeader, bytes]:
    """Parse one DataChannel message into a header and a payload.

    Args:
        data: Raw binary message from the peer. Treated as untrusted.

    Returns:
        The parsed header and the payload slice (not copied).

    Raises:
        FrameProtocolError: If the message is truncated, the JSON is invalid,
            or a declared limit is exceeded. The payload is not interpreted
            as JPEG here.
    """
    if len(data) < _HEADER_PREFIX.size:
        raise FrameProtocolError("header_too_short")
    (header_len,) = _HEADER_PREFIX.unpack_from(data)
    if type(header_len) is not int or header_len > HEADER_LEN_MAX:
        raise FrameProtocolError("header_too_long")
    header_end = _HEADER_PREFIX.size + header_len
    if len(data) < header_end:
        raise FrameProtocolError("header_truncated")
    try:
        parsed = json.loads(data[_HEADER_PREFIX.size : header_end].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrameProtocolError("invalid_json") from exc
    header = _header_from_json(parsed)
    payload = data[header_end:]
    if len(payload) > header.total_bytes:
        raise FrameProtocolError("payload_size", frame_id=header.frame_id)
    return header, payload


class FrameAssembler:
    """Reassemble unordered chunks into one JPEG per ``(run_id, frame_id)``.

    Incomplete frames older than two seconds are dropped. The clock is
    injected so tests can expire a frame without sleeping.

    Args:
        clock: Returns a monotonic timestamp in seconds.
    """

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = time.monotonic if clock is None else clock
        self._partials: dict[tuple[str, int], _PartialFrame] = {}
        self._expired: list[tuple[str, int]] = []

    def add(self, header: ChunkHeader, payload: bytes) -> bytes | None:
        """Store one chunk and return the JPEG when every part has arrived.

        A repeated ``part`` index is ignored, so a duplicate does not change
        the assembled bytes. Chunks of one frame must agree on ``parts`` and
        ``total_bytes``. A new part whose bytes would push the running sum
        above ``total_bytes`` is not stored: the partial frame is dropped and
        ``FrameProtocolError`` is raised before any ``join``.

        Args:
            header: Chunk metadata.
            payload: JPEG bytes of this part.

        Returns:
            The concatenated JPEG, or ``None`` when parts are still missing.

        Raises:
            FrameProtocolError: On inconsistent metadata or a payload sum that
                exceeds or, once complete, does not equal ``total_bytes``.
        """
        self._drop_expired()
        _validate_header_fields(
            run_id=header.run_id,
            frame_id=header.frame_id,
            part=header.part,
            parts=header.parts,
            total_bytes=header.total_bytes,
        )
        key = (header.run_id, header.frame_id)
        partial = self._partials.get(key)
        if partial is None:
            partial = _PartialFrame(
                parts=header.parts,
                total_bytes=header.total_bytes,
                started_at=self._clock(),
            )
            self._partials[key] = partial
        elif partial.parts != header.parts or partial.total_bytes != header.total_bytes:
            self._partials.pop(key, None)
            raise FrameProtocolError("inconsistent_frame", frame_id=header.frame_id)
        if header.part not in partial.payloads:
            # Check before storing so one frame cannot retain parts * total_bytes.
            running = _payload_sum(partial.payloads) + len(payload)
            if running > partial.total_bytes:
                self._partials.pop(key, None)
                raise FrameProtocolError("payload_size", frame_id=header.frame_id)
            partial.payloads[header.part] = payload
        if len(partial.payloads) < partial.parts:
            return None
        running = _payload_sum(partial.payloads)
        self._partials.pop(key, None)
        if running != partial.total_bytes:
            raise FrameProtocolError("payload_size", frame_id=header.frame_id)
        return b"".join(partial.payloads[index] for index in range(partial.parts))

    def pop_expired(self) -> list[tuple[str, int]]:
        """Return frames dropped for age since the previous call.

        The peer uses this to send ``error`` after a limit violation. The
        list is cleared.

        Returns:
            ``(run_id, frame_id)`` pairs, oldest drop first.
        """
        expired = self._expired
        self._expired = []
        return expired

    def _drop_expired(self) -> None:
        now = self._clock()
        expired = [
            key
            for key, partial in self._partials.items()
            if now - partial.started_at > INCOMPLETE_FRAME_TTL_S
        ]
        for key in expired:
            age_s = now - self._partials[key].started_at
            logger.warning(
                "frame_discarded reason=incomplete_timeout run_id=%s frame_id=%s age_s=%.3f",
                key[0],
                key[1],
                age_s,
            )
            del self._partials[key]
            self._expired.append(key)


@dataclass
class _PartialFrame:
    """Chunks of one frame still waiting for the rest."""

    parts: int
    total_bytes: int
    started_at: float
    payloads: dict[int, bytes] = field(default_factory=dict)


def _payload_sum(payloads: dict[int, bytes]) -> int:
    """Return the byte count of stored chunks without concatenating them."""
    return sum(len(chunk) for chunk in payloads.values())


def _encode_header(header: ChunkHeader) -> bytes:
    # Key order matches the browser packer (T020): t, run_id, frame_id, part, parts, total_bytes.
    document = {
        "t": "frame",
        "run_id": header.run_id,
        "frame_id": header.frame_id,
        "part": header.part,
        "parts": header.parts,
        "total_bytes": header.total_bytes,
    }
    return json.dumps(document, separators=(",", ":")).encode("utf-8")


def _header_from_json(parsed: object) -> ChunkHeader:
    if not isinstance(parsed, dict):
        raise FrameProtocolError("invalid_header")
    if parsed.get("t") != "frame":
        raise FrameProtocolError("invalid_header")
    try:
        run_id = parsed["run_id"]
        frame_id = parsed["frame_id"]
        part = parsed["part"]
        parts = parsed["parts"]
        total_bytes = parsed["total_bytes"]
    except KeyError as exc:
        raise FrameProtocolError("invalid_header") from exc
    _validate_header_fields(
        run_id=run_id,
        frame_id=frame_id,
        part=part,
        parts=parts,
        total_bytes=total_bytes,
    )
    return ChunkHeader(
        run_id=run_id,
        frame_id=frame_id,
        part=part,
        parts=parts,
        total_bytes=total_bytes,
    )


def _validate_header_fields(
    *,
    run_id: object,
    frame_id: object,
    part: object,
    parts: object,
    total_bytes: object,
) -> None:
    known_frame: int | None = frame_id if type(frame_id) is int else None
    try:
        ensure_run_id(run_id)
    except ValueError as exc:
        raise FrameProtocolError("invalid_run_id", frame_id=known_frame) from exc
    if type(frame_id) is not int:
        raise FrameProtocolError("invalid_header")
    if type(parts) is not int or not PARTS_MIN <= parts <= PARTS_MAX:
        raise FrameProtocolError("parts_out_of_range", frame_id=frame_id)
    if type(part) is not int or not 0 <= part < parts:
        raise FrameProtocolError("part_out_of_range", frame_id=frame_id)
    if type(total_bytes) is not int or total_bytes < 0 or total_bytes > TOTAL_BYTES_MAX:
        raise FrameProtocolError("total_bytes_out_of_range", frame_id=frame_id)
