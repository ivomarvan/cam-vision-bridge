"""Pydantic models for protocol v1 JSON messages.

Every JSON object in the protocol has ``v`` and ``t``. That includes the frame
header carried inside a binary chunk. JPEG bytes are not a message. ``part``,
``parts``, and ``total_bytes`` stay unconstrained here; the frame codec applies
the size limits before those bytes are trusted.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import Field, TypeAdapter

from cam_vision_bridge.protocol.results import ResultItem, _ProtocolModel

_PositiveInt = Annotated[int, Field(ge=1)]
_FrameId = Annotated[int, Field(ge=0)]
_NonNegativeMs = Annotated[float, Field(ge=0)]


class Hello(_ProtocolModel):
    """Phone handshake: user-agent, camera facing, and capture size."""

    v: Literal[1]
    t: Literal["hello"]
    device_ua: str
    camera: Literal["user", "environment"] | None = None
    width: _PositiveInt
    height: _PositiveInt


class Welcome(_ProtocolModel):
    """PC reply: optional requested capture size and frame rate."""

    v: Literal[1]
    t: Literal["welcome"]
    width: int | None = None
    height: int | None = None
    fps: _PositiveInt | None = None


class ErrorMessage(_ProtocolModel):
    """Failure notice the phone can show. The connection stays up."""

    v: Literal[1]
    t: Literal["error"]
    reason: str
    frame_id: _FrameId | None = None


class FrameHeader(_ProtocolModel):
    """JSON header of one binary frame chunk.

    ``part``, ``parts``, and ``total_bytes`` are plain integers in this model.
    Range checks belong to the frame codec, which runs before JPEG decode.
    """

    v: Literal[1]
    t: Literal["frame"]
    frame_id: _FrameId
    captured_at: str
    w: _PositiveInt
    h: _PositiveInt
    part: int
    parts: int
    total_bytes: int


class Result(_ProtocolModel):
    """Overlay payload for one frame: items plus time spent processing it."""

    v: Literal[1]
    t: Literal["result"]
    frame_id: _FrameId
    items: list[ResultItem]
    processing_ms: _NonNegativeMs


Message: TypeAlias = Hello | Welcome | ErrorMessage | FrameHeader | Result
TextMessage: TypeAlias = Annotated[Message, Field(discriminator="t")]

_TEXT_MESSAGE_ADAPTER: TypeAdapter[Message] = TypeAdapter(TextMessage)


def parse_text_message(payload: Mapping[str, Any]) -> Message:
    """Parse one v1 JSON message.

    Args:
        payload: JSON object already decoded to a mapping. ``v`` must be 1 and
            ``t`` must be a known message tag.

    Returns:
        The message model selected by ``t``.

    Raises:
        ValidationError: If ``t`` is unknown, ``v`` is not 1, or a field is invalid.
            Nothing is returned for a payload that does not match.
    """
    return _TEXT_MESSAGE_ADAPTER.validate_python(payload)
