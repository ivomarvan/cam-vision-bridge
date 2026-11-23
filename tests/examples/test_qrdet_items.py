"""Mapping from a QReader detection to protocol items, without torch."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[2] / "examples" / "qrdet_demo" / "detections.py"
_spec = importlib.util.spec_from_file_location("qrdet_demo_detections", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
_detections = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_detections)
find_summary = _detections.find_summary
items_from_detection = _detections.items_from_detection
items_from_reads = _detections.items_from_reads


def test_items_from_detection_draws_a_quad_and_panel_text() -> None:
    items = items_from_detection(
        "hello",
        {
            "quad_xyn": ((0.1, 0.2), (0.4, 0.2), (0.4, 0.5), (0.1, 0.5)),
            "confidence": 0.9,
        },
    )
    assert items[0].t == "quad"
    assert items[0].label == "hello"
    assert items[0].points[0].x == pytest.approx(0.1)
    assert items[1].t == "text"
    assert items[1].text == "hello"
    assert items[1].x is None


def test_items_from_detection_clamps_and_skips_empty_text() -> None:
    items = items_from_detection(
        None,
        {"quad_xyn": ((-0.2, 0.0), (1.4, 0.2), (0.4, 0.5), (0.1, 0.5)), "confidence": 0.2},
    )
    assert len(items) == 1
    assert items[0].points[0].x == 0.0
    assert items[0].points[1].x == 1.0


def test_find_summary_names_each_code_and_skips_an_empty_frame() -> None:
    assert find_summary((), ()) is None
    assert find_summary(("abc", None), ({}, {})) == "found count=2 text=abc, unreadable"


def test_items_from_reads_keeps_texts_aligned_with_detections() -> None:
    quad = ((0.1, 0.2), (0.4, 0.2), (0.4, 0.5), (0.1, 0.5))
    other = ((0.5, 0.5), (0.8, 0.5), (0.8, 0.8), (0.5, 0.8))
    items = items_from_reads(
        ("first", "second"),
        (
            {"quad_xyn": quad, "confidence": 0.9},
            {"quad_xyn": other, "confidence": 0.4},
        ),
    )
    assert [item.label for item in items if item.t == "quad"] == ["first", "second"]
    assert [item.text for item in items if item.t == "text"] == ["first", "second"]


def test_items_from_reads_accepts_a_numpy_quad() -> None:
    numpy = pytest.importorskip("numpy")
    quad = numpy.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]], dtype=numpy.float32)
    items = items_from_reads(("code",), ({"quad_xyn": quad, "confidence": numpy.float32(0.5)},))
    assert items[0].points[2].x == pytest.approx(1.0)
    assert items[0].score == pytest.approx(0.5)


def test_items_from_detection_rejects_a_short_quad() -> None:
    with pytest.raises(ValueError, match="four points"):
        items_from_detection("x", {"quad_xyn": ((0.0, 0.0), (1.0, 1.0))})
