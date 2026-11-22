"""PhoneCamera over FakeTransport: frames, publish, run, timeout, and close."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager

import cv2
import numpy as np
import pytest

from cam_vision_bridge import (
    ConnectionTimeout,
    PhoneCamera,
    TransportNotConfigured,
    show_pairing_qr,
)
from cam_vision_bridge.core.frame import Frame
from cam_vision_bridge.protocol import Box
from cam_vision_bridge.protocol.frame_codec import split_jpeg
from cam_vision_bridge.protocol.results import ResultItem
from cam_vision_bridge.transport.fake import FakeTransport
from cam_vision_bridge.transport.peerjs import PeerJsWebRtcTransport

pytestmark = pytest.mark.unit

_PAGE = "https://ivomarvan.github.io/cam-vision-bridge/v1/"
_CAPTURED_AT = "2026-11-22T00:00:00+00:00"
_WIDTH = 2
_HEIGHT = 2
_PEER = "cvb-0123456789abcdef"


@contextmanager
def _started(
    *,
    peer_id: str | None = _PEER,
    connect_timeout_s: float | None = 2.0,
    page_url: str = _PAGE,
    capture_size: tuple[int, int] | None = None,
) -> Iterator[tuple[PhoneCamera, FakeTransport]]:
    transport = FakeTransport()
    camera = PhoneCamera(
        transport,
        peer_id=peer_id,
        connect_timeout_s=connect_timeout_s,
        page_url=page_url,
        capture_size=capture_size,
    )
    camera.start()
    try:
        yield camera, transport
    finally:
        camera.close()


def test_package_exports_phone_camera() -> None:
    import cam_vision_bridge

    assert cam_vision_bridge.PhoneCamera is PhoneCamera
    assert cam_vision_bridge.TransportNotConfigured is TransportNotConfigured
    assert cam_vision_bridge.ConnectionTimeout is ConnectionTimeout


def test_phone_camera_without_transport_uses_peerjs() -> None:
    camera = PhoneCamera(peer_id=_PEER)
    try:
        transport = camera._transport
        assert isinstance(transport, PeerJsWebRtcTransport)
        assert transport.signaling_target == ("0.peerjs.com", 443, "/", "peerjs")
        assert transport.heartbeat_interval_s == 5.0
        assert transport.ice_server_urls == ("stun:stun.l.google.com:19302",)
    finally:
        camera.close()


def test_injected_fake_transport_is_not_replaced() -> None:
    fake = FakeTransport()
    camera = PhoneCamera(fake, peer_id=_PEER)
    try:
        assert camera._transport is fake
    finally:
        camera.close()


def test_frames_before_start_raises_runtime_error() -> None:
    camera = PhoneCamera(peer_id=_PEER)
    try:
        with pytest.raises(RuntimeError, match="not started"):
            next(camera.frames())
    finally:
        camera.close()


def test_start_returns_url_and_show_pairing_qr_prints_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    camera = PhoneCamera(FakeTransport(), peer_id=None)
    try:
        url = camera.start()
        quiet = capsys.readouterr().out
        show_pairing_qr(url)
    finally:
        camera.close()
    out = capsys.readouterr().out
    peer = url.split("#peer=", 1)[1]
    assert url == f"{_PAGE}#peer={peer}"
    assert len(peer) == len("cvb-") + 16
    assert peer.startswith("cvb-")
    int(peer.removeprefix("cvb-"), 16)
    assert url not in quiet
    assert url in out
    assert "█" in out


def test_show_pairing_qr_rejects_a_blank_or_multiline_url() -> None:
    with pytest.raises(ValueError, match="single non-empty line"):
        show_pairing_qr("")
    with pytest.raises(ValueError, match="single non-empty line"):
        show_pairing_qr("http://example.test/\n#peer=cvb-aa")


def test_frames_publish_fake_jpeg_result_has_same_frame_id() -> None:
    box = Box(t="box", x=0.1, y=0.2, w=0.3, h=0.4, label="mark")
    with _started() as (camera, transport):
        transport.feed_bytes(_hello())
        transport.feed_bytes(_jpeg(frame_id=7))
        frame = next(camera.frames())
        assert isinstance(frame, Frame)
        assert frame.frame_id == 7
        assert frame.camera == "environment"
        assert frame.image.shape == (_HEIGHT, _WIDTH, 3)
        time.sleep(0.02)
        camera.publish(frame, [box])
        sent = transport.drain_sent_json()

    kinds = [message.get("t") for message in sent]
    assert "welcome" in kinds
    assert "error" not in kinds
    result = next(message for message in sent if message.get("t") == "result")
    assert result["frame_id"] == 7
    assert result["v"] == 1
    processing_ms = result["processing_ms"]
    assert isinstance(processing_ms, int | float)
    assert 5 <= float(processing_ms) <= 2000
    items = result["items"]
    assert isinstance(items, list)
    assert items[0]["t"] == "box"
    assert items[0]["label"] == "mark"


def test_hello_then_welcome_includes_requested_capture_size() -> None:
    with _started(capture_size=(1280, 720), peer_id="cvb-size00000000001") as (camera, transport):
        transport.feed_bytes(_hello())
        transport.feed_bytes(_jpeg(frame_id=1))
        next(camera.frames())
        sent = transport.drain_sent_json()

    welcome = next(message for message in sent if message.get("t") == "welcome")
    assert welcome["v"] == 1
    assert welcome["t"] == "welcome"
    assert welcome["width"] == 1280
    assert welcome["height"] == 720
    assert "fps" not in welcome


def test_capture_size_none_omits_width_and_height_from_welcome() -> None:
    with _started(capture_size=None, peer_id="cvb-nosize000000001") as (camera, transport):
        transport.feed_bytes(_hello())
        transport.feed_bytes(_jpeg(frame_id=1))
        next(camera.frames())
        sent = transport.drain_sent_json()

    welcome = next(message for message in sent if message.get("t") == "welcome")
    assert welcome == {"v": 1, "t": "welcome"}
    assert "width" not in welcome
    assert "height" not in welcome


@pytest.mark.parametrize(
    "capture_size",
    [(0, 480), (-1, 480), (1280, 0), (1.5, 480), (1280, "720"), (True, 480)],
)
def test_invalid_capture_size_raises_value_error_before_transport_starts(
    capture_size: tuple[object, object],
) -> None:
    transport = FakeTransport()
    with pytest.raises(ValueError, match="capture_size"):
        PhoneCamera(transport, peer_id=_PEER, capture_size=capture_size)  # type: ignore[arg-type]
    assert transport._loop is None


def test_run_callback_result_is_sent_on_fake_transport() -> None:
    box = Box(t="box", x=0.0, y=0.0, w=1.0, h=1.0)
    errors: list[BaseException] = []
    published = threading.Event()
    with _started(peer_id="cvb-run0000000000001") as (camera, transport):
        transport.feed_bytes(_hello())
        transport.feed_bytes(_jpeg(frame_id=3))
        original = camera.publish

        def publish(frame: Frame, items: Sequence[ResultItem]) -> None:
            original(frame, items)
            published.set()

        camera.publish = publish  # type: ignore[method-assign]

        def callback(frame: Frame) -> list[Box]:
            assert frame.frame_id == 3
            return [box]

        worker = threading.Thread(
            target=_run_collecting,
            args=(camera, callback, errors),
        )
        worker.start()
        assert published.wait(timeout=2.0)
        sent = transport.drain_sent_json()
        camera.close()
        worker.join(timeout=2.0)

    assert errors == []
    assert not worker.is_alive()
    result = next(message for message in sent if message.get("t") == "result")
    assert result["frame_id"] == 3


def test_close_while_waiting_ends_frames_without_another_frame() -> None:
    errors: list[BaseException] = []
    frames: list[Frame] = []
    with _started(connect_timeout_s=None, peer_id="cvb-close0000000001") as (camera, _transport):
        worker = threading.Thread(target=_collect_frames, args=(camera, frames, errors))
        worker.start()
        worker.join(timeout=0.05)
        camera.close()
        worker.join(timeout=2.0)

    assert errors == []
    assert frames == []
    assert not worker.is_alive()


def test_run_callback_runtime_error_propagates() -> None:
    with _started(peer_id="cvb-error0000000001") as (camera, transport):
        transport.feed_bytes(_hello())
        transport.feed_bytes(_jpeg(frame_id=9))

        def callback(_frame: Frame) -> list[Box]:
            raise RuntimeError("user failed")

        with pytest.raises(RuntimeError, match="user failed"):
            camera.run(callback)


def test_frames_without_data_raises_connection_timeout() -> None:
    camera = PhoneCamera(
        FakeTransport(),
        peer_id="cvb-timeout00000001",
        connect_timeout_s=0.05,
    )
    camera.start()
    try:
        started = time.monotonic()
        with pytest.raises(ConnectionTimeout):
            next(camera.frames())
        assert time.monotonic() - started < 1.5
    finally:
        camera.close()


def test_invalid_chunk_sends_error_and_later_frame_arrives(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("WARNING")
    with _started(peer_id="cvb-bad000000000001") as (camera, transport):
        transport.feed_bytes(b"\x00\x00")
        transport.feed_bytes(_jpeg(frame_id=42))
        frame = next(camera.frames())
        sent = transport.drain_sent_json()

    assert frame.frame_id == 42
    errors = [message for message in sent if message.get("t") == "error"]
    assert errors[0]["reason"] == "message_too_short"
    assert any("frame_protocol_error" in record.message for record in caplog.records)


def _run_collecting(
    camera: PhoneCamera,
    callback: Callable[[Frame], Sequence[ResultItem]],
    errors: list[BaseException],
) -> None:
    try:
        camera.run(callback)
    except BaseException as exc:  # runner reports failures to the test thread
        errors.append(exc)


def _collect_frames(
    camera: PhoneCamera,
    frames: list[Frame],
    errors: list[BaseException],
) -> None:
    try:
        frames.extend(camera.frames())
    except BaseException as exc:  # close must end the iterator, not raise
        errors.append(exc)


def _hello() -> bytes:
    payload = {
        "v": 1,
        "t": "hello",
        "device_ua": "test",
        "camera": "environment",
        "width": _WIDTH,
        "height": _HEIGHT,
    }
    return json.dumps(payload).encode("utf-8")


def _jpeg(*, frame_id: int) -> bytes:
    image = np.full((_HEIGHT, _WIDTH, 3), 128, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    chunks = split_jpeg(
        encoded.tobytes(),
        frame_id=frame_id,
        captured_at=_CAPTURED_AT,
        w=_WIDTH,
        h=_HEIGHT,
        chunk_bytes=0,
    )
    assert len(chunks) == 1
    return chunks[0]
