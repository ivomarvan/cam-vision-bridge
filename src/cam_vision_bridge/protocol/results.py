"""Result geometry and panel values for protocol v1.

Each item is a JSON object selected by ``t``. Coordinates are fractions of the
sent frame. Items do not carry ``v``; the enclosing ``result`` message does.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal, Self, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

# Quad, polygon, and polyline sizes are part of the v1 contract.
_QUAD_POINT_COUNT = 4
_POLYGON_MIN_POINTS = 3
_POLYLINE_MIN_POINTS = 2

_UnitInterval = Annotated[float, Field(ge=0, le=1)]
_NodeIndex = Annotated[int, Field(ge=0)]


class _ProtocolModel(BaseModel):
    """Shared payload rules: unknown fields are errors, instances stay frozen.

    Phone and peer JSON is untrusted. Ignoring an unknown field would hide a
    protocol mismatch, so extra keys fail validation instead of being dropped.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


class Point(_ProtocolModel):
    """One normalized coordinate pair relative to the sent frame."""

    x: _UnitInterval
    y: _UnitInterval


class Metric(_ProtocolModel):
    """One named number for the phone metrics panel."""

    name: str
    value: float


class Box(_ProtocolModel):
    """Axis-aligned rectangle in normalized coordinates."""

    t: Literal["box"]
    x: _UnitInterval
    y: _UnitInterval
    w: _UnitInterval
    h: _UnitInterval
    label: str | None = None
    score: float | None = None


class Quad(_ProtocolModel):
    """Four-corner polygon in normalized coordinates."""

    t: Literal["quad"]
    points: Annotated[
        list[Point],
        Field(min_length=_QUAD_POINT_COUNT, max_length=_QUAD_POINT_COUNT),
    ]
    label: str | None = None
    score: float | None = None


class Polygon(_ProtocolModel):
    """Closed shape with at least three normalized points."""

    t: Literal["polygon"]
    points: Annotated[list[Point], Field(min_length=_POLYGON_MIN_POINTS)]
    label: str | None = None
    score: float | None = None


class Keypoints(_ProtocolModel):
    """Normalized points and optional segments between them."""

    t: Literal["keypoints"]
    points: list[Point]
    edges: list[tuple[_NodeIndex, _NodeIndex]] | None = None
    label: str | None = None
    score: float | None = None


class Polyline(_ProtocolModel):
    """Open chain of at least two normalized points."""

    t: Literal["polyline"]
    points: Annotated[list[Point], Field(min_length=_POLYLINE_MIN_POINTS)]
    label: str | None = None
    score: float | None = None


class Text(_ProtocolModel):
    """A string drawn at a point, or in the text panel when coordinates are absent."""

    t: Literal["text"]
    text: str
    x: _UnitInterval | None = None
    y: _UnitInterval | None = None

    @model_validator(mode="after")
    def _coordinates_are_paired(self) -> Self:
        # One coordinate is neither a panel line nor a position on the frame.
        if (self.x is None) != (self.y is None):
            raise ValueError("text x and y must both be set or both be omitted")
        return self


class Metrics(_ProtocolModel):
    """Named numbers for the phone metrics panel."""

    t: Literal["metrics"]
    metrics: list[Metric]


GeometryItem: TypeAlias = Box | Quad | Polygon | Keypoints | Polyline | Text | Metrics
ResultItem: TypeAlias = Annotated[GeometryItem, Field(discriminator="t")]

_RESULT_ITEM_ADAPTER: TypeAdapter[GeometryItem] = TypeAdapter(ResultItem)


def parse_result_item(payload: Mapping[str, Any]) -> GeometryItem:
    """Parse one result item.

    Args:
        payload: JSON object already decoded to a mapping. ``t`` selects the variant.

    Returns:
        The item model for ``payload["t"]``.

    Raises:
        ValidationError: If ``t`` is unknown, a coordinate is outside 0..1, or the
            variant's shape constraints fail. Unknown fields are rejected.
    """
    return _RESULT_ITEM_ADAPTER.validate_python(payload)
