"""Choose which webcam a demo opens.

A laptop often exposes the built-in camera as index 0 and a USB camera as a
higher index. ``--camera N`` selects one. ``--list-cameras`` prints the
devices and stops before any detector is loaded.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CameraInfo:
    """One video device that was probed.

    ``width`` and ``height`` are ``None`` when the device did not return a frame.
    """

    index: int
    name: str
    width: int | None
    height: int | None


def prepare_webcam(argv: list[str] | None = None) -> int:
    """Resolve ``--camera`` before a demo loads a detector.

    Args:
        argv: Arguments without the program name. ``None`` reads the process
            command line.

    Returns:
        OpenCV index of the camera that should be opened.

    Raises:
        SystemExit: When ``--list-cameras`` was passed, or no usable camera
            matches the request.
    """
    args = _parse_args(argv)
    cameras = probe_cameras()
    if args.list_cameras:
        print(format_cameras(cameras), flush=True)
        raise SystemExit(0)
    chosen = choose_camera(cameras, args.camera)
    print(
        f"webcam index={chosen.index} name={chosen.name} size={chosen.width}x{chosen.height}",
        flush=True,
    )
    return chosen.index


def choose_camera(cameras: list[CameraInfo], requested: int | None) -> CameraInfo:
    """Pick one device that returned a frame.

    Args:
        cameras: Every probed device, including those with no frame.
        requested: Index from ``--camera``, or ``None`` when the caller did
            not choose.

    Returns:
        The selected device.

    Raises:
        SystemExit: When the request is missing and several cameras work, or
            when the requested index did not return a frame.
    """
    working = [camera for camera in cameras if camera.width is not None]
    if requested is not None:
        chosen = next((camera for camera in working if camera.index == requested), None)
        if chosen is None:
            raise SystemExit(
                f"camera {requested} did not return a frame\n{format_cameras(cameras)}"
            )
        return chosen
    if len(working) == 1:
        return working[0]
    if not working:
        raise SystemExit(f"no webcam returned a frame\n{format_cameras(cameras)}")
    raise SystemExit(
        "More than one webcam returned a frame. Pass --camera N.\n" + format_cameras(cameras)
    )


def format_cameras(cameras: list[CameraInfo]) -> str:
    """Render probed devices as lines of ``index  name  size``.

    Args:
        cameras: Devices from :func:`probe_cameras`.

    Returns:
        A multi-line description. Devices with no frame say ``no frame``.
    """
    if not cameras:
        return "no video devices found"
    lines: list[str] = []
    for camera in cameras:
        size = "no frame" if camera.width is None else f"{camera.width}x{camera.height}"
        lines.append(f"{camera.index:2d}  {camera.name}  {size}")
    return "\n".join(lines)


def maximum_frame_size(index: int) -> tuple[int, int]:
    """Return the largest frame ``index`` actually delivers.

    The request is an oversized MJPEG mode. The driver clamps it to its
    largest mode. Many USB cameras otherwise stay at 640×480 YUYV.

    Args:
        index: OpenCV camera index.

    Returns:
        Width and height of one captured frame.

    Raises:
        SystemExit: If the camera does not return a frame.
    """
    cv2 = _cv2()
    capture = cv2.VideoCapture(index, cv2.CAP_V4L2)
    try:
        _set_timeouts(cv2, capture)
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 10000)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 10000)
        ok, frame = capture.read()
    finally:
        capture.release()
    if not ok or frame is None:
        raise SystemExit(f"webcam {index} did not return a frame")
    height, width = int(frame.shape[0]), int(frame.shape[1])
    return width, height


def probe_cameras() -> list[CameraInfo]:
    """Open each local video device long enough to read one frame.

    Returns:
        Devices in index order. A device that does not return a frame has
        ``width`` and ``height`` set to ``None``.
    """
    cv2 = _cv2()
    return [_probe_one(cv2, index, name) for index, name in _device_names()]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Webcam demo.")
    parser.add_argument(
        "--camera",
        type=int,
        default=None,
        help="Video device index. Use --list-cameras to see the choices.",
    )
    parser.add_argument(
        "--list-cameras",
        action="store_true",
        help="Print video devices and exit.",
    )
    return parser.parse_args(argv)


def _device_names() -> list[tuple[int, str]]:
    root = Path("/sys/class/video4linux")
    if not root.is_dir():
        return [(index, f"camera {index}") for index in range(6)]
    devices: list[tuple[int, str]] = []
    for node in sorted(root.glob("video*"), key=_video_index):
        if not _is_capture_node(node):
            continue
        name_path = node / "name"
        name = name_path.read_text(encoding="utf-8").strip() if name_path.is_file() else node.name
        devices.append((_video_index(node), name))
    return devices


def _is_capture_node(node: Path) -> bool:
    """Keep the capture node and skip a camera's metadata node.

    Args:
        node: One ``/sys/class/video4linux/videoN`` directory.

    Returns:
        ``True`` when ``index`` is missing or ``0``. A UVC camera uses ``0``
        for frames and ``1`` for metadata.
    """
    index_path = node / "index"
    if not index_path.is_file():
        return True
    return index_path.read_text(encoding="utf-8").strip() == "0"


def _video_index(node: Path) -> int:
    return int(node.name.removeprefix("video"))


def _probe_one(cv2: Any, index: int, name: str) -> CameraInfo:
    capture = cv2.VideoCapture(index, cv2.CAP_V4L2)
    try:
        _set_timeouts(cv2, capture)
        ok, frame = capture.read()
    finally:
        capture.release()
    if not ok or frame is None:
        return CameraInfo(index, name, None, None)
    height, width = int(frame.shape[0]), int(frame.shape[1])
    return CameraInfo(index, name, width, height)


def _set_timeouts(cv2: Any, capture: Any) -> None:
    for prop in ("CAP_PROP_OPEN_TIMEOUT_MSEC", "CAP_PROP_READ_TIMEOUT_MSEC"):
        if hasattr(cv2, prop):
            capture.set(getattr(cv2, prop), 2000)


def _cv2() -> Any:
    try:
        import cv2
    except ImportError as exc:
        raise SystemExit("OpenCV is required to list webcams.") from exc
    return cv2
