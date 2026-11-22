"""Protocol v1 messages, result geometry, and JSON Schema export.

Pydantic models are the only contract. ``schema/cam-vision-bridge-v1.schema.json``
is generated from them and must not be edited by hand.

``export_schema`` is not re-exported here: the function has the same name as its
module, and binding it on the package would shadow ``python -m
cam_vision_bridge.protocol.export_schema``.
"""

from cam_vision_bridge.protocol.messages import (
    ErrorMessage,
    FrameHeader,
    Hello,
    Result,
    Welcome,
    parse_text_message,
)
from cam_vision_bridge.protocol.results import (
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

__all__ = [
    "Box",
    "ErrorMessage",
    "FrameHeader",
    "Hello",
    "Keypoints",
    "Metric",
    "Metrics",
    "Point",
    "Polygon",
    "Polyline",
    "Quad",
    "Result",
    "Text",
    "Welcome",
    "parse_result_item",
    "parse_text_message",
]
