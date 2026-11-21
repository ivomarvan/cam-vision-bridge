"""In-process aiortc tests for EchoPeer. No external network."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from aiortc.rtcdatachannel import RTCDataChannel

from echo_peer import EchoPeer
from frame_codec import ChunkHeader, pack_chunk
from results_writer import ResultsWriter

pytestmark = pytest.mark.integration

_CHUNK_BYTES = 16384
_RUN_ID = "r20261121T120000-01"
_FRAME_ID = 7
_STARTED = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


@dataclass
class _Pair:
    offerer: RTCPeerConnection
    channel: RTCDataChannel
    incoming: asyncio.Queue[str | bytes]
    peer: EchoPeer


def test_echo_peer_chunked_jpeg_echoes_and_writes_csv(tmp_path: Path) -> None:
    asyncio.run(asyncio.wait_for(_chunked_jpeg(tmp_path), timeout=20))


def test_echo_peer_invalid_binary_sends_error_and_stays_open(tmp_path: Path) -> None:
    asyncio.run(asyncio.wait_for(_invalid_binary(tmp_path), timeout=20))


def test_echo_peer_running_overshoot_sends_error_and_stays_open(tmp_path: Path) -> None:
    asyncio.run(asyncio.wait_for(_running_overshoot(tmp_path), timeout=20))


async def _chunked_jpeg(tmp_path: Path) -> None:
    pair = await _connect(tmp_path)
    try:
        jpeg = _noisy_jpeg()
        parts = [
            jpeg[index : index + _CHUNK_BYTES]
            for index in range(0, len(jpeg), _CHUNK_BYTES)
        ]
        assert len(parts) >= 2
        pair.channel.send(_run_start())
        for index, payload in enumerate(parts):
            header = ChunkHeader(_RUN_ID, _FRAME_ID, index, len(parts), len(jpeg))
            pair.channel.send(pack_chunk(header, payload))
        echo = json.loads(
            _as_text(await asyncio.wait_for(pair.incoming.get(), timeout=5))
        )
        assert echo["t"] == "echo"
        assert echo["run_id"] == _RUN_ID
        assert echo["frame_id"] == _FRAME_ID
        assert echo["bytes"] == len(jpeg)
        assert echo["parts"] == len(parts)
        assert float(echo["decode_ms"]) >= 0
        pair.channel.send(
            json.dumps(
                {"t": "rtt", "run_id": _RUN_ID, "frame_id": _FRAME_ID, "rtt_ms": 42.5}
            )
        )
        pair.channel.send(
            json.dumps(
                {
                    "t": "run_end",
                    "run_id": _RUN_ID,
                    "frames_sent": 1,
                    "frames_echoed": 1,
                }
            )
        )
        runs, frames = await _wait_csv(tmp_path)
        header = (
            "run_id,started_at,device_ua,mode,width,height,quality,in_flight,chunk_bytes,"
            "duration_s,connect_ms,ice_local_type,ice_remote_type,ice_protocol,frames_sent,"
            "frames_echoed"
        )
        row = (
            f"{_RUN_ID},2026-11-21T12:00:00Z,test-agent,synthetic,640,480,0.8,1,16384,"
            "20.0,15.0,host,host,udp,1,1"
        )
        assert runs.splitlines() == [header, row]
        frame_lines = frames.splitlines()
        assert frame_lines[0] == "frame_id,bytes,parts,rtt_ms,decode_ms"
        frame_id, nbytes, part_count, rtt_ms, decode_ms = frame_lines[1].split(",")
        assert frame_id == str(_FRAME_ID)
        assert nbytes == str(len(jpeg))
        assert part_count == str(len(parts))
        assert rtt_ms == "42.5"
        assert float(decode_ms) >= 0
    finally:
        await _close(pair)


async def _invalid_binary(tmp_path: Path) -> None:
    pair = await _connect(tmp_path)
    try:
        pair.channel.send(b"\x00\x00")
        error = json.loads(
            _as_text(await asyncio.wait_for(pair.incoming.get(), timeout=5))
        )
        assert error["t"] == "error"
        assert "reason" in error
        assert pair.channel.readyState == "open"
    finally:
        await _close(pair)


async def _running_overshoot(tmp_path: Path) -> None:
    pair = await _connect(tmp_path)
    try:
        pair.channel.send(pack_chunk(ChunkHeader(_RUN_ID, 1, 0, 3, 4), b"abcd"))
        pair.channel.send(pack_chunk(ChunkHeader(_RUN_ID, 1, 1, 3, 4), b"efgh"))
        error = json.loads(
            _as_text(await asyncio.wait_for(pair.incoming.get(), timeout=5))
        )
        assert error["t"] == "error"
        assert error["reason"] == "payload_size"
        assert error["frame_id"] == 1
        assert pair.channel.readyState == "open"
    finally:
        await _close(pair)


async def _connect(tmp_path: Path) -> _Pair:
    offerer = RTCPeerConnection(configuration=RTCConfiguration(iceServers=[]))
    channel = offerer.createDataChannel("spike")
    incoming: asyncio.Queue[str | bytes] = asyncio.Queue()
    opened = asyncio.Event()

    @channel.on("open")
    def _on_open() -> None:
        opened.set()

    @channel.on("message")
    def _on_message(message: str | bytes) -> None:
        incoming.put_nowait(message)

    offer = await offerer.createOffer()
    await offerer.setLocalDescription(offer)
    local = offerer.localDescription
    assert local is not None
    signaling = _MemorySignaling()
    peer = EchoPeer(
        peer_id="cvb-testpeer000001",
        signaling=signaling,
        results=ResultsWriter(tmp_path),
        ice_servers=[],
        now=lambda: _STARTED,
    )
    await peer.handle_signaling_message(
        {
            "type": "OFFER",
            "src": "browser-peer",
            "dst": "cvb-testpeer000001",
            "payload": {
                "sdp": {"type": local.type, "sdp": local.sdp},
                "type": "data",
                "connectionId": "conn-1",
                "label": "spike",
                "reliable": True,
                "serialization": "raw",
                "metadata": None,
                "browser": "chrome",
            },
        }
    )
    assert signaling.sent, "EchoPeer did not send an ANSWER"
    answer = signaling.sent[-1]
    await offerer.setRemoteDescription(
        RTCSessionDescription(
            sdp=answer["payload"]["sdp"]["sdp"], type=answer["payload"]["sdp"]["type"]
        )
    )
    await asyncio.wait_for(opened.wait(), timeout=5)
    return _Pair(offerer=offerer, channel=channel, incoming=incoming, peer=peer)


async def _close(pair: _Pair) -> None:
    await pair.peer.close()
    await pair.offerer.close()


async def _wait_csv(tmp_path: Path) -> tuple[str, str]:
    runs_path = tmp_path / "runs.csv"
    frames_path = tmp_path / "frames" / f"{_RUN_ID}.csv"
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 2
    while loop.time() < deadline:
        if runs_path.exists() and frames_path.exists():
            return (
                runs_path.read_text(encoding="utf-8"),
                frames_path.read_text(encoding="utf-8"),
            )
        await asyncio.sleep(0.02)
    raise AssertionError("CSV files were not written")


def _run_start() -> str:
    message: dict[str, Any] = {
        "t": "run_start",
        "run_id": _RUN_ID,
        "config": {
            "mode": "synthetic",
            "width": 640,
            "height": 480,
            "quality": 0.8,
            "in_flight": 1,
            "chunk_bytes": _CHUNK_BYTES,
            "duration_s": 20,
        },
        "device_ua": "test-agent",
        "connect_ms": 15,
        "ice": {"local_type": "host", "remote_type": "host", "protocol": "udp"},
    }
    return json.dumps(message)


def _noisy_jpeg() -> bytes:
    image = np.random.default_rng(0).integers(
        0, 256, size=(480, 640, 3), dtype=np.uint8
    )
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise RuntimeError("jpeg encode failed")
    return encoded.tobytes()


def _as_text(message: str | bytes) -> str:
    if isinstance(message, bytes):
        return message.decode("utf-8")
    return message


class _MemorySignaling:
    """Captures ANSWER messages. Replaces the PeerJS socket inside the test."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send(self, message: dict[str, Any]) -> None:
        self.sent.append(message)
