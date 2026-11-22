"""Tests for Frame assembly, FrameHub flow, and FakeTransport."""

from __future__ import annotations

import asyncio

import cv2
import numpy as np
import pytest

from cam_vision_bridge.core.frame import Frame
from cam_vision_bridge.core.frame_hub import FrameHub, FrameHubClosed
from cam_vision_bridge.protocol.frame_codec import split_jpeg
from cam_vision_bridge.transport.fake import FakeTransport

pytestmark = pytest.mark.unit

_CAPTURED_AT = "2026-11-22T00:00:00+00:00"
_WIDTH = 2
_HEIGHT = 2


def test_frame_is_frozen_rgb_metadata() -> None:
    image = np.zeros((_HEIGHT, _WIDTH, 3), dtype=np.uint8)
    frame = Frame(
        image=image,
        frame_id=1,
        captured_at=_CAPTURED_AT,
        width=_WIDTH,
        height=_HEIGHT,
        camera="user",
    )
    assert frame.image.shape == (_HEIGHT, _WIDTH, 3)
    assert frame.camera == "user"
    with pytest.raises(AttributeError):
        frame.frame_id = 2  # type: ignore[misc]


def test_frame_hub_one_jpeg_wait_frame_returns_rgb_shape() -> None:
    hub = FrameHub(camera="environment")
    chunk = _packed_2x2_jpeg(frame_id=10)

    hub.ingest_chunk(chunk)
    frame = asyncio.run(hub.wait_frame())

    assert frame.frame_id == 10
    assert frame.width == _WIDTH
    assert frame.height == _HEIGHT
    assert frame.image.shape == (_HEIGHT, _WIDTH, 3)
    assert frame.image.dtype == np.uint8
    assert frame.camera == "environment"


def test_frame_hub_two_complete_frames_before_wait_returns_newer() -> None:
    hub = FrameHub()
    older = _packed_2x2_jpeg(frame_id=1)
    newer = _packed_2x2_jpeg(frame_id=2, pixel_value=200)

    hub.ingest_chunk(older)
    hub.ingest_chunk(newer)
    frame = asyncio.run(hub.wait_frame())

    assert frame.frame_id == 2
    assert int(frame.image[0, 0, 0]) == 200


def test_frame_hub_invalid_chunk_calls_error_callback_without_imdecode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_imdecode = cv2.imdecode
    decode_calls: list[int] = []

    def tracking_imdecode(buf: object, flags: int) -> object:
        decode_calls.append(1)
        return real_imdecode(buf, flags)  # type: ignore[arg-type]

    monkeypatch.setattr(cv2, "imdecode", tracking_imdecode)
    errors: list[tuple[str, int | None]] = []

    hub = FrameHub(on_protocol_error=lambda reason, fid: errors.append((reason, fid)))
    hub.ingest_chunk(b"\x00\x00\x01")  # shorter than 4 bytes

    assert errors == [("message_too_short", None)]
    assert decode_calls == []

    async def wait_then_recover() -> Frame:
        task = asyncio.create_task(hub.wait_frame())
        await asyncio.sleep(0.02)
        assert not task.done()
        hub.ingest_chunk(_packed_2x2_jpeg(frame_id=42))
        return await task

    frame = asyncio.run(wait_then_recover())

    assert frame.frame_id == 42
    assert frame.image.shape == (_HEIGHT, _WIDTH, 3)
    assert len(decode_calls) == 1


def test_frame_hub_close_wakes_waiter() -> None:
    hub = FrameHub()

    async def wait_and_close() -> None:
        task = asyncio.create_task(hub.wait_frame())
        await asyncio.sleep(0.01)
        hub.close()
        with pytest.raises(FrameHubClosed):
            await task

    asyncio.run(wait_and_close())


def test_fake_transport_queues_without_network() -> None:
    transport = FakeTransport()

    async def exercise() -> None:
        await transport.start()
        transport.feed_bytes(b"\x01\x02")
        received = await transport.receive_bytes()
        assert received == b"\x01\x02"
        await transport.send_json({"v": 1, "t": "welcome"})
        transport.close_inbound()
        assert await transport.receive_bytes() is None
        assert transport.drain_sent_json() == [{"v": 1, "t": "welcome"}]

    asyncio.run(exercise())


def _packed_2x2_jpeg(*, frame_id: int, pixel_value: int = 128) -> bytes:
    image = np.full((_HEIGHT, _WIDTH, 3), pixel_value, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    jpeg = encoded.tobytes()
    chunks = split_jpeg(
        jpeg,
        frame_id=frame_id,
        captured_at=_CAPTURED_AT,
        w=_WIDTH,
        h=_HEIGHT,
        chunk_bytes=0,
    )
    assert len(chunks) == 1
    return chunks[0]
