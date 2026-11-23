"""Download the WeChat QR models and build the OpenCV detector."""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
from colors import WECHAT
from numpy.typing import NDArray

from cam_vision_bridge.protocol import Point, Quad

_DIR = Path(__file__).resolve().parent / ".models"
# OpenCV 5 loads ONNX. The Caffe pair is rejected by the constructor.
# mirror.opencv.ai hosts these bytes, but its certificate is expired, so the
# copy is the GitHub file with the same SHA-256.
_MODELS = (
    (
        "detect.onnx",
        "https://raw.githubusercontent.com/PPKunOfficial/wechat-qrcode-wasm/main/models/detect.onnx",
        "a533c75ec6866759eb28ff8cfb11d30b4887f838124a9ff4ac477e25ad6c7f9f",
    ),
    (
        "sr.onnx",
        "https://raw.githubusercontent.com/PPKunOfficial/wechat-qrcode-wasm/main/models/upstream/sr.onnx",
        "125ab273d59717c5bf4c5dfb674aa9630d3df42e05b99d2d6fa5ffea32fe34f6",
    ),
)


def open_detector() -> Any:
    """Build ``cv2.wechat_qrcode_WeChatQRCode``, downloading weights if needed.

    Returns:
        The OpenCV WeChat QR detector.

    Raises:
        SystemExit: If this OpenCV build has no WeChat module, or a download fails.
    """
    detect_path, sr_path = _ensure_models()
    cv2 = _contrib()
    try:
        return cv2.wechat_qrcode_WeChatQRCode(str(detect_path), str(sr_path))
    except (SystemError, cv2.error) as exc:
        raise SystemExit(f"WeChat QR models failed to load: {exc}") from exc


def quads_in_tile(detector: Any, tile_rgb: NDArray[np.uint8]) -> list[Quad]:
    """Run WeChat QR on one RGB tile.

    Args:
        detector: Object returned by :func:`open_detector`.
        tile_rgb: RGB ``uint8`` crop.

    Returns:
        Quads in tile coordinates, colored amber.
    """
    cv2 = _contrib()
    bgr = cv2.cvtColor(tile_rgb, cv2.COLOR_RGB2BGR)
    decoded, points = detector.detectAndDecode(bgr)
    height, width = int(bgr.shape[0]), int(bgr.shape[1])
    quads: list[Quad] = []
    for text, corners in _pairs(decoded, points):
        quad = _quad(corners, width, height, text)
        if quad is not None:
            quads.append(quad)
    return quads


def _ensure_models() -> tuple[Path, Path]:
    _DIR.mkdir(parents=True, exist_ok=True)
    paths = [_model_file(name, url, digest) for name, url, digest in _MODELS]
    return (paths[0], paths[1])


def _model_file(name: str, url: str, digest: str) -> Path:
    destination = _DIR / name
    if not _matches(destination, digest):
        try:
            urllib.request.urlretrieve(url, destination)
        except OSError as exc:
            raise SystemExit(f"could not download {url}") from exc
    if not _matches(destination, digest):
        raise SystemExit(f"{name} does not match the expected WeChat QR model")
    return destination


def _matches(path: Path, digest: str) -> bool:
    if not path.is_file():
        return False
    return hashlib.sha256(path.read_bytes()).hexdigest() == digest


def _pairs(decoded: object, points: object) -> list[tuple[object, object]]:
    texts = [decoded] if isinstance(decoded, str) else list(decoded or [])  # type: ignore[arg-type]
    corners = [] if points is None else list(points)  # type: ignore[arg-type]
    return list(zip(texts, corners, strict=False))


def _quad(corners: object, width: int, height: int, text: object) -> Quad | None:
    if width <= 0 or height <= 0:
        return None
    array = np.asarray(corners, dtype=np.float64).reshape(-1, 2)
    if array.shape[0] != 4:
        return None
    points = [Point(x=_unit(float(x) / width), y=_unit(float(y) / height)) for x, y in array]
    label = text if isinstance(text, str) and text else None
    return Quad(t="quad", points=points, label=label, color=WECHAT)


def _unit(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _contrib() -> Any:
    try:
        import cv2
    except ImportError as exc:
        raise SystemExit("Install opencv-contrib-python to use WeChat QR.") from exc
    if not hasattr(cv2, "wechat_qrcode_WeChatQRCode"):
        raise SystemExit(
            "This OpenCV build has no WeChat QR detector. "
            "pip install opencv-contrib-python==5.1.0.95"
        )
    return cv2
