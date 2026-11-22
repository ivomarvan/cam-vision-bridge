"""Parsing tests for protocol v1 JSON messages."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from cam_vision_bridge.protocol import (
    Box,
    ErrorMessage,
    FrameHeader,
    Hello,
    Result,
    Welcome,
    parse_text_message,
)

pytestmark = pytest.mark.unit


def test_parse_text_message_each_tag_round_trips() -> None:
    messages = [
        Hello(
            v=1, t="hello", device_ua="TestAgent/1.0", camera="environment", width=640, height=480
        ),
        Welcome(v=1, t="welcome", width=320, height=240, fps=15),
        ErrorMessage(v=1, t="error", reason="bad frame", frame_id=3),
        FrameHeader(
            v=1,
            t="frame",
            frame_id=0,
            captured_at="2026-11-22T00:00:00+00:00",
            w=1,
            h=1,
            part=0,
            parts=1,
            total_bytes=8,
        ),
        Result(
            v=1,
            t="result",
            frame_id=4,
            items=[Box(t="box", x=0.1, y=0.2, w=0.3, h=0.4, label="qr", score=0.9)],
            processing_ms=12.5,
        ),
    ]
    for message in messages:
        raw = message.model_dump(mode="json")
        assert parse_text_message(raw) == message


def test_parse_text_message_welcome_without_options_is_valid() -> None:
    parsed = parse_text_message({"v": 1, "t": "welcome"})
    assert parsed == Welcome(v=1, t="welcome")


def test_parse_text_message_hello_without_camera_is_valid() -> None:
    parsed = parse_text_message({"v": 1, "t": "hello", "device_ua": "ua", "width": 1, "height": 1})
    assert isinstance(parsed, Hello)
    assert parsed.camera is None


def test_parse_text_message_error_without_frame_id_is_valid() -> None:
    parsed = parse_text_message({"v": 1, "t": "error", "reason": "offline"})
    assert isinstance(parsed, ErrorMessage)
    assert parsed.frame_id is None


def test_frame_header_negative_part_is_valid_before_codec_limits() -> None:
    parsed = parse_text_message(
        {
            "v": 1,
            "t": "frame",
            "frame_id": 0,
            "captured_at": "t",
            "w": 2,
            "h": 2,
            "part": -1,
            "parts": 0,
            "total_bytes": -5,
        }
    )
    assert isinstance(parsed, FrameHeader)
    assert parsed.part == -1


@pytest.mark.parametrize(
    "payload",
    [
        {"v": 2, "t": "hello", "device_ua": "ua", "width": 1, "height": 1},
        {"v": 1, "t": "ping"},
        {"t": "hello", "device_ua": "ua", "width": 1, "height": 1},
        {"v": 1, "t": "hello", "device_ua": "ua", "width": 0, "height": 1},
        {"v": 1, "t": "hello", "device_ua": "ua", "width": 1, "height": 1, "camera": "front"},
        {"v": 1, "t": "hello", "device_ua": "ua", "width": 1, "height": 1, "extra": True},
        {"v": 1, "t": "welcome", "fps": 0},
        {
            "v": 1,
            "t": "frame",
            "frame_id": -1,
            "captured_at": "t",
            "w": 1,
            "h": 1,
            "part": 0,
            "parts": 1,
            "total_bytes": 1,
        },
        {
            "v": 1,
            "t": "frame",
            "frame_id": 0,
            "captured_at": "t",
            "w": 0,
            "h": 1,
            "part": 0,
            "parts": 1,
            "total_bytes": 1,
        },
        {"v": 1, "t": "result", "frame_id": 0, "processing_ms": -0.1, "items": []},
        {
            "v": 1,
            "t": "result",
            "frame_id": 0,
            "processing_ms": 0,
            "items": [{"t": "not-a-shape"}],
        },
    ],
)
def test_parse_text_message_invalid_payload_raises(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        parse_text_message(payload)
