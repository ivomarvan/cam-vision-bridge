"""Unit tests for the binary frame codec. No network."""

from __future__ import annotations

import json
import struct

import pytest

from frame_codec import (
    TOTAL_BYTES_MAX,
    ChunkHeader,
    FrameAssembler,
    FrameProtocolError,
    pack_chunk,
    unpack_chunk,
)

pytestmark = pytest.mark.unit


def test_pack_chunk_round_trip_preserves_header_and_payload() -> None:
    header = ChunkHeader(run_id="run1", frame_id=3, part=1, parts=4, total_bytes=10)
    payload = b"abc"
    restored, unpacked = unpack_chunk(pack_chunk(header, payload))
    assert restored == header
    assert unpacked == payload


def test_assembler_three_parts_in_order_returns_jpeg() -> None:
    assembler = FrameAssembler(clock=lambda: 0.0)
    parts = [b"aa", b"bb", b"cc"]
    assert _add_part(assembler, 0, 3, parts[0]) is None
    assert _add_part(assembler, 1, 3, parts[1]) is None
    assert _add_part(assembler, 2, 3, parts[2]) == b"aabbcc"


def test_assembler_three_parts_out_of_order_returns_jpeg() -> None:
    assembler = FrameAssembler(clock=lambda: 0.0)
    parts = [b"aa", b"bb", b"cc"]
    assert _add_part(assembler, 2, 3, parts[2]) is None
    assert _add_part(assembler, 0, 3, parts[0]) is None
    assert _add_part(assembler, 1, 3, parts[1]) == b"aabbcc"


def test_assembler_single_part_returns_jpeg() -> None:
    assembler = FrameAssembler(clock=lambda: 0.0)
    jpeg = _add_part(assembler, 0, 1, b"xyz", total_bytes=3)
    assert jpeg == b"xyz"


def test_assembler_incomplete_frame_older_than_two_seconds_is_discarded() -> None:
    clock = {"t": 0.0}
    assembler = FrameAssembler(clock=lambda: clock["t"])
    assert _add_part(assembler, 0, 2, b"ab") is None
    clock["t"] = 2.01
    assert _add_part(assembler, 1, 2, b"cd") is None
    assert assembler.pop_expired() == [("run1", 1)]


def test_assembler_incomplete_frame_at_exactly_two_seconds_is_kept() -> None:
    clock = {"t": 0.0}
    assembler = FrameAssembler(clock=lambda: clock["t"])
    assert _add_part(assembler, 0, 2, b"ab") is None
    clock["t"] = 2.0
    assert _add_part(assembler, 1, 2, b"cd") == b"abcd"


def test_assembler_duplicate_part_does_not_change_jpeg() -> None:
    assembler = FrameAssembler(clock=lambda: 0.0)
    assert _add_part(assembler, 0, 2, b"aa") is None
    assert _add_part(assembler, 0, 2, b"ZZ") is None
    assert _add_part(assembler, 1, 2, b"bb") == b"aabb"


def test_unpack_chunk_header_longer_than_4096_raises() -> None:
    data = struct.pack(">I", 4097) + b"{}"
    with pytest.raises(FrameProtocolError):
        unpack_chunk(data)


def test_unpack_chunk_parts_zero_raises() -> None:
    with pytest.raises(FrameProtocolError):
        unpack_chunk(_raw(parts=0, part=0))


def test_unpack_chunk_parts_above_256_raises() -> None:
    with pytest.raises(FrameProtocolError):
        unpack_chunk(_raw(parts=257, part=0))


def test_unpack_chunk_part_index_past_end_raises() -> None:
    with pytest.raises(FrameProtocolError):
        unpack_chunk(_raw(parts=2, part=2))


def test_unpack_chunk_total_bytes_above_8_mib_raises() -> None:
    with pytest.raises(FrameProtocolError):
        unpack_chunk(_raw(total_bytes=TOTAL_BYTES_MAX + 1, payload=b""))


def test_assembler_mismatched_parts_raises() -> None:
    assembler = FrameAssembler(clock=lambda: 0.0)
    assert _add_part(assembler, 0, 2, b"ab") is None
    with pytest.raises(FrameProtocolError):
        _add_part(assembler, 1, 3, b"cd")


def test_assembler_mismatched_total_bytes_raises() -> None:
    assembler = FrameAssembler(clock=lambda: 0.0)
    header = ChunkHeader("run1", 1, 0, 2, 4)
    assert assembler.add(header, b"ab") is None
    other = ChunkHeader("run1", 1, 1, 2, 5)
    with pytest.raises(FrameProtocolError):
        assembler.add(other, b"cd")


def test_assembler_payload_sum_not_equal_total_bytes_raises() -> None:
    assembler = FrameAssembler(clock=lambda: 0.0)
    assert _add_part(assembler, 0, 2, b"ab", total_bytes=5) is None
    with pytest.raises(FrameProtocolError):
        _add_part(assembler, 1, 2, b"cd", total_bytes=5)


def test_assembler_running_sum_above_total_bytes_drops_frame() -> None:
    assembler = FrameAssembler(clock=lambda: 0.0)
    assert assembler.add(ChunkHeader("run1", 1, 0, 3, 4), b"abcd") is None
    with pytest.raises(FrameProtocolError):
        assembler.add(ChunkHeader("run1", 1, 1, 3, 4), b"efgh")
    # The overshooting part was not stored and the partial frame was dropped,
    # so a later 4-byte part fits exactly instead of summing with the first.
    assert assembler.add(ChunkHeader("run1", 1, 2, 3, 4), b"wxyz") is None


def test_unpack_chunk_invalid_json_raises() -> None:
    body = b"{"
    with pytest.raises(FrameProtocolError):
        unpack_chunk(struct.pack(">I", len(body)) + body)


def test_unpack_chunk_shorter_than_4_bytes_raises() -> None:
    with pytest.raises(FrameProtocolError):
        unpack_chunk(b"\x00\x00\x01")


def _add_part(
    assembler: FrameAssembler,
    part: int,
    parts: int,
    payload: bytes,
    *,
    total_bytes: int | None = None,
) -> bytes | None:
    size = len(payload) * parts if total_bytes is None else total_bytes
    header = ChunkHeader("run1", 1, part, parts, size)
    return assembler.add(header, payload)


def _raw(**overrides: object) -> bytes:
    header: dict[str, object] = {
        "t": "frame",
        "run_id": "run1",
        "frame_id": 1,
        "part": 0,
        "parts": 1,
        "total_bytes": 1,
    }
    payload = overrides.pop("payload", b"x")
    header.update(overrides)
    body = json.dumps(header).encode("utf-8")
    assert isinstance(payload, bytes)
    return struct.pack(">I", len(body)) + body + payload
