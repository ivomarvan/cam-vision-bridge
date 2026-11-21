"""Unit tests for PeerJS URL, answer, ICE conversion, and registration errors."""

from __future__ import annotations

import asyncio
import json

import pytest

from peerjs_signaling import (
    PeerJsSignaling,
    SignalingError,
    build_answer_message,
    build_peerjs_ws_url,
    ice_candidate_from_payload,
)

pytestmark = pytest.mark.unit

_HOST_LINE = (
    "candidate:842163049 1 udp 1677729535 192.168.1.10 50000 typ host generation 0"
)
_SRFLX_LINE = (
    "candidate:842163049 1 udp 1677724415 203.0.113.5 50001 typ srflx "
    "raddr 192.168.1.10 rport 50000"
)


def test_build_peerjs_ws_url_default_cloud() -> None:
    url = build_peerjs_ws_url(
        host="0.peerjs.com",
        port=443,
        path="/",
        key="peerjs",
        peer_id="cvb-abc",
        token="tok",
        version="1.5.4",
    )
    assert (
        url
        == "wss://0.peerjs.com:443/peerjs?key=peerjs&id=cvb-abc&token=tok&version=1.5.4"
    )


def test_build_peerjs_ws_url_custom_host_port_path_key() -> None:
    url = build_peerjs_ws_url(
        host="signals.example",
        port=9443,
        path="/custom/",
        key="lab",
        peer_id="cvb-1",
        token="tok",
        version="1.5.4",
    )
    assert url == (
        "wss://signals.example:9443/custom/peerjs?key=lab&id=cvb-1&token=tok&version=1.5.4"
    )


def test_build_answer_message_copies_connection_and_dst() -> None:
    offer = {
        "type": "OFFER",
        "src": "phone-1",
        "dst": "cvb-abc",
        "payload": {
            "sdp": {"type": "offer", "sdp": "v=0"},
            "type": "data",
            "connectionId": "conn-9",
            "label": "conn-9",
            "reliable": True,
            "serialization": "raw",
            "metadata": None,
            "browser": "chrome",
        },
    }
    answer = build_answer_message(offer=offer, sdp="v=0-answer")
    assert answer == {
        "type": "ANSWER",
        "dst": "phone-1",
        "payload": {
            "sdp": {"type": "answer", "sdp": "v=0-answer"},
            "type": "data",
            "connectionId": "conn-9",
            "browser": "aiortc",
        },
    }


def test_ice_candidate_from_payload_udp_host() -> None:
    ice = ice_candidate_from_payload(_candidate_payload(_HOST_LINE))
    assert ice is not None
    assert ice.protocol == "udp"
    assert ice.type == "host"
    assert ice.ip == "192.168.1.10"
    assert ice.port == 50000
    assert ice.sdpMid == "0"
    assert ice.sdpMLineIndex == 0


def test_ice_candidate_from_payload_srflx() -> None:
    ice = ice_candidate_from_payload(_candidate_payload(_SRFLX_LINE))
    assert ice is not None
    assert ice.type == "srflx"
    assert ice.protocol == "udp"
    assert ice.ip == "203.0.113.5"
    assert ice.relatedAddress == "192.168.1.10"
    assert ice.relatedPort == 50000


def test_ice_candidate_from_payload_empty_is_none() -> None:
    assert ice_candidate_from_payload(_candidate_payload("")) is None
    assert (
        ice_candidate_from_payload(
            {"candidate": None, "type": "data", "connectionId": "c"}
        )
        is None
    )
    assert ice_candidate_from_payload({"type": "data", "connectionId": "c"}) is None


def test_connect_id_taken_raises_signaling_error() -> None:
    asyncio.run(_expect_registration_error('{"type": "ID-TAKEN"}'))


def test_connect_open_sends_heartbeat() -> None:
    asyncio.run(_expect_heartbeat())


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


def _candidate_payload(line: str) -> dict[str, object]:
    return {
        "candidate": {"candidate": line, "sdpMid": "0", "sdpMLineIndex": 0},
        "type": "data",
        "connectionId": "conn-1",
    }


async def _expect_registration_error(raw: str) -> None:
    socket = _FakeWebSocket([raw])

    async def connector(url: str) -> _FakeWebSocket:
        assert url.startswith("wss://0.peerjs.com:443/peerjs?")
        assert "id=cvb-abc" in url
        assert "token=" in url
        return socket

    signaling = PeerJsSignaling(
        "cvb-abc",
        token="tok",
        version="1.5.4",
        connector=connector,
    )
    with pytest.raises(SignalingError) as caught:
        await signaling.connect()
    assert caught.value.reason == "ID-TAKEN"


async def _expect_heartbeat() -> None:
    socket = _FakeWebSocket(['{"type": "OPEN"}'])

    async def connector(_url: str) -> _FakeWebSocket:
        return socket

    signaling = PeerJsSignaling(
        "cvb-abc",
        token="tok",
        heartbeat_interval=0.01,
        connector=connector,
    )
    await signaling.connect()
    try:
        await asyncio.wait_for(socket.heartbeat.wait(), timeout=1)
    finally:
        await signaling.close()
    assert {"type": "HEARTBEAT"} in [json.loads(item) for item in socket.sent]
