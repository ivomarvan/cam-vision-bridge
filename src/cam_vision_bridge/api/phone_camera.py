"""Synchronous ``PhoneCamera`` façade over a background asyncio loop.

The loop reads one transport, assembles frames in ``FrameHub``, and sends protocol
JSON back. Callers block in ``frames`` / ``publish`` / ``run``. Pairing URL and QR
go to stdout; every other diagnostic uses ``logging``.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import secrets
import sys
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator, Sequence
from typing import Any, TypeAlias

import qrcode  # type: ignore[import-untyped]  # qrcode==8.2 has no type stubs.
from pydantic import ValidationError

from cam_vision_bridge.core.frame import Frame
from cam_vision_bridge.core.frame_hub import FrameHub, FrameHubClosed
from cam_vision_bridge.protocol.messages import (
    ErrorMessage,
    Hello,
    Message,
    Result,
    Welcome,
    parse_text_message,
)
from cam_vision_bridge.protocol.results import ResultItem
from cam_vision_bridge.transport.base import Transport
from cam_vision_bridge.transport.peerjs import PeerJsWebRtcTransport

logger = logging.getLogger(__name__)

_DEFAULT_PAGE_URL = "https://ivomarvan.github.io/cam-vision-bridge/v1/"
_PEER_ID_PREFIX = "cvb-"
_PEER_ID_HEX_BYTES = 8
_MS_PER_SECOND = 1000.0
_LOOP_READY_TIMEOUT_S = 5.0
_SHUTDOWN_TIMEOUT_S = 5.0

_Outbound: TypeAlias = Welcome | ErrorMessage | Result


class TransportNotConfigured(Exception):
    """Signals that a camera session has no transport.

    ``PhoneCamera`` installs ``PeerJsWebRtcTransport`` when the caller does not
    inject one, so a missing constructor argument does not raise this exception.
    The type stays public for callers that already catch it.
    """


class ConnectionTimeout(Exception):
    """Raised when ``frames`` waits longer than ``connect_timeout_s`` with no frame."""


# Pattern: Facade — blocking iteration in front of an asyncio FrameHub.
class PhoneCamera:
    """Blocking camera session backed by one transport and a background event loop."""

    def __init__(
        self,
        transport: Transport | None = None,
        *,
        page_url: str = _DEFAULT_PAGE_URL,
        peer_id: str | None = None,
        connect_timeout_s: float | None = None,
    ) -> None:
        """Store pairing options and the transport used after ``start``.

        Args:
            transport: Peer connection. ``None`` installs ``PeerJsWebRtcTransport``.
            page_url: Phone page without the ``#peer=`` fragment.
            peer_id: Signaling id. When omitted, a ``cvb-`` id of 16 hex chars is generated.
            connect_timeout_s: Max seconds ``frames`` waits for the next frame.
                ``None`` waits until ``close``.

        Raises:
            ValueError: If the timeout is negative, or the page URL or peer id is unusable.
        """
        _validate_options(page_url, peer_id, connect_timeout_s)
        self._transport: Transport = transport if transport is not None else PeerJsWebRtcTransport()
        self._page_url = page_url
        self._peer_id = peer_id
        self._connect_timeout_s = connect_timeout_s
        self._init_runtime()

    def _init_runtime(self) -> None:
        """Create the hub and the idle flags for one session."""
        self._hub = FrameHub(on_protocol_error=self._on_protocol_error)
        self._protocol_errors: deque[tuple[str, int | None]] = deque()
        self._issued_at: dict[int, float] = {}
        self._issued_lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._reader: asyncio.Task[None] | None = None
        self._closed = False
        self._started = False
        self._url = ""

    def start(self) -> str:
        """Start the background loop, print the pairing URL and QR, and return the URL.

        Returns:
            Page URL whose fragment is ``#peer=<id>``.

        Raises:
            RuntimeError: If the session was already started or the loop did not boot.
            Exception: Whatever ``Transport.start`` raises (for example signaling down).
        """
        self._require_startable()
        peer_id = self._peer_id if self._peer_id is not None else _generate_peer_id()
        self._peer_id = peer_id
        self._bind_peer_id(peer_id)
        self._url = _pairing_url(self._page_url, peer_id)
        try:
            self._open_loop()
            self._boot_transport()
        except Exception:
            self.close()
            raise
        self._started = True
        _print_pairing(self._url)
        logger.info("phone_camera_started peer_id=%s", peer_id)
        return self._url

    def frames(self) -> Iterator[Frame]:
        """Yield complete frames, blocking until one arrives or the session closes.

        Returns:
            Iterator that ends after ``close`` without raising for the close itself.

        Raises:
            RuntimeError: If ``start`` has not been called.
            ConnectionTimeout: If ``connect_timeout_s`` elapses with no frame.
        """
        self._require_started()
        while not self._closed:
            frame = self._pull_frame()
            if frame is None:
                return
            self._remember_issued(frame)
            yield frame

    def publish(self, frame: Frame, items: Sequence[ResultItem]) -> None:
        """Send a ``result`` for ``frame``, including time since ``frames`` yielded it.

        Args:
            frame: Frame previously produced by ``frames``.
            items: Overlay items in normalized coordinates.

        Raises:
            RuntimeError: If the session is not running.
            ValidationError: If ``items`` do not match protocol v1.
        """
        self._require_loop()
        processing_ms = self._processing_ms(frame)
        message = Result(
            v=1,
            t="result",
            frame_id=frame.frame_id,
            items=list(items),
            processing_ms=processing_ms,
        )
        self._send_blocking(message)

    def run(self, callback: Callable[[Frame], Sequence[ResultItem]]) -> None:
        """Publish ``callback(frame)`` for each frame until close or a callback error.

        Args:
            callback: Maps one frame to result items. Its exceptions propagate.

        Raises:
            ConnectionTimeout: If a frame does not arrive in time.
            Exception: Whatever ``callback`` raises. It is not caught here.
        """
        for frame in self.frames():
            items = callback(frame)
            self.publish(frame, items)

    def close(self) -> None:
        """Stop the loop and unblock ``frames``. Further calls do nothing."""
        if self._closed:
            return
        self._closed = True
        self._stop_loop()

    def _require_startable(self) -> None:
        if self._closed:
            raise RuntimeError("PhoneCamera is closed")
        if self._started:
            raise RuntimeError("PhoneCamera is already started")

    def _require_started(self) -> None:
        if not self._started:
            raise RuntimeError("PhoneCamera is not started")

    def _bind_peer_id(self, peer_id: str) -> None:
        """Point the default PeerJS transport at the id embedded in the QR URL."""
        transport = self._transport
        if isinstance(transport, PeerJsWebRtcTransport):
            transport.use_peer_id(peer_id)

    def _require_loop(self) -> asyncio.AbstractEventLoop:
        self._require_started()
        loop = self._loop
        if self._closed or loop is None or not loop.is_running():
            raise RuntimeError("PhoneCamera is not running")
        return loop

    def _open_loop(self) -> None:
        ready = threading.Event()
        thread = threading.Thread(
            target=self._run_loop,
            args=(ready,),
            name="cam-vision-bridge",
            daemon=True,
        )
        self._thread = thread
        thread.start()
        if not ready.wait(timeout=_LOOP_READY_TIMEOUT_S):
            raise RuntimeError("PhoneCamera event loop did not start")

    def _run_loop(self, ready: threading.Event) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        loop.call_soon(ready.set)
        try:
            loop.run_forever()
        finally:
            _cancel_pending(loop)
            loop.close()

    def _boot_transport(self) -> None:
        loop = self._loop
        if loop is None:
            raise RuntimeError("PhoneCamera event loop is missing")
        asyncio.run_coroutine_threadsafe(self._boot(), loop).result()

    async def _boot(self) -> None:
        await self._transport.start()
        reader = asyncio.create_task(self._read_loop(), name="cam-vision-bridge-reader")
        reader.add_done_callback(_log_reader_done)
        self._reader = reader

    async def _read_loop(self) -> None:
        transport = self._transport
        while True:
            data = await transport.receive_bytes()
            if data is None:
                logger.info("inbound_closed")
                continue
            if _looks_like_json_object(data):
                await self._handle_text(data)
                continue
            self._hub.ingest_chunk(data)
            await self._flush_protocol_errors()

    async def _handle_text(self, data: bytes) -> None:
        message = _parse_text(data)
        if isinstance(message, Hello):
            self._hub.camera = message.camera
            logger.info("hello_accepted camera=%s", message.camera)
            await self._send_message(Welcome(v=1, t="welcome"))
            return
        await self._reject_text(message)

    async def _reject_text(self, message: Message | None) -> None:
        if message is None:
            logger.warning("text_rejected reason=invalid_message")
            await self._send_error("invalid_message", None)
            return
        logger.warning("text_rejected t=%s", message.t)
        await self._send_error("unexpected_message", _frame_id_of(message))

    async def _flush_protocol_errors(self) -> None:
        while self._protocol_errors:
            reason, frame_id = self._protocol_errors.popleft()
            await self._send_error(reason, frame_id)

    async def _send_error(self, reason: str, frame_id: int | None) -> None:
        logger.info("error_forwarded reason=%s frame_id=%s", reason, frame_id)
        await self._send_message(ErrorMessage(v=1, t="error", reason=reason, frame_id=frame_id))

    async def _send_message(self, message: _Outbound) -> None:
        await self._transport.send_json(_dump_message(message))

    def _on_protocol_error(self, reason: str, frame_id: int | None) -> None:
        # FrameHub already logged the warning. The reader forwards ``error`` after ingest.
        self._protocol_errors.append((reason, frame_id))

    def _pull_frame(self) -> Frame | None:
        loop = self._loop
        if self._closed or loop is None or not loop.is_running():
            return None
        try:
            future = asyncio.run_coroutine_threadsafe(self._hub.wait_frame(), loop)
        except RuntimeError:
            return None
        return self._wait_for(future)

    def _wait_for(self, future: concurrent.futures.Future[Frame]) -> Frame | None:
        try:
            frame = _future_result(future, self._connect_timeout_s)
        except TimeoutError as exc:
            return self._timeout(future, exc)
        except (FrameHubClosed, asyncio.CancelledError, concurrent.futures.CancelledError):
            return None
        if self._closed:
            return None
        return frame

    def _timeout(
        self,
        future: concurrent.futures.Future[Frame],
        exc: TimeoutError,
    ) -> Frame | None:
        if future.done():
            return self._finished_frame(future)
        future.cancel()
        timeout_s = self._connect_timeout_s
        logger.warning("frame_wait_timeout timeout_s=%s", timeout_s)
        raise ConnectionTimeout(f"no frame arrived within {timeout_s} seconds") from exc

    def _finished_frame(self, future: concurrent.futures.Future[Frame]) -> Frame | None:
        try:
            frame = future.result()
        except (FrameHubClosed, asyncio.CancelledError, concurrent.futures.CancelledError):
            return None
        if self._closed:
            return None
        return frame

    def _remember_issued(self, frame: Frame) -> None:
        # ``Frame`` holds an ndarray, so it cannot be a dict key. ``id`` matches this yield.
        with self._issued_lock:
            self._issued_at[id(frame)] = time.monotonic()

    def _processing_ms(self, frame: Frame) -> float:
        with self._issued_lock:
            started = self._issued_at.pop(id(frame), None)
        if started is None:
            logger.warning("publish_without_issue_time frame_id=%s", frame.frame_id)
            return 0.0
        return max(0.0, (time.monotonic() - started) * _MS_PER_SECOND)

    def _send_blocking(self, message: _Outbound) -> None:
        loop = self._require_loop()
        asyncio.run_coroutine_threadsafe(self._send_message(message), loop).result()

    def _stop_loop(self) -> None:
        loop = self._loop
        thread = self._thread
        if loop is not None and loop.is_running():
            self._request_shutdown(loop)
            _stop_running_loop(loop)
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=_SHUTDOWN_TIMEOUT_S)
            if thread.is_alive():
                logger.warning("loop_thread_still_alive")

    def _request_shutdown(self, loop: asyncio.AbstractEventLoop) -> None:
        future = asyncio.run_coroutine_threadsafe(self._shutdown(), loop)
        try:
            future.result(timeout=_SHUTDOWN_TIMEOUT_S)
        except Exception:
            logger.warning("shutdown_failed", exc_info=True)

    async def _shutdown(self) -> None:
        self._hub.close()
        await self._close_transport()
        reader = self._reader
        if reader is None or reader.done():
            return
        reader.cancel()
        try:
            await reader
        except asyncio.CancelledError:
            logger.info("reader_cancelled")

    async def _close_transport(self) -> None:
        transport = self._transport
        if isinstance(transport, PeerJsWebRtcTransport):
            await transport.close()


def _validate_options(
    page_url: str,
    peer_id: str | None,
    connect_timeout_s: float | None,
) -> None:
    if connect_timeout_s is not None and connect_timeout_s < 0:
        raise ValueError("connect_timeout_s must be >= 0 when set")
    if page_url == "":
        raise ValueError("page_url must be non-empty")
    if peer_id is not None and _invalid_peer_id(peer_id):
        raise ValueError("peer_id must be non-empty and must not contain whitespace or '#'")


def _invalid_peer_id(peer_id: str) -> bool:
    return peer_id == "" or "#" in peer_id or any(char.isspace() for char in peer_id)


def _generate_peer_id() -> str:
    return f"{_PEER_ID_PREFIX}{secrets.token_hex(_PEER_ID_HEX_BYTES)}"


def _pairing_url(page_url: str, peer_id: str) -> str:
    base = page_url.split("#", 1)[0]
    return f"{base}#peer={peer_id}"


def _print_pairing(url: str) -> None:
    """Write the pairing URL and an ASCII QR code. These two lines are not logs."""
    print(url, flush=True)
    code = qrcode.QRCode()
    code.add_data(url)
    code.make(fit=True)
    code.print_ascii(out=sys.stdout)
    sys.stdout.flush()


def _looks_like_json_object(data: bytes) -> bool:
    return data.lstrip().startswith(b"{")


def _parse_text(data: bytes) -> Message | None:
    try:
        decoded = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(decoded, dict):
        return None
    payload: dict[str, Any] = {}
    for key, value in decoded.items():
        if not isinstance(key, str):
            return None
        payload[key] = value
    try:
        return parse_text_message(payload)
    except ValidationError:
        return None


def _frame_id_of(message: Message) -> int | None:
    if isinstance(message, Hello | Welcome):
        return None
    return message.frame_id


def _dump_message(message: _Outbound) -> dict[str, object]:
    raw = message.model_dump(mode="json", exclude_none=True)
    payload: dict[str, object] = {}
    for key, value in raw.items():
        payload[key] = value
    return payload


def _future_result(
    future: concurrent.futures.Future[Frame],
    timeout_s: float | None,
) -> Frame:
    if timeout_s is None:
        return future.result()
    return future.result(timeout=timeout_s)


def _log_reader_done(task: asyncio.Task[None]) -> None:
    if task.cancelled():
        return
    error = task.exception()
    if error is not None:
        logger.error("reader_stopped error=%s", error)


def _cancel_pending(loop: asyncio.AbstractEventLoop) -> None:
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    if not pending:
        return
    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))


def _stop_running_loop(loop: asyncio.AbstractEventLoop) -> None:
    try:
        loop.call_soon_threadsafe(loop.stop)
    except RuntimeError:
        logger.warning("loop_stop_failed", exc_info=True)
