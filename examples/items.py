"""Shared assembly of quad overlays and panel lines."""

from __future__ import annotations

from collections.abc import Sequence

from cam_vision_bridge.protocol import Quad, Text
from cam_vision_bridge.protocol.results import ResultItem


def quads_with_panel(quads: Sequence[Quad], *, prefix: str) -> list[ResultItem]:
    """Return the quads plus one panel line per decoded label.

    Args:
        quads: Geometry already in full-frame coordinates.
        prefix: Detector name written in front of the decoded text.

    Returns:
        Quads followed by panel text items. A quad without a label still
        contributes an ``unreadable`` line.
    """
    items: list[ResultItem] = list(quads)
    for quad in quads:
        payload = quad.label if quad.label else "unreadable"
        items.append(Text(t="text", text=f"{prefix}: {payload}", color=quad.color))
    return items
