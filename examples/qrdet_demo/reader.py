"""Open one QReader and turn a frame into protocol items.

The mapping in ``detections`` stays free of torch. This module is the only
place that imports QReader.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

import numpy as np
from detections import items_from_reads
from numpy.typing import NDArray

from cam_vision_bridge.protocol import Quad
from cam_vision_bridge.protocol.results import ResultItem


class _DropHalfDeprecation(logging.Filter):
    """Ignore the ultralytics rename warning that qrdet triggers on every frame."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return false for the ``half`` deprecation warning.

        Args:
            record: One ultralytics log record.

        Returns:
            False when the record is the known ``half`` warning.
        """
        return "'half' is deprecated" not in record.getMessage()


def silence_detector_noise() -> None:
    """Hide detector warnings that do not describe a failed detection.

    qrdet 2.5 passes ``half=False`` into ``YOLO.predict``. Current ultralytics
    warns on every frame that ``half`` was renamed to ``quantize``. Torch also
    warns when NVML cannot start. Inference still runs.
    """
    warnings.filterwarnings("ignore", message="Can't initialize NVML")
    logging.getLogger("ultralytics").addFilter(_DropHalfDeprecation())


def open_reader() -> Any:
    """Build one QReader.

    Returns:
        A QReader instance.

    Raises:
        SystemExit: If the demo dependencies are not installed.
    """
    silence_detector_noise()
    try:
        from qreader import QReader
    except ImportError as exc:
        raise SystemExit(
            "Install demo dependencies: pip install -r examples/qrdet_demo/requirements.txt"
        ) from exc
    return QReader()


def scan_frame(
    reader: Any,
    image: NDArray[np.uint8],
    *,
    color: str | None = None,
) -> list[ResultItem]:
    """Detect and decode QR codes in one RGB frame.

    Args:
        reader: Object returned by :func:`open_reader`.
        image: RGB ``uint8`` frame.
        color: Optional ``#RRGGBB`` stroke for the quads.

    Returns:
        Quads plus a panel line for each decoded string.
    """
    decoded_qrs, detections = reader.detect_and_decode(image=image, return_detections=True)
    return items_from_reads(decoded_qrs, detections, color=color)


def quads_in_frame(
    reader: Any,
    image: NDArray[np.uint8],
    *,
    color: str | None = None,
) -> list[Quad]:
    """Return only the quads from :func:`scan_frame`.

    Args:
        reader: Object returned by :func:`open_reader`.
        image: RGB ``uint8`` frame or tile.
        color: Optional ``#RRGGBB`` stroke.

    Returns:
        Quad items. Panel text is omitted so a tile merger can add it once.
    """
    return [item for item in scan_frame(reader, image, color=color) if isinstance(item, Quad)]
