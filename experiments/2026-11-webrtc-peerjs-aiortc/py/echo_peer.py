"""aiortc answerer that echoes JPEG frames and records spike measurements.

The browser creates the DataChannel. For each PeerJS ``OFFER`` this peer
builds one ``RTCPeerConnection``, answers, and accepts trickle candidates
that arrived early. A later offer replaces the previous connection.

Binary input is untrusted: chunk limits are enforced before ``cv2.imdecode``.
A bad message is logged and answered with ``error``; the channel stays open.
"""

from __future__ import annotations

import json
import logging
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import cv2
import numpy as np
from aiortc import (
    RTCConfiguration,
    RTCDataChannel,
    RTCIceCandidate,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)
from aiortc.exceptions import (
    InternalError,
    InvalidAccessError,
    InvalidStateError,
    OperationError,
)

from frame_codec import (
    TOTAL_BYTES_MAX,
    ChunkHeader,
    FrameAssembler,
    FrameProtocolError,
    ensure_run_id,
    unpack_chunk,
)
from peerjs_signaling import (
    SignalingError,
    build_answer_message,
    ice_candidate_from_payload,
    peerjs_ice_servers,
)
from results_writer import ResultsWriter

logger = logging.getLogger(__name__)

_MODES = frozenset({"synthetic", "camera"})
# Failures a hostile offer or DataChannel payload is allowed to provoke.
_NEGOTIATE_ERRORS = (
    SignalingError,
    InternalError,
    InvalidAccessError,
    InvalidStateError,
    OperationError,
    AssertionError,
    ValueError,
    TypeError,
    OSError,
)
_CHANNEL_ERRORS = (cv2.error, InvalidStateError, ValueError, TypeError, OSError)


class SignalingSender(Protocol):
    """Sink for signaling messages this peer sends to the PeerJS server."""

    async def send(self, message: Mapping[str, Any]) -> None:
        """Send one JSON signaling message.

        Args:
            message: Object with ``type`` and, for an answer, ``dst``.
        """


class PeerMessageError(Exception):
    """A text DataChannel message failed validation.

    Args:
        reason: Stable code returned to the browser in an ``error`` message.
        frame_id: Frame the failure refers to, when the message carried one.
    """

    def __init__(self, reason: str, frame_id: int | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.frame_id = frame_id


@dataclass
class _RunRecord:
    """Fields of ``run_start`` kept until ``run_end`` writes ``runs.csv``."""

    started_at: str
    device_ua: str
    mode: str
    width: int
    height: int
    quality: float
    in_flight: int
    chunk_bytes: int
    duration_s: float
    connect_ms: float
    ice_local_type: str
    ice_remote_type: str
    ice_protocol: str


class EchoPeer:
    """Answer PeerJS data offers and echo decoded JPEG frames.

    Args:
        peer_id: Local PeerJS id. Used only in logs.
        signaling: Where ``ANSWER`` messages are sent.
        results: CSV writer for ``run_end`` and ``rtt``.
        ice_servers: ICE servers for new peer connections. ``None`` selects
            the PeerJS defaults. An empty list keeps gathering on host
            candidates only (in-process tests).
        now: Clock for ``started_at``. Tests inject a fixed UTC time.
        monotonic: Clock for the frame assembler's two-second timeout.
    """

    def __init__(
        self,
        peer_id: str,
        signaling: SignalingSender,
        results: ResultsWriter,
        *,
        ice_servers: Sequence[RTCIceServer] | None = None,
        now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        self._peer_id = peer_id
        self._signaling = signaling
        self._results = results
        self._ice_servers = list(
            peerjs_ice_servers() if ice_servers is None else ice_servers
        )
        self._now = _utc_now if now is None else now
        self._monotonic = time.monotonic if monotonic is None else monotonic
        self._connections: dict[str, RTCPeerConnection] = {}
        self._assemblers: dict[str, FrameAssembler] = {}
        self._pending: dict[str, list[RTCIceCandidate]] = {}
        self._runs: dict[str, _RunRecord] = {}
        self._echoes: dict[tuple[str, int], tuple[int, int, float]] = {}

    async def handle_signaling_message(self, message: Mapping[str, Any]) -> None:
        """Apply one server message (``OFFER``, ``CANDIDATE``, ``LEAVE``).

        Args:
            message: Decoded PeerJS server message. Malformed input is logged
                and ignored so the signaling loop keeps running.
        """
        msg_type = message.get("type")
        if msg_type == "OFFER":
            await self._handle_offer(message)
        elif msg_type == "CANDIDATE":
            await self._handle_candidate(message)
        elif msg_type == "LEAVE":
            logger.info(
                "signaling_leave peer_id=%s src=%s", self._peer_id, message.get("src")
            )
            await self.close()
        elif msg_type == "EXPIRE":
            logger.warning("signaling_expire peer_id=%s", self._peer_id)
        else:
            logger.debug(
                "signaling_ignored type=%s peer_id=%s", msg_type, self._peer_id
            )

    async def close(self) -> None:
        """Close every peer connection this answerer still holds."""
        connection_ids = list(self._connections)
        for connection_id in connection_ids:
            await self._discard_connection(connection_id, reason="close")
        self._pending.clear()

    async def _handle_offer(self, message: Mapping[str, Any]) -> None:
        payload = message.get("payload")
        if not isinstance(payload, Mapping):
            logger.warning(
                "offer_rejected reason=bad_payload peer_id=%s", self._peer_id
            )
            return
        connection_id = payload.get("connectionId")
        sdp_obj = payload.get("sdp")
        if not isinstance(connection_id, str) or not isinstance(sdp_obj, Mapping):
            logger.warning(
                "offer_rejected reason=missing_fields peer_id=%s", self._peer_id
            )
            return
        sdp = sdp_obj.get("sdp")
        if not isinstance(sdp, str) or sdp_obj.get("type") != "offer":
            logger.warning(
                "offer_rejected reason=bad_sdp connection_id=%s", connection_id
            )
            return
        queued = self._pending.pop(connection_id, [])
        await self._replace_existing_connections()
        pc = RTCPeerConnection(
            configuration=RTCConfiguration(iceServers=list(self._ice_servers))
        )
        self._connections[connection_id] = pc
        self._assemblers[connection_id] = FrameAssembler(clock=self._monotonic)
        self._watch_states(pc, connection_id)
        self._bind_datachannel(pc, connection_id)
        try:
            await self._negotiate(pc, connection_id, sdp, queued, message)
        except _NEGOTIATE_ERRORS as exc:
            # Remote SDP is untrusted. A bad offer must not kill the process.
            logger.warning(
                "offer_rejected reason=negotiate connection_id=%s error=%s",
                connection_id,
                exc,
            )
            await self._discard_connection(connection_id, reason="negotiate_failed")

    async def _negotiate(
        self,
        pc: RTCPeerConnection,
        connection_id: str,
        sdp: str,
        queued: list[RTCIceCandidate],
        offer: Mapping[str, Any],
    ) -> None:
        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="offer"))
        for ice in queued:
            await pc.addIceCandidate(ice)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        local = pc.localDescription
        if local is None or not local.sdp:
            raise SignalingError("no_local_description")
        await self._signaling.send(build_answer_message(offer=offer, sdp=local.sdp))
        logger.info(
            "answer_sent connection_id=%s peer_id=%s", connection_id, self._peer_id
        )

    async def _handle_candidate(self, message: Mapping[str, Any]) -> None:
        payload = message.get("payload")
        if not isinstance(payload, Mapping):
            logger.warning(
                "candidate_rejected reason=bad_payload peer_id=%s", self._peer_id
            )
            return
        connection_id = payload.get("connectionId")
        if not isinstance(connection_id, str):
            logger.warning("candidate_rejected reason=missing_connection_id")
            return
        try:
            ice = ice_candidate_from_payload(payload)
        except SignalingError as exc:
            logger.warning(
                "candidate_rejected reason=%s connection_id=%s",
                exc.reason,
                connection_id,
            )
            return
        if ice is None:
            logger.debug(
                "candidate_ignored reason=end_of_candidates connection_id=%s",
                connection_id,
            )
            return
        pc = self._connections.get(connection_id)
        if pc is None:
            # CANDIDATE may arrive before OFFER. Hold it until that offer is negotiated.
            self._pending.setdefault(connection_id, []).append(ice)
            logger.info("candidate_queued connection_id=%s", connection_id)
            return
        await pc.addIceCandidate(ice)

    async def _replace_existing_connections(self) -> None:
        for connection_id in list(self._connections):
            await self._discard_connection(connection_id, reason="replaced")
        self._pending.clear()

    async def _discard_connection(self, connection_id: str, *, reason: str) -> None:
        pc = self._connections.pop(connection_id, None)
        self._assemblers.pop(connection_id, None)
        if pc is None:
            return
        logger.info(
            "peer_connection_closed connection_id=%s reason=%s",
            connection_id,
            reason,
        )
        await pc.close()

    def _watch_states(self, pc: RTCPeerConnection, connection_id: str) -> None:
        @pc.on("connectionstatechange")
        def _on_connection_state() -> None:
            logger.info(
                "peer_connection_state connection_id=%s state=%s",
                connection_id,
                pc.connectionState,
            )

        @pc.on("iceconnectionstatechange")
        def _on_ice_state() -> None:
            logger.info(
                "ice_connection_state connection_id=%s state=%s",
                connection_id,
                pc.iceConnectionState,
            )

    def _bind_datachannel(self, pc: RTCPeerConnection, connection_id: str) -> None:
        @pc.on("datachannel")
        def _on_datachannel(channel: RTCDataChannel) -> None:
            logger.info(
                "datachannel_received connection_id=%s label=%s",
                connection_id,
                channel.label,
            )

            @channel.on("message")
            def _on_message(message: str | bytes) -> None:
                self._on_datachannel_message(channel, connection_id, message)

    def _on_datachannel_message(
        self,
        channel: RTCDataChannel,
        connection_id: str,
        message: str | bytes,
    ) -> None:
        try:
            if isinstance(message, bytes):
                self._on_binary(channel, connection_id, message)
            elif isinstance(message, str):
                self._on_text(channel, message)
            else:
                logger.warning("datachannel_rejected reason=unsupported_type")
                self._send_error(channel, "unsupported_type")
        except _CHANNEL_ERRORS as exc:
            # A bad payload must not tear the DataChannel down.
            logger.error("datachannel_handler_failed error=%s", exc)
            self._send_error(channel, "internal")

    def _on_binary(
        self, channel: RTCDataChannel, connection_id: str, data: bytes
    ) -> None:
        assembler = self._assemblers.get(connection_id)
        if assembler is None:
            logger.warning(
                "frame_rejected reason=no_assembler connection_id=%s", connection_id
            )
            self._send_error(channel, "no_assembler")
            return
        try:
            header, payload = unpack_chunk(data)
            jpeg = assembler.add(header, payload)
        except FrameProtocolError as exc:
            self._send_expired(channel, assembler)
            logger.warning(
                "frame_rejected reason=%s frame_id=%s", exc.reason, exc.frame_id
            )
            self._send_error(channel, exc.reason, frame_id=exc.frame_id)
            return
        self._send_expired(channel, assembler)
        if jpeg is None:
            return
        self._echo_jpeg(channel, header, jpeg)

    def _send_expired(self, channel: RTCDataChannel, assembler: FrameAssembler) -> None:
        """Tell the browser about frames dropped for exceeding the 2s limit."""
        for run_id, frame_id in assembler.pop_expired():
            logger.warning(
                "frame_rejected reason=incomplete_timeout run_id=%s frame_id=%s",
                run_id,
                frame_id,
            )
            self._send_error(channel, "incomplete_timeout", frame_id=frame_id)

    def _echo_jpeg(
        self, channel: RTCDataChannel, header: ChunkHeader, jpeg: bytes
    ) -> None:
        # Plan limits are checked again at the decode boundary. unpack/assembler
        # already rejected oversized input; this is the last gate before OpenCV.
        if len(jpeg) != header.total_bytes or len(jpeg) > TOTAL_BYTES_MAX:
            logger.warning(
                "frame_rejected reason=payload_size frame_id=%s",
                header.frame_id,
            )
            self._send_error(channel, "payload_size", frame_id=header.frame_id)
            return
        started = time.perf_counter()
        try:
            image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        except cv2.error as exc:
            logger.warning(
                "frame_rejected reason=jpeg_decode frame_id=%s error=%s",
                header.frame_id,
                exc,
            )
            self._send_error(channel, "jpeg_decode", frame_id=header.frame_id)
            return
        decode_ms = round((time.perf_counter() - started) * 1000.0, 3)
        if image is None:
            logger.warning(
                "frame_rejected reason=jpeg_decode frame_id=%s", header.frame_id
            )
            self._send_error(channel, "jpeg_decode", frame_id=header.frame_id)
            return
        self._echoes[(header.run_id, header.frame_id)] = (
            header.total_bytes,
            header.parts,
            decode_ms,
        )
        logger.info(
            "frame_echoed run_id=%s frame_id=%s bytes=%s parts=%s decode_ms=%.3f",
            header.run_id,
            header.frame_id,
            header.total_bytes,
            header.parts,
            decode_ms,
        )
        self._send_json(
            channel,
            {
                "t": "echo",
                "run_id": header.run_id,
                "frame_id": header.frame_id,
                "bytes": header.total_bytes,
                "parts": header.parts,
                "decode_ms": decode_ms,
            },
        )

    def _on_text(self, channel: RTCDataChannel, text: str) -> None:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("text_rejected reason=invalid_json")
            self._send_error(channel, "invalid_json")
            return
        if not isinstance(parsed, dict):
            logger.warning("text_rejected reason=invalid_json")
            self._send_error(channel, "invalid_json")
            return
        kind = parsed.get("t")
        try:
            if kind == "run_start":
                self._on_run_start(parsed)
            elif kind == "rtt":
                self._on_rtt(parsed)
            elif kind == "run_end":
                self._on_run_end(parsed)
            else:
                raise PeerMessageError("unknown_type")
        except PeerMessageError as exc:
            logger.warning("text_rejected reason=%s", exc.reason)
            self._send_error(channel, exc.reason, frame_id=exc.frame_id)

    def _on_run_start(self, message: Mapping[str, Any]) -> None:
        run_id = _require_run_id(message.get("run_id"))
        config = message.get("config")
        ice = message.get("ice")
        if not isinstance(config, Mapping) or not isinstance(ice, Mapping):
            raise PeerMessageError("bad_fields")
        mode = _as_str(config.get("mode"))
        if mode not in _MODES:
            raise PeerMessageError("bad_mode")
        record = _RunRecord(
            started_at=_format_utc(self._now()),
            device_ua=_as_str(message.get("device_ua")),
            mode=mode,
            width=_as_int(config.get("width")),
            height=_as_int(config.get("height")),
            quality=_as_float(config.get("quality")),
            in_flight=_as_int(config.get("in_flight")),
            chunk_bytes=_as_int(config.get("chunk_bytes")),
            duration_s=_as_float(config.get("duration_s")),
            connect_ms=_as_float(message.get("connect_ms")),
            ice_local_type=_as_str(ice.get("local_type")),
            ice_remote_type=_as_str(ice.get("remote_type")),
            ice_protocol=_as_str(ice.get("protocol")),
        )
        self._runs[run_id] = record
        logger.info("run_started run_id=%s mode=%s", run_id, mode)

    def _on_rtt(self, message: Mapping[str, Any]) -> None:
        run_id = _require_run_id(message.get("run_id"))
        frame_id = _as_int(message.get("frame_id"))
        rtt_ms = _as_float(message.get("rtt_ms"))
        remembered = self._echoes.get((run_id, frame_id))
        if remembered is None:
            raise PeerMessageError("unknown_frame", frame_id=frame_id)
        nbytes, parts, decode_ms = remembered
        self._results.append_frame(
            run_id,
            frame_id=frame_id,
            nbytes=nbytes,
            parts=parts,
            rtt_ms=rtt_ms,
            decode_ms=decode_ms,
        )

    def _on_run_end(self, message: Mapping[str, Any]) -> None:
        run_id = _require_run_id(message.get("run_id"))
        record = self._runs.get(run_id)
        if record is None:
            raise PeerMessageError("unknown_run")
        self._results.append_run(
            run_id=run_id,
            started_at=record.started_at,
            device_ua=record.device_ua,
            mode=record.mode,
            width=record.width,
            height=record.height,
            quality=record.quality,
            in_flight=record.in_flight,
            chunk_bytes=record.chunk_bytes,
            duration_s=record.duration_s,
            connect_ms=record.connect_ms,
            ice_local_type=record.ice_local_type,
            ice_remote_type=record.ice_remote_type,
            ice_protocol=record.ice_protocol,
            frames_sent=_as_int(message.get("frames_sent")),
            frames_echoed=_as_int(message.get("frames_echoed")),
        )
        logger.info("run_finished run_id=%s", run_id)

    def _send_error(
        self,
        channel: RTCDataChannel,
        reason: str,
        frame_id: int | None = None,
    ) -> None:
        payload: dict[str, object] = {"t": "error", "reason": reason}
        if frame_id is not None:
            payload["frame_id"] = frame_id
        self._send_json(channel, payload)

    def _send_json(
        self, channel: RTCDataChannel, payload: Mapping[str, object]
    ) -> None:
        if channel.readyState != "open":
            logger.warning("datachannel_not_open state=%s", channel.readyState)
            return
        try:
            channel.send(json.dumps(dict(payload), separators=(",", ":")))
        except (InvalidStateError, ValueError) as exc:
            logger.warning("datachannel_send_failed error=%s", exc)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _format_utc(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise PeerMessageError("bad_clock")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_run_id(value: object) -> str:
    try:
        return ensure_run_id(value)
    except ValueError as exc:
        raise PeerMessageError("invalid_run_id") from exc


def _as_int(value: object) -> int:
    if type(value) is not int:
        raise PeerMessageError("bad_number")
    return value


def _as_float(value: object) -> float:
    if type(value) not in (int, float):
        raise PeerMessageError("bad_number")
    number = float(value)
    if not math.isfinite(number):
        raise PeerMessageError("bad_number")
    return number


def _as_str(value: object) -> str:
    if type(value) is not str:
        raise PeerMessageError("bad_fields")
    return value
