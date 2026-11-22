"""Parsing tests for protocol v1 result items."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from cam_vision_bridge.protocol import (
    Box,
    Keypoints,
    Metric,
    Metrics,
    Point,
    Polygon,
    Polyline,
    Quad,
    Text,
    parse_result_item,
)

pytestmark = pytest.mark.unit

_SQUARE = [
    Point(x=0, y=0),
    Point(x=1, y=0),
    Point(x=1, y=1),
    Point(x=0, y=1),
]


def test_parse_result_item_each_tag_round_trips() -> None:
    items = [
        Box(t="box", x=0, y=1, w=0, h=1, label="edge", score=1.5),
        Quad(t="quad", points=list(_SQUARE)),
        Polygon(t="polygon", points=list(_SQUARE[:3])),
        Keypoints(t="keypoints", points=list(_SQUARE[:2]), edges=[(0, 1)]),
        Polyline(t="polyline", points=list(_SQUARE[:2])),
        Text(t="text", text="panel"),
        Text(t="text", text="on frame", x=0, y=1),
        Metrics(t="metrics", metrics=[Metric(name="fps", value=12.5)]),
    ]
    for item in items:
        raw = item.model_dump(mode="json")
        assert parse_result_item(raw) == item


def test_parse_result_item_box_coordinates_zero_and_one_are_valid() -> None:
    parsed = parse_result_item({"t": "box", "x": 0, "y": 1, "w": 0, "h": 1})
    assert parsed == Box(t="box", x=0, y=1, w=0, h=1)


@pytest.mark.parametrize("count", [3, 5])
def test_parse_result_item_quad_not_four_points_raises(count: int) -> None:
    points = [{"x": 0, "y": 0}] * count
    with pytest.raises(ValidationError):
        parse_result_item({"t": "quad", "points": points})


def test_parse_result_item_text_only_x_raises() -> None:
    with pytest.raises(ValidationError):
        parse_result_item({"t": "text", "text": "half", "x": 0.2})


def test_parse_result_item_text_only_y_raises() -> None:
    with pytest.raises(ValidationError):
        parse_result_item({"t": "text", "text": "half", "y": 0.2})


@pytest.mark.parametrize(
    "payload",
    [
        {"t": "nope"},
        {"t": "box", "x": 1.1, "y": 0, "w": 0.1, "h": 0.1},
        {"t": "box", "x": -0.01, "y": 0, "w": 0.1, "h": 0.1},
        {"t": "polygon", "points": [{"x": 0, "y": 0}, {"x": 1, "y": 1}]},
        {"t": "polyline", "points": [{"x": 0, "y": 0}]},
        {"t": "keypoints", "points": [{"x": 0, "y": 0}], "edges": [[-1, 0]]},
        {"t": "text", "text": "nope", "label": "hidden"},
        {"t": "metrics", "metrics": [{"name": "fps", "value": 1}], "score": 1},
        {"t": "box", "v": 1, "x": 0, "y": 0, "w": 1, "h": 1},
    ],
)
def test_parse_result_item_invalid_payload_raises(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        parse_result_item(payload)
