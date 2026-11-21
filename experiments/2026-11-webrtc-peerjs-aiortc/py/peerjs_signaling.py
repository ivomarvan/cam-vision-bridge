"""Minimal PeerJS server-protocol client for the public signaling cloud.

The browser originates the DataChannel. This module only speaks the server
WebSocket: register, heartbeat, and forward ``OFFER`` / ``ANSWER`` /
``CANDIDATE``. aiortc puts its ICE candidates into the SDP answer, so this
peer does not send ``CANDIDATE``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from urllib.parse import urlencode

from aiortc import RTCIceCandidate, RTCIceServer
from aiortc.sdp import candidate_from_sdp
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)

# Client version emulated towards the PeerJS cloud (spec example, 1.5.x line).
PEERJS_CLIENT_VERSION = "1.5.4"
HEARTBEAT_INTERVAL_S = 5.0
OPEN_TIMEOUT_S = 10.0
_ERROR_TYPES = frozenset({"ID-TAKEN", "INVALID-KEY", "ERROR"})
_CANDIDATE_PREFIX = "candidate:"

Connector = Callable[[str], Awaitable[Any]]


class SignalingError(Exception):
    """The PeerJS server rejected registration or the socket failed.

    Args:
        reason: Short cause (``ID-TAKEN``, ``INVALID-KEY``, ``ERROR``, or
            ``connect_failed``).
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def peerjs_ice_servers() -> list[RTCIceServer]:
    """Return the PeerJS default ICE servers this spike answerer uses.

    TURN is only a fallback candidate. The spike does not verify that the
    TURN server relays media.

    Returns:
        STUN plus the PeerJS TURN server, in the order the contract names.
    """
    return [
        RTCIceServer(urls="stun:stun.l.google.com:19302"),
        RTCIceServer(
            urls="turn:0.peerjs.com:3478",
            username="peerjs",
            credential="peerjsp",
        ),
    ]


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
        path: HTTP path prefix. The default PeerJS path is ``/`` and the
            suffix ``peerjs`` is appended as the contract specifies.
        key: PeerJS API key.
        peer_id: Id this peer registers under.
        token: Random client token. The server echoes it; it is not a secret
            from the signaling host, but it must not be written to logs.
        version: PeerJS client version string being emulated.

    Returns:
        Absolute ``wss`` URL including the query string.
    """
    query = urlencode(
        (("key", key), ("id", peer_id), ("token", token), ("version", version))
    )
    return f"wss://{host}:{port}{path}peerjs?{query}"


def build_answer_message(*, offer: Mapping[str, Any], sdp: str) -> dict[str, Any]:
    """Build the ``ANSWER`` signaling message for one PeerJS data offer.

    Args:
        offer: The ``OFFER`` object received from the server, including ``src``
            and ``payload.connectionId``.
        sdp: SDP answer text from ``RTCPeerConnection.localDescription``.

    Returns:
        A message whose ``dst`` is the offer's ``src``. The server fills
        ``src`` when it forwards the message.

    Raises:
        SignalingError: If the offer is missing fields the answer must copy.
    """
    payload = offer.get("payload")
    src = offer.get("src")
    if not isinstance(payload, Mapping) or not isinstance(src, str):
        raise SignalingError("bad_offer")
    connection_id = payload.get("connectionId")
    if not isinstance(connection_id, str):
        raise SignalingError("bad_offer")
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
        payload: ``CANDIDATE.payload``. An empty or missing candidate string
            is the end-of-candidates marker.

    Returns:
        A candidate with ``sdpMid`` and ``sdpMLineIndex`` filled in, or
        ``None`` when the browser signaled the end of trickle ICE.

    Raises:
        SignalingError: If the candidate line cannot be parsed.
    """
    candidate_obj = payload.get("candidate")
    if not isinstance(candidate_obj, Mapping):
        return None
    line = candidate_obj.get("candidate")
    if not isinstance(line, str) or line.strip() == "":
        return None
    stripped = line.strip()
    if stripped.startswith(_CANDIDATE_PREFIX):
        stripped = stripped[len(_CANDIDATE_PREFIX) :].strip()
    if stripped == "":
        return None
    try:
        ice = candidate_from_sdp(stripped)
    except (AssertionError, ValueError) as exc:
        raise SignalingError("invalid_candidate") from exc
    sdp_mid = candidate_obj.get("sdpMid")
    if isinstance(sdp_mid, str):
        ice.sdpMid = sdp_mid
    sdp_index = candidate_obj.get("sdpMLineIndex")
    if type(sdp_index) is int:
        ice.sdpMLineIndex = sdp_index
    return ice


def new_signaling_token() -> str:
    """Return a random token for one PeerJS registration.

    Returns:
        32 hex characters. Logged nowhere; it only travels on the signaling URL.
    """
    return secrets.token_hex(16)


class PeerJsSignaling:
    """Async PeerJS cloud client: register, heartbeat, send, and iterate.

    Args:
        peer_id: Id to register. The server replies ``ID-TAKEN`` on collision.
        host: Signaling host.
        port: Signaling port.
        path: Path prefix, default ``/``.
        key: PeerJS API key.
        token: Registration token. Generated when omitted.
        version: Emulated PeerJS client version.
        heartbeat_interval: Seconds between ``HEARTBEAT`` messages.
        connector: Awaitable factory ``(url) -> websocket``. Tests inject a fake.
            The default opens ``wss`` with compression and proxies disabled so
            the only hop is the PeerJS host.
    """

    def __init__(
        self,
        peer_id: str,
        *,
        host: str = "0.peerjs.com",
        port: int = 443,
        path: str = "/",
        key: str = "peerjs",
        token: str | None = None,
        version: str = PEERJS_CLIENT_VERSION,
        heartbeat_interval: float = HEARTBEAT_INTERVAL_S,
        connector: Connector | None = None,
    ) -> None:
        self._peer_id = peer_id
        self._host = host
        self._port = port
        self._path = path
        self._key = key
        self._token = new_signaling_token() if token is None else token
        self._version = version
        self._heartbeat_interval = heartbeat_interval
        self._connector = _open_peerjs_socket if connector is None else connector
        self._ws: Any = None
        self._queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self._send_lock = asyncio.Lock()
        self._reader_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._closed = False
        self._ended = False

    async def connect(self) -> None:
        """Open the socket and wait until the server sends ``OPEN``.

        Raises:
            SignalingError: On ``ID-TAKEN``, ``INVALID-KEY``, ``ERROR``, an
                unexpected first message, or a socket failure.
        """
        url = build_peerjs_ws_url(
            host=self._host,
            port=self._port,
            path=self._path,
            key=self._key,
            peer_id=self._peer_id,
            token=self._token,
            version=self._version,
        )
        logger.info(
            "signaling_connecting host=%s port=%s peer_id=%s",
            self._host,
            self._port,
            self._peer_id,
        )
        try:
            self._ws = await self._connector(url)
            raw = await self._ws.recv()
        except SignalingError:
            raise
        except (WebSocketException, OSError) as exc:
            logger.error(
                "signaling_connect_failed host=%s peer_id=%s error=%s",
                self._host,
                self._peer_id,
                exc,
            )
            await self.close()
            raise SignalingError("connect_failed") from exc
        try:
            message = _decode_server_message(raw)
        except SignalingError:
            await self.close()
            raise
        msg_type = message.get("type")
        if msg_type in _ERROR_TYPES:
            logger.error(
                "signaling_rejected type=%s peer_id=%s", msg_type, self._peer_id
            )
            await self.close()
            raise SignalingError(str(msg_type))
        if msg_type != "OPEN":
            logger.error(
                "signaling_rejected type=%s peer_id=%s", msg_type, self._peer_id
            )
            await self.close()
            raise SignalingError("unexpected_message")
        logger.info("signaling_message type=OPEN peer_id=%s", self._peer_id)
        self._reader_task = asyncio.create_task(self._read_loop(), name="peerjs-read")
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(), name="peerjs-heartbeat"
        )

    async def send(self, message: Mapping[str, Any]) -> None:
        """Send one JSON message to the signaling server.

        Args:
            message: Object the server should forward. ``dst`` is filled by
                the caller; the server adds ``src``.

        Raises:
            SignalingError: If ``connect`` has not succeeded or the socket died.
        """
        if self._ws is None:
            raise SignalingError("not_connected")
        raw = json.dumps(dict(message), separators=(",", ":"))
        try:
            async with self._send_lock:
                await self._ws.send(raw)
        except (ConnectionClosed, ConnectionError) as exc:
            raise SignalingError("send_failed") from exc

    def __aiter__(self) -> PeerJsSignaling:
        """Return this object as the asynchronous iterator of server messages."""
        return self

    async def __anext__(self) -> dict[str, Any]:
        """Return the next decoded server message.

        Returns:
            One JSON object from the server.

        Raises:
            StopAsyncIteration: When the socket closes or ``close`` is called.
        """
        message = await self._queue.get()
        if message is None:
            raise StopAsyncIteration
        return message

    async def close(self) -> None:
        """Stop heartbeat and reading, then close the WebSocket."""
        if self._closed:
            return
        self._closed = True
        tasks = [
            task
            for task in (self._heartbeat_task, self._reader_task)
            if task is not None
        ]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self._ws is not None:
            try:
                await self._ws.close()
            except (WebSocketException, OSError) as exc:
                logger.warning(
                    "signaling_close_failed peer_id=%s error=%s", self._peer_id, exc
                )
        self._finish()

    async def _read_loop(self) -> None:
        assert self._ws is not None
        try:
            while not self._closed:
                raw = await self._ws.recv()
                try:
                    message = _decode_server_message(raw)
                except SignalingError:
                    logger.warning(
                        "signaling_rejected reason=invalid_json peer_id=%s",
                        self._peer_id,
                    )
                    continue
                self._queue.put_nowait(message)
        except asyncio.CancelledError:
            raise
        except (ConnectionClosed, ConnectionError) as exc:
            logger.info(
                "signaling_closed peer_id=%s error=%s",
                self._peer_id,
                type(exc).__name__,
            )
        finally:
            self._finish()

    async def _heartbeat_loop(self) -> None:
        try:
            while not self._closed:
                await asyncio.sleep(self._heartbeat_interval)
                if self._closed:
                    return
                await self.send({"type": "HEARTBEAT"})
                logger.debug("signaling_heartbeat peer_id=%s", self._peer_id)
        except asyncio.CancelledError:
            raise
        except SignalingError as exc:
            logger.warning(
                "heartbeat_failed peer_id=%s error=%s", self._peer_id, exc.reason
            )

    def _finish(self) -> None:
        if self._ended:
            return
        self._ended = True
        self._queue.put_nowait(None)


async def _open_peerjs_socket(url: str) -> Any:
    """Open one WebSocket to the PeerJS cloud and return it.

    Compression and HTTP proxies are off so registration bytes go only to the
    host in ``url``.

    Args:
        url: Absolute ``wss`` URL from :func:`build_peerjs_ws_url`.

    Returns:
        A connected websockets client. The caller closes it.
    """
    return await ws_connect(
        url,
        open_timeout=OPEN_TIMEOUT_S,
        compression=None,
        proxy=None,
    )


def _decode_server_message(raw: str | bytes) -> dict[str, Any]:
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SignalingError("invalid_json") from exc
    else:
        text = raw
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SignalingError("invalid_json") from exc
    if not isinstance(parsed, dict):
        raise SignalingError("invalid_json")
    return parsed
