"""Run one detector on the phone, or on a webcam with a window on this PC.

The detector receives an RGB ``uint8`` frame and returns protocol items.
Pairing and the window stay here, so each example only implements detection.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Sequence

import numpy as np
from dev_page import ensure_page
from numpy.typing import NDArray
from preview import draw_items

from cam_vision_bridge import PhoneCamera, local_page_url, show_pairing_qr
from cam_vision_bridge.core.frame import Frame
from cam_vision_bridge.protocol.results import ResultItem

Detect = Callable[[NDArray[np.uint8]], Sequence[ResultItem]]
_LOGGER = logging.getLogger("examples")


def run_phone(
    detect: Detect,
    *,
    capture_size: tuple[int, int] = (640, 480),
) -> int:
    """Pair the phone and publish ``detect`` for every frame.

    Args:
        detect: Maps one RGB frame to protocol items.
        capture_size: Width and height requested in ``welcome``.

    Returns:
        Process status code. ``0`` after the session closes.
    """
    _configure_logging()
    ensure_page()
    camera = PhoneCamera(page_url=local_page_url(), capture_size=capture_size)
    previous: str | None = None
    try:
        show_pairing_qr(camera.start())

        def on_frame(frame: Frame) -> Sequence[ResultItem]:
            nonlocal previous
            items = list(detect(frame.image))
            previous = _note(items, previous)
            return items

        camera.run(on_frame)
    finally:
        camera.close()
    return 0


def run_webcam(
    detect: Detect,
    *,
    camera_index: int = 0,
    window: str = "cam-vision-bridge",
    capture_size: tuple[int, int] | None = None,
) -> int:
    """Read a webcam, draw ``detect`` on the frame, and show it in a window.

    Press ``q`` or Esc, or close the window, to stop. The picture keeps moving
    while ``detect`` runs.

    Args:
        detect: Maps one RGB frame to protocol items.
        camera_index: OpenCV camera index.
        window: Title of the preview window.
        capture_size: Width and height to request. ``None`` leaves the driver
            default, which is often 640×480.

    Returns:
        Process status code. ``0`` after the window closes.

    Raises:
        SystemExit: If OpenCV has no window support, or the camera does not open.
    """
    _configure_logging()
    cv2 = _cv2()
    capture = _open_capture(cv2, camera_index, capture_size)
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    pump = _FramePump(capture)
    worker = _DetectPump(detect, cv2)
    try:
        _show_until_closed(cv2, window, pump, worker)
    finally:
        worker.close()
        pump.stop()
        capture.release()
        pump.join()
        cv2.destroyAllWindows()
    return 0


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def _note(items: Sequence[ResultItem], previous: str | None) -> str | None:
    labels = [item.label if item.label else "unreadable" for item in items if item.t == "quad"]
    if not labels:
        return None
    summary = f"found count={len(labels)} text={', '.join(labels)}"
    if summary != previous:
        _LOGGER.info(summary)
    return summary


def _open_capture(
    cv2: object,
    camera_index: int,
    capture_size: tuple[int, int] | None,
) -> object:
    capture = cv2.VideoCapture(camera_index)  # type: ignore[attr-defined]
    if not capture.isOpened():
        raise SystemExit(f"webcam {camera_index} did not open")
    _request_size(cv2, capture, capture_size)
    # A full driver queue shows old frames while detection is still busy.
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # type: ignore[attr-defined]
    return capture


def _request_size(cv2: object, capture: object, capture_size: tuple[int, int] | None) -> None:
    """Ask the driver for ``capture_size``.

    MJPEG is what lets a USB camera leave the 640×480 YUYV default. The driver
    may still clamp the request.
    """
    if capture_size is None:
        return
    width, height = capture_size
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")  # type: ignore[attr-defined]
    capture.set(cv2.CAP_PROP_FOURCC, fourcc)  # type: ignore[attr-defined]
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))  # type: ignore[attr-defined]
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))  # type: ignore[attr-defined]
    actual_w = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))  # type: ignore[attr-defined]
    actual_h = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))  # type: ignore[attr-defined]
    if (actual_w, actual_h) != (width, height):
        _LOGGER.warning(
            "webcam size requested=%dx%d actual=%dx%d",
            width,
            height,
            actual_w,
            actual_h,
        )


def _show_until_closed(cv2: object, window: str, pump: _FramePump, worker: _DetectPump) -> None:
    """Paint the newest camera frame while detection updates the overlay."""
    previous: str | None = None
    deadline = time.monotonic() + 3.0
    while True:
        frame = pump.latest()
        if frame is None:
            if pump.failed or time.monotonic() > deadline:
                raise SystemExit("webcam returned no frame")
            cv2.waitKey(1)  # type: ignore[attr-defined]
            continue
        worker.submit(frame)
        shown = frame.copy()
        items = worker.items()
        draw_items(shown, items)
        previous = _note(items, previous)
        cv2.imshow(window, shown)  # type: ignore[attr-defined]
        if _window_closed(cv2, window):
            return


class _FramePump:
    """Read the webcam on its own thread and keep only the newest frame."""

    def __init__(self, capture: object) -> None:
        self._capture = capture
        self._lock = threading.Lock()
        self._frame: NDArray[np.uint8] | None = None
        self._failed = False
        self._running = True
        self._thread = threading.Thread(target=self._read, name="webcam-capture", daemon=True)
        self._thread.start()

    @property
    def failed(self) -> bool:
        """True after the camera stops returning frames."""
        return self._failed

    def latest(self) -> NDArray[np.uint8] | None:
        """Return a copy of the newest frame, or ``None`` before the first one."""
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def stop(self) -> None:
        """Ask the reader thread to exit."""
        self._running = False

    def join(self) -> None:
        """Wait until the reader thread has left ``read``."""
        self._thread.join(timeout=1.0)

    def _read(self) -> None:
        while self._running:
            ok, frame = self._capture.read()  # type: ignore[attr-defined]
            if not ok or frame is None:
                self._failed = True
                return
            with self._lock:
                self._frame = frame


class _DetectPump:
    """Run detection off the preview thread, always on the newest submitted frame."""

    def __init__(self, detect: Detect, cv2: object) -> None:
        self._detect = detect
        self._cv2 = cv2
        self._lock = threading.Lock()
        self._pending: NDArray[np.uint8] | None = None
        self._items: list[ResultItem] = []
        self._running = True
        self._thread = threading.Thread(target=self._run, name="webcam-detect", daemon=True)
        self._thread.start()

    def submit(self, frame: NDArray[np.uint8]) -> None:
        """Replace any frame that detection has not started yet.

        Args:
            frame: BGR image. Not modified.
        """
        with self._lock:
            self._pending = frame

    def items(self) -> list[ResultItem]:
        """Return the last finished detection."""
        with self._lock:
            return self._items

    def close(self) -> None:
        """Stop the worker after the current frame."""
        self._running = False
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while self._running:
            frame = self._take()
            if frame is None:
                time.sleep(0.005)
                continue
            self._publish(frame)

    def _take(self) -> NDArray[np.uint8] | None:
        with self._lock:
            frame = self._pending
            self._pending = None
            return frame

    def _publish(self, frame: NDArray[np.uint8]) -> None:
        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)  # type: ignore[attr-defined]
        try:
            items = list(self._detect(rgb))
        except Exception:
            # One bad frame must not stop the live preview.
            _LOGGER.exception("webcam detection failed")
            return
        with self._lock:
            self._items = items


def _window_closed(cv2: object, window: str) -> bool:
    key = int(cv2.waitKey(1)) & 0xFF  # type: ignore[attr-defined]
    if key in (ord("q"), 27):
        return True
    visible = float(cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE))  # type: ignore[attr-defined]
    return visible < 1


def _cv2() -> object:
    try:
        import cv2
    except ImportError as exc:
        raise SystemExit("OpenCV is required for the webcam window.") from exc
    if not hasattr(cv2, "imshow"):
        raise SystemExit(
            "This OpenCV build has no window support. Install opencv-python "
            "or opencv-contrib-python."
        )
    return cv2
