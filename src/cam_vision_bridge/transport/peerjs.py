"""PeerJS signaling client and aiortc answerer behind ``Transport``.

The browser creates the data channel and sends protocol v1. This module
registers with the PeerJS broker, answers one data ``OFFER``, and forwards
data-channel payloads as bytes. It does not parse JSON or reassemble JPEGs.

The experiment under ``experiments/`` is not imported. That code speaks the
spike echo protocol; production messages are protocol v1 and are handled
above this layer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

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
from aiortc.sdp import candidate_from_sdp
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)

# Emulated PeerJS client. 1.5.4 data offers have no ``browser`` field (DECISIONS #6).
PEERJS_CLIENT_VERSION = "1.5.4"
DEFAULT_SIGNALING_HOST = "0.peerjs.com"
DEFAULT_SIGNALING_PORT = 443
DEFAULT_SIGNALING_PATH = "/"
DEFAULT_SIGNALING_KEY = "peerjs"
DEFAULT_STUN_URL = "stun:stun.l.google.com:19302"
HEARTBEAT_INTERVAL_S = 5.0
_OPEN_TIMEOUT_S = 10.0
_ERROR_TYPES = frozenset({"ID-TAKEN", "INVALID-KEY", "ERROR"})
_CANDIDATE_PREFIX = "candidate:"
# ``disconnected`` can recover. A second offer is refused until failed or closed.
_DEAD_CONNECTION_STATES = frozenset({"failed", "closed"})

# Pattern: Adapter — PeerJS broker plus one aiortc answerer, exposed as Transport.
Connector = Callable[[str], Awaitable[Any]]


class SignalingError(Exception):
    """The PeerJS server or an offer rejected this peer.

    Args:
        reason: Stable cause (``ID-TAKEN``, ``INVALID-KEY``, ``ERROR``,
            ``bad_offer``, ``connect_failed``, or ``negotiate_failed``).
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


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
# One bad trickle candidate must not abort the offer.
_ADD_CANDIDATE_ERRORS = (
    InternalError,
    InvalidAccessError,
    InvalidStateError,
    OperationError,
    AssertionError,
    ValueError,
    TypeError,
    OSError,
)


@dataclass(frozen=True)
class OfferDetails:
    """Fields taken from a PeerJS 1.5.4 data offer.

    ``browser`` is intentionally absent: that version does not send it.
    """

    src: str
    connection_id: str
    sdp: str


@dataclass
class PendingCandidates:
    """Trickle candidates that arrived before the offer for their connection.

    Helper owned only by ``PeerJsWebRtcTransport``. One class per file would
    split this buffer from the only object that applies it.
    """

    _items: dict[str, list[RTCIceCandidate]] = field(default_factory=dict)

    def add(self, connection_id: str, candidate: RTCIceCandidate) -> None:
        """Append ``candidate`` until the matching offer is negotiated."""
        self._items.setdefault(connection_id, []).append(candidate)

    def pop(self, connection_id: str) -> list[RTCIceCandidate]:
        """Remove and return every candidate queued for ``connection_id``."""
        return self._items.pop(connection_id, [])

    def count(self, connection_id: str) -> int:
        """Return how many candidates are waiting for ``connection_id``."""
        return len(self._items.get(connection_id, []))


def build_peerjs_ws_url(
    *,
    host: str,
    port: int,
    path: str,
    key: str,
    peer_id: str,
    token: str,
    version: str,
) -> str:
    """Build the PeerJS registration WebSocket URL.

    Args:
        host: Signaling host, without a scheme.
        port: TCP port. The scheme is always ``wss``.
        path: Path prefix. The cloud default is ``/`` and ``peerjs`` is appended.
        key: PeerJS API key.
        peer_id: Id this peer registers under.
        token: Random client token. It travels only in this URL and is not logged.
        version: PeerJS client version being emulated.

    Returns:
        Absolute ``wss`` URL including the query string.
    """
    query = urlencode((("key", key), ("id", peer_id), ("token", token), ("version", version)))
    return f"wss://{host}:{port}{path}peerjs?{query}"


def parse_offer(message: Mapping[str, Any]) -> OfferDetails:
    """Read a PeerJS 1.5.4 data ``OFFER``.

    A ``browser`` field is not required. When present it is ignored.

    Args:
        message: Server message whose ``type`` is ``OFFER``.

    Returns:
        The source peer, connection id, and SDP offer text.

    Raises:
        SignalingError: If ``src``, ``connectionId``, or the SDP offer is unusable.
    """
    payload = message.get("payload")
    src = message.get("src")
    if not isinstance(payload, Mapping) or not isinstance(src, str) or src == "":
        raise SignalingError("bad_offer")
    return _offer_from_payload(src, payload)


def build_answer_message(*, src: str, connection_id: str, sdp: str) -> dict[str, Any]:
    """Build the ``ANSWER`` for one data offer.

    Args:
        src: Peer id that sent the offer. Copied to ``dst``.
        connection_id: ``connectionId`` from the offer.
        sdp: SDP answer from ``RTCPeerConnection.localDescription``.

    Returns:
        A signaling object. ``browser`` is ``aiortc``; PeerJS 1.5.4 ignores it
        and reads the SDP.
    """
    return {
        "type": "ANSWER",
        "dst": src,
        "payload": {
            "sdp": {"type": "answer", "sdp": sdp},
            "type": "data",
            "connectionId": connection_id,
            "browser": "aiortc",
        },
    }


def ice_candidate_from_payload(payload: Mapping[str, Any]) -> RTCIceCandidate | None:
    """Convert a PeerJS ``CANDIDATE`` payload into an aiortc candidate.

    Args:
        payload: ``CANDIDATE.payload``. An empty candidate string ends trickle ICE.

    Returns:
        A candidate with ``sdpMid`` and ``sdpMLineIndex`` filled in, or ``None``
        when the browser signaled the end of candidates.

    Raises:
        SignalingError: If the candidate line cannot be parsed.
    """
    candidate_obj = payload.get("candidate")
    if not isinstance(candidate_obj, Mapping):
        return None
    line = candidate_obj.get("candidate")
    if not isinstance(line, str):
        return None
    stripped = _strip_candidate_prefix(line)
    if stripped is None:
        return None
    ice = _parse_candidate_line(stripped)
    _copy_candidate_ids(ice, candidate_obj)
    return ice


class PeerJsWebRtcTransport:
    """Answer one browser data channel and move bytes for ``PhoneCamera``.

    ``start`` finishes when the broker sends ``OPEN``. The phone connects
    afterwards, which is what makes the pairing QR useful. A second ``OFFER``
    is refused while that peer connection is alive.

    Args:
        peer_id: Id to register. ``PhoneCamera`` may set it later via
            ``use_peer_id`` before ``start``.
        host: Signaling host.
        port: Signaling port.
        path: Path prefix. The cloud default is ``/``.
        key: PeerJS API key.
        ice_servers: ICE servers for the answerer. ``None`` selects Google STUN.
            An empty list keeps gathering on host candidates (in-process tests).
        connector: Awaitable ``(url) -> websocket``. Tests inject a fake so the
            suite never opens a socket to the public broker.
        heartbeat_interval_s: Seconds between ``HEARTBEAT`` messages.
        token: Registration token. Generated when omitted and never logged.
    """

    _peer_id: str | None
    _host: str
    _port: int
    _path: str
    _key: str
    _ice_servers: list[RTCIceServer]
    _connector: Connector
    _heartbeat_interval_s: float
    _token: str
    _pending: PendingCandidates
    _inbound: asyncio.Queue[bytes | None]
    _answers: asyncio.Queue[dict[str, Any]]
    _lock: asyncio.Lock
    _send_lock: asyncio.Lock
    _channel_open: asyncio.Event
    _ws: Any
    _pc: RTCPeerConnection | None
    _channel: RTCDataChannel | None
    _connection_id: str | None
    _reader_task: asyncio.Task[None] | None
    _heartbeat_task: asyncio.Task[None] | None
    _registered: bool
    _closed: bool
    _signaled_close: bool

    def __init__(
        self,
        peer_id: str | None = None,
        *,
        host: str = DEFAULT_SIGNALING_HOST,
        port: int = DEFAULT_SIGNALING_PORT,
        path: str = DEFAULT_SIGNALING_PATH,
        key: str = DEFAULT_SIGNALING_KEY,
        ice_servers: Sequence[RTCIceServer] | None = None,
        connector: Connector | None = None,
        heartbeat_interval_s: float = HEARTBEAT_INTERVAL_S,
        token: str | None = None,
    ) -> None:
        _validate_endpoint(host, path, key, heartbeat_interval_s, token)
        self._bind_config(
            host,
            port,
            path,
            key,
            ice_servers,
            connector,
            heartbeat_interval_s,
            token,
        )
        self._reset_runtime()
        if peer_id is not None:
            self.use_peer_id(peer_id)

    def _bind_config(
        self,
        host: str,
        port: int,
        path: str,
        key: str,
        ice_servers: Sequence[RTCIceServer] | None,
        connector: Connector | None,
        heartbeat_interval_s: float,
        token: str | None,
    ) -> None:
        """Store signaling options. The registration token is not logged."""
        self._peer_id = None
        self._host = host
        self._port = port
        self._path = path
        self._key = key
        self._ice_servers = _ice_servers(ice_servers)
        self._connector = _open_peerjs_socket if connector is None else connector
        self._heartbeat_interval_s = heartbeat_interval_s
        self._token = secrets.token_hex(16) if token is None else token

    def _reset_runtime(self) -> None:
        """Create the queues and clear any peer connection."""
        self._pending = PendingCandidates()
        self._inbound = asyncio.Queue()
        self._answers = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._send_lock = asyncio.Lock()
        self._channel_open = asyncio.Event()
        self._ws = None
        self._pc = None
        self._channel = None
        self._connection_id = None
        self._reader_task = None
        self._heartbeat_task = None
        self._registered = False
        self._closed = False
        self._signaled_close = False

    @property
    def signaling_target(self) -> tuple[str, int, str, str]:
        """Return ``(host, port, path, key)`` used for registration."""
        return (self._host, self._port, self._path, self._key)

    @property
    def heartbeat_interval_s(self) -> float:
        """Return the delay between ``HEARTBEAT`` messages."""
        return self._heartbeat_interval_s

    @property
    def ice_server_urls(self) -> tuple[str, ...]:
        """Return the ICE server URLs configured for the answerer."""
        return _ice_urls(self._ice_servers)

    def use_peer_id(self, peer_id: str) -> None:
        """Set the id registered by ``start``.

        ``PhoneCamera`` calls this so the pairing URL and the broker id match.

        Args:
            peer_id: Non-empty id without whitespace or ``#``.

        Raises:
            RuntimeError: If registration has already started.
            ValueError: If ``peer_id`` cannot be placed in the pairing URL.
        """
        if self._registered:
            raise RuntimeError("peer id is already registered")
        if peer_id == "" or "#" in peer_id or any(char.isspace() for char in peer_id):
            raise ValueError("peer_id must be non-empty and must not contain whitespace or '#'")
        self._peer_id = peer_id

    def live_connection_count(self) -> int:
        """Return 1 when an offer is in progress or the peer connection is up."""
        return 1 if self._is_alive() else 0

    def queued_candidate_count(self, connection_id: str) -> int:
        """Return how many trickle candidates are waiting for ``connection_id``."""
        return self._pending.count(connection_id)

    def pending_answer_count(self) -> int:
        """Return how many ``ANSWER`` messages have not been read yet."""
        return self._answers.qsize()

    async def wait_answer(self) -> dict[str, Any]:
        """Return the next ``ANSWER`` this peer built.

        In-process tests read this instead of a PeerJS socket.

        Returns:
            The signaling object passed to the broker, including SDP.
        """
        return await self._answers.get()

    async def start(self) -> None:
        """Register with PeerJS and return when the server sends ``OPEN``.

        The data channel opens later, when the browser sends ``OFFER``.
        ``send_json`` waits for that channel.

        Raises:
            SignalingError: If the peer id is missing, the broker rejects the
                registration, or the socket fails.
            RuntimeError: If the transport was already started or is closed.
        """
        self._require_startable()
        try:
            await self._register()
        except SignalingError:
            await self.close()
            raise
        self._reader_task = asyncio.create_task(self._read_loop(), name="peerjs-read")
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(),
            name="peerjs-heartbeat",
        )

    async def send_json(self, payload: dict[str, object]) -> None:
        """Send one JSON object as a text data-channel message.

        Args:
            payload: Protocol object. Serialized here and not interpreted.

        Raises:
            SignalingError: If the data channel is not open.
            TypeError: If ``payload`` is not JSON serializable.
        """
        channel = await self._require_channel()
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        try:
            channel.send(text)
        except InvalidStateError as exc:
            raise SignalingError("datachannel_not_open") from exc

    async def receive_bytes(self) -> bytes | None:
        """Return the next data-channel payload, or ``None`` when it closes.

        Binary messages are unchanged. Text messages are UTF-8 bytes so the
        caller can distinguish JSON from a frame chunk. JPEG parts are not
        reassembled here.

        Returns:
            Raw bytes, or ``None`` once after the current channel closes.
        """
        return await self._inbound.get()

    async def handle_signaling_message(self, message: Mapping[str, Any]) -> None:
        """Apply one broker message (``OFFER``, ``CANDIDATE``, ``LEAVE``).

        In-process tests call this with SDP and candidates and do not open a
        WebSocket. A bad ``OFFER`` raises; other malformed input is logged.

        Args:
            message: Decoded PeerJS server message.

        Raises:
            SignalingError: If an ``OFFER`` has no usable ``connectionId`` or SDP,
                or negotiation of a well-formed offer fails.
        """
        msg_type = message.get("type")
        if msg_type == "OFFER":
            await self._handle_offer(message)
            return
        if msg_type == "CANDIDATE":
            await self._handle_candidate(message)
            return
        if msg_type == "LEAVE":
            await self._on_leave()
            return
        if msg_type == "EXPIRE":
            logger.warning("signaling_expire peer_id=%s", self._peer_id)
            return
        if msg_type in _ERROR_TYPES:
            raise SignalingError(str(msg_type))
        logger.debug("signaling_ignored type=%s peer_id=%s", msg_type, self._peer_id)

    async def close(self) -> None:
        """Stop signaling and the peer connection. Further calls do nothing."""
        if self._closed:
            return
        self._closed = True
        await self._cancel_background()
        async with self._lock:
            await self._drop_peer_unlocked(reason="close")
        await self._close_socket()
        self._signal_inbound_closed()

    def _require_startable(self) -> None:
        if self._closed:
            raise RuntimeError("transport is closed")
        if self._registered:
            raise RuntimeError("transport already started")
        if self._peer_id is None:
            raise SignalingError("missing_peer_id")

    async def _register(self) -> None:
        peer_id = self._peer_id
        if peer_id is None:
            raise SignalingError("missing_peer_id")
        url = build_peerjs_ws_url(
            host=self._host,
            port=self._port,
            path=self._path,
            key=self._key,
            peer_id=peer_id,
            token=self._token,
            version=PEERJS_CLIENT_VERSION,
        )
        # The URL contains the token. Log the host and id only.
        logger.info(
            "signaling_connecting host=%s port=%s peer_id=%s",
            self._host,
            self._port,
            peer_id,
        )
        raw = await self._recv_registration(url)
        self._accept_registration(raw)

    async def _recv_registration(self, url: str) -> str | bytes:
        try:
            self._ws = await self._connector(url)
            raw = await self._ws.recv()
        except (WebSocketException, OSError) as exc:
            logger.error(
                "signaling_connect_failed host=%s peer_id=%s error=%s",
                self._host,
                self._peer_id,
                exc,
            )
            raise SignalingError("connect_failed") from exc
        if not isinstance(raw, str | bytes):
            raise SignalingError("invalid_json")
        return raw

    def _accept_registration(self, raw: str | bytes) -> None:
        message = _decode_server_message(raw)
        msg_type = message.get("type")
        if msg_type in _ERROR_TYPES:
            logger.error("signaling_rejected type=%s peer_id=%s", msg_type, self._peer_id)
            raise SignalingError(str(msg_type))
        if msg_type != "OPEN":
            logger.error("signaling_rejected type=%s peer_id=%s", msg_type, self._peer_id)
            raise SignalingError("unexpected_message")
        logger.info("signaling_message type=OPEN peer_id=%s", self._peer_id)
        self._registered = True

    async def _read_loop(self) -> None:
        ws = self._ws
        if ws is None:
            return
        try:
            while not self._closed:
                await self._read_one(ws)
        except asyncio.CancelledError:
            raise
        except (ConnectionClosed, ConnectionError, OSError) as exc:
            logger.info(
                "signaling_closed peer_id=%s error=%s",
                self._peer_id,
                type(exc).__name__,
            )

    async def _read_one(self, ws: Any) -> None:
        raw = await ws.recv()
        try:
            message = _decode_server_message(raw)
        except SignalingError:
            logger.warning("signaling_rejected reason=invalid_json peer_id=%s", self._peer_id)
            return
        try:
            await self.handle_signaling_message(message)
        except SignalingError as exc:
            logger.warning(
                "signaling_message_rejected reason=%s peer_id=%s",
                exc.reason,
                self._peer_id,
            )

    async def _heartbeat_loop(self) -> None:
        try:
            while not self._closed:
                await asyncio.sleep(self._heartbeat_interval_s)
                await self._send_signaling({"type": "HEARTBEAT"})
                logger.debug("signaling_heartbeat peer_id=%s", self._peer_id)
        except asyncio.CancelledError:
            raise
        except SignalingError as exc:
            logger.warning(
                "heartbeat_failed peer_id=%s reason=%s",
                self._peer_id,
                exc.reason,
            )

    async def _handle_offer(self, message: Mapping[str, Any]) -> None:
        offer = parse_offer(message)
        async with self._lock:
            if self._refuse_live_offer(offer):
                return
            await self._drop_peer_unlocked(reason="replaced")
            await self._open_answerer(offer)

    def _refuse_live_offer(self, offer: OfferDetails) -> bool:
        if not self._is_alive():
            return False
        state = self._pc.connectionState if self._pc is not None else ""
        logger.warning(
            "offer_rejected reason=connection_active connection_id=%s state=%s",
            offer.connection_id,
            state,
        )
        return True

    async def _open_answerer(self, offer: OfferDetails) -> None:
        pc = RTCPeerConnection(configuration=RTCConfiguration(iceServers=list(self._ice_servers)))
        self._pc = pc
        self._connection_id = offer.connection_id
        self._signaled_close = False
        self._watch_connection(pc)
        self._listen_for_channel(pc)
        queued = self._pending.pop(offer.connection_id)
        try:
            await self._negotiate(pc, offer, queued)
        except _NEGOTIATE_ERRORS as exc:
            logger.warning(
                "offer_rejected reason=negotiate connection_id=%s error=%s",
                offer.connection_id,
                exc,
            )
            await self._drop_peer_unlocked(reason="negotiate_failed")
            raise SignalingError("negotiate_failed") from exc

    async def _negotiate(
        self,
        pc: RTCPeerConnection,
        offer: OfferDetails,
        queued: list[RTCIceCandidate],
    ) -> None:
        await pc.setRemoteDescription(RTCSessionDescription(sdp=offer.sdp, type="offer"))
        await self._add_candidates(pc, queued)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await self._send_local_answer(pc, offer)

    async def _send_local_answer(self, pc: RTCPeerConnection, offer: OfferDetails) -> None:
        local = pc.localDescription
        if local is None or not local.sdp:
            raise SignalingError("no_local_description")
        await self._send_signaling(
            build_answer_message(
                src=offer.src,
                connection_id=offer.connection_id,
                sdp=local.sdp,
            )
        )
        logger.info(
            "answer_sent connection_id=%s peer_id=%s",
            offer.connection_id,
            self._peer_id,
        )

    async def _handle_candidate(self, message: Mapping[str, Any]) -> None:
        parsed = _queueable_candidate(message)
        if parsed is None:
            return
        connection_id, ice = parsed
        async with self._lock:
            await self._store_candidate(connection_id, ice)

    async def _store_candidate(self, connection_id: str, ice: RTCIceCandidate) -> None:
        pc = self._pc
        if pc is not None and self._connection_id == connection_id and self._is_alive():
            await self._add_candidates(pc, [ice])
            return
        self._pending.add(connection_id, ice)
        logger.info("candidate_queued connection_id=%s", connection_id)

    async def _add_candidates(
        self,
        pc: RTCPeerConnection,
        candidates: list[RTCIceCandidate],
    ) -> None:
        for ice in candidates:
            try:
                await pc.addIceCandidate(ice)
            except _ADD_CANDIDATE_ERRORS as exc:
                logger.warning("candidate_rejected reason=add_failed error=%s", exc)

    async def _on_leave(self) -> None:
        logger.info("signaling_leave peer_id=%s", self._peer_id)
        async with self._lock:
            await self._drop_peer_unlocked(reason="leave")

    def _is_alive(self) -> bool:
        pc = self._pc
        return pc is not None and pc.connectionState not in _DEAD_CONNECTION_STATES

    def _watch_connection(self, pc: RTCPeerConnection) -> None:
        @pc.on("connectionstatechange")
        def _on_connection_state() -> None:
            logger.info(
                "peer_connection_state connection_id=%s state=%s",
                self._connection_id,
                pc.connectionState,
            )

        @pc.on("iceconnectionstatechange")
        def _on_ice_state() -> None:
            logger.info(
                "ice_connection_state connection_id=%s state=%s",
                self._connection_id,
                pc.iceConnectionState,
            )

    def _listen_for_channel(self, pc: RTCPeerConnection) -> None:
        @pc.on("datachannel")
        def _on_datachannel(channel: RTCDataChannel) -> None:
            # The browser owns the channel. Answerers receive it already open.
            logger.info("datachannel_received label=%s", channel.label)
            self._bind_channel(channel)

    def _bind_channel(self, channel: RTCDataChannel) -> None:
        self._channel = channel
        self._channel_open.clear()
        self._signaled_close = False

        @channel.on("message")
        def _on_message(message: object) -> None:
            self._enqueue_message(message)

        @channel.on("close")
        def _on_close() -> None:
            self._on_channel_close(channel)

        if channel.readyState == "open":
            self._channel_open.set()

    def _enqueue_message(self, message: object) -> None:
        data = _message_to_bytes(message)
        if data is None:
            logger.warning("datachannel_rejected reason=unsupported_type")
            return
        self._inbound.put_nowait(data)

    def _on_channel_close(self, channel: RTCDataChannel) -> None:
        if self._channel is not channel:
            return
        logger.info("datachannel_closed connection_id=%s", self._connection_id)
        self._channel = None
        self._channel_open.clear()
        self._signal_inbound_closed()

    async def _require_channel(self) -> RTCDataChannel:
        channel = _open_channel(self._channel)
        if channel is not None:
            return channel
        await self._channel_open.wait()
        channel = _open_channel(self._channel)
        if channel is None:
            raise SignalingError("datachannel_not_open")
        return channel

    async def _drop_peer_unlocked(self, *, reason: str) -> None:
        pc = self._pc
        had_channel = self._channel is not None
        self._pc = None
        self._channel = None
        self._connection_id = None
        self._channel_open.clear()
        if pc is None:
            return
        logger.info("peer_connection_closed reason=%s", reason)
        if had_channel:
            self._signal_inbound_closed()
        await pc.close()

    def _signal_inbound_closed(self) -> None:
        if self._signaled_close:
            return
        self._signaled_close = True
        self._inbound.put_nowait(None)

    async def _send_signaling(self, message: Mapping[str, Any]) -> None:
        payload = dict(message)
        raw = json.dumps(payload, separators=(",", ":"))
        ws = self._ws
        if ws is not None:
            await self._send_on_socket(ws, raw)
        if payload.get("type") == "ANSWER":
            self._answers.put_nowait(payload)

    async def _send_on_socket(self, ws: Any, raw: str) -> None:
        try:
            async with self._send_lock:
                await ws.send(raw)
        except (ConnectionClosed, ConnectionError, OSError) as exc:
            raise SignalingError("send_failed") from exc

    async def _cancel_background(self) -> None:
        tasks = [task for task in (self._heartbeat_task, self._reader_task) if task is not None]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._heartbeat_task = None
        self._reader_task = None

    async def _close_socket(self) -> None:
        ws = self._ws
        self._ws = None
        if ws is None:
            return
        try:
            await ws.close()
        except (WebSocketException, OSError) as exc:
            logger.warning("signaling_close_failed peer_id=%s error=%s", self._peer_id, exc)


def _validate_endpoint(
    host: str,
    path: str,
    key: str,
    heartbeat_interval_s: float,
    token: str | None,
) -> None:
    if host == "" or path == "" or key == "":
        raise ValueError("host, path, and key must be non-empty")
    if heartbeat_interval_s <= 0:
        raise ValueError("heartbeat_interval_s must be > 0")
    if token is not None and token == "":
        raise ValueError("token must be non-empty when set")


def _ice_servers(ice_servers: Sequence[RTCIceServer] | None) -> list[RTCIceServer]:
    if ice_servers is None:
        return [RTCIceServer(urls=DEFAULT_STUN_URL)]
    return list(ice_servers)


def _ice_urls(servers: Sequence[RTCIceServer]) -> tuple[str, ...]:
    urls: list[str] = []
    for server in servers:
        if isinstance(server.urls, str):
            urls.append(server.urls)
            continue
        urls.extend(server.urls)
    return tuple(urls)


def _offer_from_payload(src: str, payload: Mapping[str, Any]) -> OfferDetails:
    connection_id = payload.get("connectionId")
    sdp_obj = payload.get("sdp")
    if not isinstance(connection_id, str) or connection_id == "":
        raise SignalingError("bad_offer")
    if not isinstance(sdp_obj, Mapping):
        raise SignalingError("bad_offer")
    sdp = sdp_obj.get("sdp")
    if not isinstance(sdp, str) or sdp == "" or sdp_obj.get("type") != "offer":
        raise SignalingError("bad_offer")
    return OfferDetails(src=src, connection_id=connection_id, sdp=sdp)


def _strip_candidate_prefix(line: str) -> str | None:
    stripped = line.strip()
    if stripped == "":
        return None
    if stripped.startswith(_CANDIDATE_PREFIX):
        stripped = stripped[len(_CANDIDATE_PREFIX) :].strip()
    if stripped == "":
        return None
    return stripped


def _parse_candidate_line(line: str) -> RTCIceCandidate:
    try:
        return candidate_from_sdp(line)
    except (AssertionError, ValueError) as exc:
        raise SignalingError("invalid_candidate") from exc


def _copy_candidate_ids(ice: RTCIceCandidate, candidate_obj: Mapping[str, Any]) -> None:
    sdp_mid = candidate_obj.get("sdpMid")
    if isinstance(sdp_mid, str):
        ice.sdpMid = sdp_mid
    sdp_index = candidate_obj.get("sdpMLineIndex")
    # ``bool`` is an ``int`` subclass and is not a valid m-line index.
    if isinstance(sdp_index, int) and not isinstance(sdp_index, bool):
        ice.sdpMLineIndex = sdp_index


def _queueable_candidate(
    message: Mapping[str, Any],
) -> tuple[str, RTCIceCandidate] | None:
    payload = message.get("payload")
    if not isinstance(payload, Mapping):
        logger.warning("candidate_rejected reason=bad_payload")
        return None
    connection_id = payload.get("connectionId")
    if not isinstance(connection_id, str) or connection_id == "":
        logger.warning("candidate_rejected reason=missing_connection_id")
        return None
    try:
        ice = ice_candidate_from_payload(payload)
    except SignalingError as exc:
        logger.warning(
            "candidate_rejected reason=%s connection_id=%s",
            exc.reason,
            connection_id,
        )
        return None
    if ice is None:
        logger.debug(
            "candidate_ignored reason=end_of_candidates connection_id=%s",
            connection_id,
        )
        return None
    return connection_id, ice


def _message_to_bytes(message: object) -> bytes | None:
    """Return data-channel input as bytes. Text stays UTF-8 and is not parsed."""
    if isinstance(message, bytes):
        return message
    if isinstance(message, str):
        return message.encode("utf-8")
    return None


def _open_channel(channel: RTCDataChannel | None) -> RTCDataChannel | None:
    if channel is not None and channel.readyState == "open":
        return channel
    return None


def _decode_server_message(raw: object) -> dict[str, Any]:
    text = _as_text(raw)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SignalingError("invalid_json") from exc
    if not isinstance(parsed, dict):
        raise SignalingError("invalid_json")
    message: dict[str, Any] = {}
    for key, value in parsed.items():
        if not isinstance(key, str):
            raise SignalingError("invalid_json")
        message[key] = value
    return message


def _as_text(raw: object) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SignalingError("invalid_json") from exc
    raise SignalingError("invalid_json")


async def _open_peerjs_socket(url: str) -> Any:
    """Open one WebSocket to the PeerJS broker.

    Compression and HTTP proxies are off so registration bytes go only to the
    host in ``url``. The token inside ``url`` is not logged.

    Args:
        url: Absolute ``wss`` URL from :func:`build_peerjs_ws_url`.

    Returns:
        A connected client. The caller closes it.
    """
    return await ws_connect(
        url,
        open_timeout=_OPEN_TIMEOUT_S,
        compression=None,
        proxy=None,
    )
