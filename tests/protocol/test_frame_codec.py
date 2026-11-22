"""Unit tests for the binary frame codec. No image decode and no network."""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from cam_vision_bridge.protocol.frame_codec import (
    TOTAL_BYTES_MAX,
    FrameAssembler,
    FrameProtocolError,
    pack_chunk,
    split_jpeg,
    unpack_chunk,
)
from cam_vision_bridge.protocol.messages import FrameHeader

pytestmark = pytest.mark.unit

_CAPTURED_AT = "2026-11-22T00:00:00+00:00"


def test_pack_chunk_unpack_chunk_round_trip() -> None:
    header = _header(part=1, parts=4, total_bytes=10)
    payload = b"abc"
    restored, unpacked = unpack_chunk(pack_chunk(header, payload))
    assert restored == header
    assert unpacked == payload


def test_assembler_three_parts_in_order_returns_jpeg() -> None:
    assembler = FrameAssembler(now=lambda: 0.0)
    parts = [b"aa", b"bb", b"cc"]
    assert _add_part(assembler, 0, 3, parts[0]) is None
    assert _add_part(assembler, 1, 3, parts[1]) is None
    assert _add_part(assembler, 2, 3, parts[2]) == b"aabbcc"


def test_assembler_three_parts_out_of_order_returns_jpeg() -> None:
    assembler = FrameAssembler(now=lambda: 0.0)
    parts = [b"aa", b"bb", b"cc"]
    assert _add_part(assembler, 2, 3, parts[2]) is None
    assert _add_part(assembler, 0, 3, parts[0]) is None
    assert _add_part(assembler, 1, 3, parts[1]) == b"aabbcc"


def test_assembler_single_part_returns_jpeg() -> None:
    assembler = FrameAssembler(now=lambda: 0.0)
    jpeg = _add_part(assembler, 0, 1, b"xyz", total_bytes=3)
    assert jpeg == b"xyz"


def test_assembler_incomplete_frame_older_than_two_seconds_is_discarded() -> None:
    clock = {"t": 0.0}
    assembler = FrameAssembler(now=lambda: clock["t"])
    assert _add_part(assembler, 0, 2, b"ab") is None
    clock["t"] = 2.01
    assert _add_part(assembler, 1, 2, b"cd") is None


def test_assembler_incomplete_frame_at_exactly_two_seconds_is_kept() -> None:
    clock = {"t": 0.0}
    assembler = FrameAssembler(now=lambda: clock["t"])
    assert _add_part(assembler, 0, 2, b"ab") is None
    clock["t"] = 2.0
    assert _add_part(assembler, 1, 2, b"cd") == b"abcd"


def test_assembler_duplicate_part_does_not_change_jpeg() -> None:
    assembler = FrameAssembler(now=lambda: 0.0)
    assert _add_part(assembler, 0, 2, b"aa") is None
    assert _add_part(assembler, 0, 2, b"ZZ") is None
    assert _add_part(assembler, 1, 2, b"bb") == b"aabb"


def test_split_jpeg_exact_multiple_has_no_empty_part() -> None:
    jpeg = b"abcdef"
    chunks = split_jpeg(
        jpeg,
        frame_id=4,
        captured_at=_CAPTURED_AT,
        w=3,
        h=2,
        chunk_bytes=3,
    )
    assert len(chunks) == 2
    payloads = []
    for chunk in chunks:
        header, payload = unpack_chunk(chunk)
        assert payload != b""
        assert header.total_bytes == len(jpeg)
        payloads.append(payload)
    assert b"".join(payloads) == jpeg
    assembler = FrameAssembler(now=lambda: 0.0)
    restored: bytes | None = None
    for chunk in reversed(chunks):
        header, payload = unpack_chunk(chunk)
        restored = assembler.add(header, payload)
    assert restored == jpeg


def test_split_jpeg_zero_chunk_bytes_is_one_part() -> None:
    jpeg = b"abcdef"
    chunks = split_jpeg(
        jpeg,
        frame_id=4,
        captured_at=_CAPTURED_AT,
        w=3,
        h=2,
        chunk_bytes=0,
    )
    assert len(chunks) == 1
    header, payload = unpack_chunk(chunks[0])
    assert header.parts == 1
    assert header.part == 0
    assert header.total_bytes == len(jpeg)
    assert payload == jpeg


def test_split_jpeg_negative_chunk_bytes_raises_value_error() -> None:
    with pytest.raises(ValueError, match="chunk_bytes"):
        split_jpeg(b"ab", frame_id=1, captured_at=_CAPTURED_AT, w=1, h=1, chunk_bytes=-1)


def test_unpack_chunk_header_len_above_4096_raises() -> None:
    data = struct.pack(">I", 4097) + b"{}"
    with pytest.raises(FrameProtocolError) as caught:
        unpack_chunk(data)
    assert caught.value.reason == "header_too_long"


def test_unpack_chunk_parts_zero_raises() -> None:
    with pytest.raises(FrameProtocolError) as caught:
        unpack_chunk(_raw_chunk(parts=0, part=0))
    assert caught.value.reason == "parts_out_of_range"


def test_unpack_chunk_parts_above_256_raises() -> None:
    with pytest.raises(FrameProtocolError) as caught:
        unpack_chunk(_raw_chunk(parts=257, part=0))
    assert caught.value.reason == "parts_out_of_range"


def test_unpack_chunk_part_index_past_end_raises() -> None:
    with pytest.raises(FrameProtocolError) as caught:
        unpack_chunk(_raw_chunk(parts=2, part=2))
    assert caught.value.reason == "part_out_of_range"


def test_add_part_outside_range_drops_in_progress_frame() -> None:
    assembler = FrameAssembler(now=lambda: 0.0)
    assert assembler.add(_header(part=0, parts=2, total_bytes=2), b"a") is None
    with pytest.raises(FrameProtocolError) as caught:
        assembler.add(_header(part=2, parts=2, total_bytes=2), b"b")
    assert caught.value.frame_id == 7
    assert assembler.add(_header(part=0, parts=2, total_bytes=2), b"a") is None
    assert assembler.add(_header(part=1, parts=2, total_bytes=2), b"b") == b"ab"


def test_unpack_chunk_total_bytes_above_8_mib_raises() -> None:
    with pytest.raises(FrameProtocolError) as caught:
        unpack_chunk(_raw_chunk(total_bytes=TOTAL_BYTES_MAX + 1, payload=b""))
    assert caught.value.reason == "total_bytes_out_of_range"


def test_assembler_mismatched_parts_drops_frame() -> None:
    assembler = FrameAssembler(now=lambda: 0.0)
    assert _add_part(assembler, 0, 2, b"ab") is None
    with pytest.raises(FrameProtocolError) as caught:
        _add_part(assembler, 1, 3, b"cd")
    assert caught.value.reason == "inconsistent_frame"
    assert _add_part(assembler, 0, 2, b"AB") is None
    assert _add_part(assembler, 1, 2, b"CD") == b"ABCD"


def test_assembler_mismatched_total_bytes_drops_frame() -> None:
    assembler = FrameAssembler(now=lambda: 0.0)
    assert assembler.add(_header(part=0, parts=2, total_bytes=4), b"ab") is None
    with pytest.raises(FrameProtocolError):
        assembler.add(_header(part=1, parts=2, total_bytes=5), b"cd")
    assert assembler.add(_header(part=0, parts=2, total_bytes=4), b"AB") is None
    assert assembler.add(_header(part=1, parts=2, total_bytes=4), b"CD") == b"ABCD"


def test_assembler_payload_sum_not_equal_total_bytes_raises() -> None:
    assembler = FrameAssembler(now=lambda: 0.0)
    assert _add_part(assembler, 0, 2, b"ab", total_bytes=5) is None
    with pytest.raises(FrameProtocolError) as caught:
        _add_part(assembler, 1, 2, b"cd", total_bytes=5)
    assert caught.value.reason == "payload_sum"
    assert _add_part(assembler, 0, 2, b"ab", total_bytes=4) is None
    assert _add_part(assembler, 1, 2, b"cd", total_bytes=4) == b"abcd"


def test_assembler_running_sum_above_total_bytes_drops_frame_before_store() -> None:
    assembler = FrameAssembler(now=lambda: 0.0)
    assert assembler.add(_header(part=0, parts=3, total_bytes=4), b"abcd") is None
    with pytest.raises(FrameProtocolError) as caught:
        assembler.add(_header(part=1, parts=3, total_bytes=4), b"efgh")
    assert caught.value.reason == "payload_sum"
    # The rejected part is not kept, and the previous part is dropped with it.
    # A new 4-byte part therefore fits on its own instead of summing with "abcd".
    assert assembler.add(_header(part=2, parts=3, total_bytes=4), b"wxyz") is None
    stored = assembler._partials[7].payloads
    assert stored == {2: b"wxyz"}


def test_assembler_error_drops_only_that_frame_id() -> None:
    assembler = FrameAssembler(now=lambda: 0.0)
    assert assembler.add(_header(frame_id=1, part=0, parts=2, total_bytes=4), b"ab") is None
    assert assembler.add(_header(frame_id=2, part=0, parts=2, total_bytes=4), b"12") is None
    with pytest.raises(FrameProtocolError):
        assembler.add(_header(frame_id=1, part=1, parts=3, total_bytes=4), b"cd")
    assert assembler.add(_header(frame_id=2, part=1, parts=2, total_bytes=4), b"34") == b"1234"


def test_unpack_chunk_invalid_json_raises() -> None:
    body = b"{"
    with pytest.raises(FrameProtocolError) as caught:
        unpack_chunk(struct.pack(">I", len(body)) + body)
    assert caught.value.reason == "invalid_json"


def test_unpack_chunk_invalid_header_raises() -> None:
    body = json.dumps({"v": 1, "t": "hello"}).encode("utf-8")
    with pytest.raises(FrameProtocolError) as caught:
        unpack_chunk(struct.pack(">I", len(body)) + body)
    assert caught.value.reason == "invalid_header"


def test_unpack_chunk_shorter_than_4_bytes_raises() -> None:
    with pytest.raises(FrameProtocolError) as caught:
        unpack_chunk(b"\x00\x00\x01")
    assert caught.value.reason == "message_too_short"


def test_frame_codec_does_not_decode_jpeg() -> None:
    source = Path(pack_chunk.__code__.co_filename).read_text(encoding="utf-8")
    assert "imdecode" not in source
    assert "import cv2" not in source


def _header(
    *,
    frame_id: int = 7,
    captured_at: str = _CAPTURED_AT,
    w: int = 2,
    h: int = 2,
    part: int = 0,
    parts: int = 1,
    total_bytes: int = 1,
) -> FrameHeader:
    return FrameHeader(
        v=1,
        t="frame",
        frame_id=frame_id,
        captured_at=captured_at,
        w=w,
        h=h,
        part=part,
        parts=parts,
        total_bytes=total_bytes,
    )


def _add_part(
    assembler: FrameAssembler,
    part: int,
    parts: int,
    payload: bytes,
    *,
    total_bytes: int | None = None,
) -> bytes | None:
    size = len(payload) * parts if total_bytes is None else total_bytes
    return assembler.add(_header(part=part, parts=parts, total_bytes=size), payload)


def _raw_chunk(
    *,
    part: int = 0,
    parts: int = 1,
    total_bytes: int = 0,
    payload: bytes = b"",
) -> bytes:
    document = {
        "v": 1,
        "t": "frame",
        "frame_id": 7,
        "captured_at": _CAPTURED_AT,
        "w": 2,
        "h": 2,
        "part": part,
        "parts": parts,
        "total_bytes": total_bytes,
    }
    body = json.dumps(document).encode("utf-8")
    return struct.pack(">I", len(body)) + body + payload
