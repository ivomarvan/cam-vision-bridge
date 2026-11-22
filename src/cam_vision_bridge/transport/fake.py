"""In-memory transport for unit tests — no network I/O."""

from __future__ import annotations

import asyncio


class FakeTransport:
    """Queue-based ``Transport`` for deterministic tests.

    Tests push inbound frame bytes with ``feed_bytes`` and inspect outbound JSON via
    ``drain_sent_json``. ``receive_bytes`` returns ``None`` after ``close_inbound``.

    ``feed_bytes`` and ``close_inbound`` may be called from a thread other than the
    loop that awaits ``receive_bytes``. ``asyncio.Queue.put_nowait`` from that thread
    does not wake the waiting loop, so the enqueue is scheduled onto the loop.
    """

    def __init__(self) -> None:
        self._inbound: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._outbound: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        """No-op besides remembering the loop used for cross-thread feeds."""
        self._bind_loop()

    async def send_json(self, payload: dict[str, object]) -> None:
        """Enqueue one JSON object as if it were sent to the phone."""
        await self._outbound.put(payload)

    async def receive_bytes(self) -> bytes | None:
        """Block until a test feeds a chunk or marks the inbound side closed."""
        self._bind_loop()
        return await self._inbound.get()

    def feed_bytes(self, data: bytes) -> None:
        """Inject one inbound binary message (synchronous test helper)."""
        self._put_inbound(data)

    def close_inbound(self) -> None:
        """Signal end of inbound data; the next ``receive_bytes`` returns ``None``."""
        self._put_inbound(None)

    def _bind_loop(self) -> None:
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            return

    def _put_inbound(self, item: bytes | None) -> None:
        loop = self._loop
        if loop is None or not loop.is_running() or _running_on(loop):
            self._inbound.put_nowait(item)
            return
        loop.call_soon_threadsafe(self._inbound.put_nowait, item)

    def drain_sent_json(self) -> list[dict[str, object]]:
        """Return and remove all JSON payloads sent through ``send_json``."""
        drained: list[dict[str, object]] = []
        while True:
            try:
                drained.append(self._outbound.get_nowait())
            except asyncio.QueueEmpty:
                break
        return drained


def _running_on(loop: asyncio.AbstractEventLoop) -> bool:
    """Return whether the caller is the thread currently running ``loop``."""
    try:
        return asyncio.get_running_loop() is loop
    except RuntimeError:
        return False
