"""Turn one QReader detection into protocol v1 items.

QReader is imported only by the demo script. This module stays importable
without torch so the coordinate mapping can be tested on its own.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from cam_vision_bridge.protocol import Point, Quad, Text
from cam_vision_bridge.protocol.results import ResultItem


def find_summary(
    decoded_qrs: Sequence[str | None],
    detections: Sequence[Mapping[str, object]],
) -> str | None:
    """Describe the codes found in one frame.

    Args:
        decoded_qrs: One decoded string or ``None`` per detection.
        detections: Detection dicts aligned with ``decoded_qrs``.

    Returns:
        A one-line summary, or ``None`` when the frame has no detection.
    """
    if not detections:
        return None
    labels = [
        decoded if isinstance(decoded, str) and decoded else "unreadable" for decoded in decoded_qrs
    ]
    return f"found count={len(detections)} text={', '.join(labels)}"


def items_from_reads(
    decoded_qrs: Sequence[str | None],
    detections: Sequence[Mapping[str, object]],
    *,
    color: str | None = None,
) -> list[ResultItem]:
    """Pair the two sequences returned by ``detect_and_decode``.

    With ``return_detections=True`` QReader returns ``(decoded_texts, detections)``.
    It does not return one ``(text, detection)`` pair per code.

    Args:
        decoded_qrs: One decoded string or ``None`` per detection, same order.
        detections: Detection dicts. Each ``quad_xyn`` is four normalized corners.

    Returns:
        Quads and panel lines for every detection.

    Raises:
        ValueError: If the sequences differ in length, or a quad is unusable.
    """
    if len(decoded_qrs) != len(detections):
        raise ValueError("decoded texts and detections differ in length")
    items: list[ResultItem] = []
    for decoded, detection in zip(decoded_qrs, detections, strict=True):
        text = decoded if isinstance(decoded, str) and decoded != "" else None
        items.extend(items_from_detection(text, detection, color=color))
    return items


def items_from_detection(
    decoded: str | None,
    detection: Mapping[str, object],
    *,
    color: str | None = None,
) -> list[ResultItem]:
    """Map one QR detection to a quad and, when decoded, a panel line.

    Args:
        decoded: Text read from the code. ``None`` means the code was seen
            but not decoded.
        detection: One QReader detection. ``quad_xyn`` is four corners in
            normalized image coordinates.

    Returns:
        A quad, plus a text item when ``decoded`` is a non-empty string.

    Raises:
        ValueError: If ``quad_xyn`` is missing or does not have four points.
    """
    corners = _four_corners(detection.get("quad_xyn"))
    score = _confidence(detection.get("confidence"))
    label = decoded if decoded else None
    items: list[ResultItem] = [
        Quad(t="quad", points=corners, label=label, score=score, color=color),
    ]
    if decoded:
        items.append(Text(t="text", text=decoded))
    return items


def _four_corners(raw: object) -> list[Point]:
    if isinstance(raw, (str, bytes)):
        raise ValueError("quad_xyn must be four points")
    try:
        rows = list(raw)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError("quad_xyn must be four points") from exc
    if len(rows) != 4:
        raise ValueError("quad_xyn must be four points")
    return [Point(x=_unit(row, 0), y=_unit(row, 1)) for row in rows]


def _unit(row: object, index: int) -> float:
    try:
        value = float(row[index])  # type: ignore[index]
    except (TypeError, IndexError, ValueError) as exc:
        raise ValueError("quad_xyn must be four points") from exc
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _confidence(raw: object) -> float | None:
    if raw is None:
        return None
    return float(raw)  # type: ignore[arg-type]
