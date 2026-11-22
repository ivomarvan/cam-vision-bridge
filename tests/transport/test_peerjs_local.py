"""PeerJS transport: local aiortc session, candidate queue, registration errors.

Nothing in this module opens a socket to ``0.peerjs.com``. The integration
session passes SDP and candidates in memory. Registration tests use a fake
WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import socket
from typing import Any

import cv2
import numpy as np
import pytest
from aiortc import RTCConfiguration, RTCDataChannel, RTCPeerConnection, RTCSessionDescription

from cam_vision_bridge.protocol.frame_codec import split_jpeg
from cam_vision_bridge.transport.peerjs import (
    HEARTBEAT_INTERVAL_S,
    PeerJsWebRtcTransport,
    SignalingError,
    build_peerjs_ws_url,
    parse_offer,
)

_PEER = "cvb-0123456789abcdef"
_HOST_LINE = "candidate:842163049 1 udp 1677729535 192.168.1.10 50000 typ host generation 0"
_CAPTURED_AT = "2026-11-22T00:00:00+00:00"


@pytest.fixture(autouse=True)
def _forbid_public_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail if a test resolves or opens the public PeerJS broker."""

    async def _blocked(url: str) -> None:
        raise AssertionError(f"test opened a signaling socket: {url}")

    original = socket.getaddrinfo

    def _guarded(*args: Any, **kwargs: Any) -> Any:
        host = args[0] if args else kwargs.get("host")
        if host == "0.peerjs.com":
            raise AssertionError("test resolved 0.peerjs.com")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        "cam_vision_bridge.transport.peerjs._open_peerjs_socket",
        _blocked,
    )
    monkeypatch.setattr(socket, "getaddrinfo", _guarded)


@pytest.mark.unit
def test_default_signaling_target_and_stun() -> None:
    transport = PeerJsWebRtcTransport(peer_id=_PEER)
    assert transport.signaling_target == ("0.peerjs.com", 443, "/", "peerjs")
    assert transport.heartbeat_interval_s == HEARTBEAT_INTERVAL_S == 5.0
    assert transport.ice_server_urls == ("stun:stun.l.google.com:19302",)


@pytest.mark.unit
def test_build_peerjs_ws_url_custom_host_port_path_key() -> None:
    url = build_peerjs_ws_url(
        host="signals.example",
        port=9443,
        path="/custom/",
        key="lab",
        peer_id=_PEER,
        token="tok",
        version="1.5.4",
    )
    assert url == (
        f"wss://signals.example:9443/custom/peerjs?key=lab&id={_PEER}&token=tok&version=1.5.4"
    )


@pytest.mark.unit
def test_parse_offer_without_browser_field() -> None:
    message = _offer_message(sdp="v=0\r\n", connection_id="conn-1")
    assert "browser" not in message["payload"]
    offer = parse_offer(message)
    assert offer.connection_id == "conn-1"
    assert offer.src == "phone"
    assert offer.sdp == "v=0\r\n"


@pytest.mark.unit
def test_parse_offer_ignores_browser_when_present() -> None:
    message = _offer_message(sdp="v=0\r\n", connection_id="conn-1")
    message["payload"]["browser"] = "chrome"
    offer = parse_offer(message)
    assert offer.connection_id == "conn-1"


@pytest.mark.unit
def test_offer_without_connection_id_raises_and_creates_no_peer() -> None:
    asyncio.run(_offer_without_connection_id())


@pytest.mark.unit
def test_candidate_before_offer_is_queued_and_empty_is_ignored() -> None:
    asyncio.run(_queue_candidate_before_offer())


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    ['{"type": "ID-TAKEN"}', '{"type": "INVALID-KEY"}', '{"type": "ERROR"}'],
)
def test_registration_error_raises_signaling_error(raw: str) -> None:
    asyncio.run(_expect_registration_error(raw))


@pytest.mark.unit
def test_open_sends_heartbeat_on_fake_socket() -> None:
    asyncio.run(_expect_heartbeat())


@pytest.mark.integration
def test_local_offer_answer_forwards_chunk_and_refuses_second_offer() -> None:
    asyncio.run(_local_offer_answer())


async def _offer_without_connection_id() -> None:
    transport = PeerJsWebRtcTransport(peer_id=_PEER, ice_servers=[])
    message = _offer_message(sdp="v=0\r\n", connection_id="conn-1")
    del message["payload"]["connectionId"]
    try:
        with pytest.raises(SignalingError) as caught:
            await transport.handle_signaling_message(message)
        assert caught.value.reason == "bad_offer"
        assert transport.live_connection_count() == 0
    finally:
        await transport.close()


async def _queue_candidate_before_offer() -> None:
    transport = PeerJsWebRtcTransport(peer_id=_PEER, ice_servers=[])
    try:
        await transport.handle_signaling_message(_candidate_message(_HOST_LINE, "conn-1"))
        await transport.handle_signaling_message(_candidate_message("", "conn-1"))
        await transport.handle_signaling_message(_candidate_message("not-a-candidate", "conn-1"))
        assert transport.queued_candidate_count("conn-1") == 1
        assert transport.live_connection_count() == 0
    finally:
        await transport.close()


async def _expect_registration_error(raw: str) -> None:
    socket_fake = _FakeWebSocket([raw])

    async def connector(url: str) -> _FakeWebSocket:
        assert url.startswith("wss://0.peerjs.com:443/peerjs?")
        assert f"id={_PEER}" in url
        assert "token=" in url
        return socket_fake

    transport = PeerJsWebRtcTransport(peer_id=_PEER, token="tok", connector=connector)
    expected = json.loads(raw)["type"]
    try:
        with pytest.raises(SignalingError) as caught:
            await transport.start()
        assert caught.value.reason == expected
    finally:
        await transport.close()


async def _expect_heartbeat() -> None:
    socket_fake = _FakeWebSocket(['{"type": "OPEN"}'])

    async def connector(_url: str) -> _FakeWebSocket:
        return socket_fake

    transport = PeerJsWebRtcTransport(
        peer_id=_PEER,
        token="tok",
        heartbeat_interval_s=0.01,
        connector=connector,
    )
    await transport.start()
    try:
        await asyncio.wait_for(socket_fake.heartbeat.wait(), timeout=1)
    finally:
        await transport.close()
    sent = [json.loads(item) for item in socket_fake.sent]
    assert {"type": "HEARTBEAT"} in sent


async def _local_offer_answer() -> None:
    chunk = _chunk()
    transport = PeerJsWebRtcTransport(peer_id=_PEER, ice_servers=[])
    offerer = RTCPeerConnection(configuration=RTCConfiguration(iceServers=[]))
    incoming: asyncio.Queue[str | bytes] = asyncio.Queue()
    try:
        channel, offer_sdp = await _connect_pair(offerer, transport, incoming)
        await _assert_forwarded_payloads(transport, channel, incoming, chunk)
        await _assert_second_offer_refused(transport, channel, offer_sdp, chunk)
    finally:
        await offerer.close()
        await transport.close()


async def _connect_pair(
    offerer: RTCPeerConnection,
    transport: PeerJsWebRtcTransport,
    incoming: asyncio.Queue[str | bytes],
) -> tuple[RTCDataChannel, str]:
    channel, opened = _listen(offerer, incoming)
    offer_sdp = await _local_description(offerer)
    await _send_early_candidates(transport, offer_sdp)
    assert transport.queued_candidate_count("conn-1") == len(_candidate_lines(offer_sdp))
    offer = _offer_message(sdp=_sdp_without_candidates(offer_sdp), connection_id="conn-1")
    assert "browser" not in offer["payload"]
    await transport.handle_signaling_message(offer)
    assert transport.queued_candidate_count("conn-1") == 0
    await _apply_answer(offerer, transport)
    await asyncio.wait_for(opened.wait(), timeout=5)
    return channel, offer_sdp


async def _assert_forwarded_payloads(
    transport: PeerJsWebRtcTransport,
    channel: RTCDataChannel,
    incoming: asyncio.Queue[str | bytes],
    chunk: bytes,
) -> None:
    channel.send(chunk)
    assert await asyncio.wait_for(transport.receive_bytes(), timeout=5) == chunk
    hello = '{"v":1,"t":"hello"}'
    channel.send(hello)
    assert await asyncio.wait_for(transport.receive_bytes(), timeout=5) == hello.encode()
    welcome = {"v": 1, "t": "welcome"}
    await transport.send_json(welcome)
    reply = await asyncio.wait_for(incoming.get(), timeout=5)
    assert reply == json.dumps(welcome, ensure_ascii=False, separators=(",", ":"))


async def _assert_second_offer_refused(
    transport: PeerJsWebRtcTransport,
    channel: RTCDataChannel,
    offer_sdp: str,
    chunk: bytes,
) -> None:
    await transport.handle_signaling_message(_offer_message(sdp=offer_sdp, connection_id="conn-2"))
    assert transport.pending_answer_count() == 0
    assert transport.live_connection_count() == 1
    channel.send(chunk)
    assert await asyncio.wait_for(transport.receive_bytes(), timeout=5) == chunk
    assert channel.readyState == "open"


async def _send_early_candidates(transport: PeerJsWebRtcTransport, sdp: str) -> None:
    for line in _candidate_lines(sdp):
        await transport.handle_signaling_message(_candidate_message(line, "conn-1"))
    await transport.handle_signaling_message(_candidate_message("", "conn-1"))


async def _apply_answer(offerer: RTCPeerConnection, transport: PeerJsWebRtcTransport) -> None:
    answer = await asyncio.wait_for(transport.wait_answer(), timeout=5)
    payload = answer["payload"]
    assert payload["browser"] == "aiortc"
    assert payload["connectionId"] == "conn-1"
    sdp_obj = payload["sdp"]
    await offerer.setRemoteDescription(
        RTCSessionDescription(sdp=sdp_obj["sdp"], type=sdp_obj["type"])
    )


def _listen(
    offerer: RTCPeerConnection,
    incoming: asyncio.Queue[str | bytes],
) -> tuple[RTCDataChannel, asyncio.Event]:
    channel = offerer.createDataChannel("cam")
    opened = asyncio.Event()

    @channel.on("open")
    def _on_open() -> None:
        opened.set()

    @channel.on("message")
    def _on_message(message: str | bytes) -> None:
        incoming.put_nowait(message)

    return channel, opened


async def _local_description(offerer: RTCPeerConnection) -> str:
    offer = await offerer.createOffer()
    await offerer.setLocalDescription(offer)
    local = offerer.localDescription
    assert local is not None
    return local.sdp


def _candidate_lines(sdp: str) -> list[str]:
    return [line[2:] for line in sdp.splitlines() if line.startswith("a=candidate:")]


def _sdp_without_candidates(sdp: str) -> str:
    kept = [
        line
        for line in sdp.splitlines()
        if not line.startswith("a=candidate:") and line != "a=end-of-candidates"
    ]
    return "\r\n".join(kept) + "\r\n"


def _offer_message(*, sdp: str, connection_id: str) -> dict[str, Any]:
    return {
        "type": "OFFER",
        "src": "phone",
        "dst": _PEER,
        "payload": {
            "sdp": {"type": "offer", "sdp": sdp},
            "type": "data",
            "connectionId": connection_id,
            "metadata": None,
            "label": "cam",
            "reliable": False,
            "serialization": "raw",
        },
    }


def _candidate_message(line: str, connection_id: str) -> dict[str, Any]:
    return {
        "type": "CANDIDATE",
        "src": "phone",
        "dst": _PEER,
        "payload": {
            "candidate": {"candidate": line, "sdpMid": "0", "sdpMLineIndex": 0},
            "type": "data",
            "connectionId": connection_id,
        },
    }


def _chunk() -> bytes:
    image = np.full((2, 2, 3), 128, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert bool(ok)
    chunks = split_jpeg(
        encoded.tobytes(),
        frame_id=7,
        captured_at=_CAPTURED_AT,
        w=2,
        h=2,
        chunk_bytes=0,
    )
    assert len(chunks) == 1
    return chunks[0]


class _FakeWebSocket:
    """In-memory socket. The first queued message is the registration reply."""

    def __init__(self, messages: list[str]) -> None:
        self._incoming: asyncio.Queue[str | None] = asyncio.Queue()
        for message in messages:
            self._incoming.put_nowait(message)
        self.sent: list[str] = []
        self.heartbeat = asyncio.Event()

    async def recv(self) -> str:
        item = await self._incoming.get()
        if item is None:
            raise ConnectionError("closed")
        return item

    async def send(self, data: str) -> None:
        self.sent.append(data)
        if json.loads(data).get("type") == "HEARTBEAT":
            self.heartbeat.set()

    async def close(self) -> None:
        await self._incoming.put(None)
