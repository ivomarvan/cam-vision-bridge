"""Unit tests for CSV output. No network."""

from __future__ import annotations

from pathlib import Path

import pytest

from results_writer import FRAME_COLUMNS, RUN_COLUMNS, ResultsWriter

pytestmark = pytest.mark.unit


def test_append_run_two_runs_writes_header_once_and_two_rows(tmp_path: Path) -> None:
    writer = ResultsWriter(tmp_path)
    writer.append_run(**_run("run-a"))
    writer.append_run(**_run("run-b"))
    lines = (tmp_path / "runs.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == ",".join(RUN_COLUMNS)
    assert len(lines) == 3
    assert lines[1].startswith("run-a,")
    assert lines[2].startswith("run-b,")
    assert sum(line.startswith("run_id,") for line in lines) == 1


def test_append_frame_writes_expected_columns(tmp_path: Path) -> None:
    writer = ResultsWriter(tmp_path)
    writer.append_frame(
        "run1", frame_id=4, nbytes=100, parts=2, rtt_ms=12.5, decode_ms=1.25
    )
    text = (tmp_path / "frames" / "run1.csv").read_text(encoding="utf-8")
    assert text == "frame_id,bytes,parts,rtt_ms,decode_ms\n4,100,2,12.5,1.25\n"
    assert text.splitlines()[0] == ",".join(FRAME_COLUMNS)


def test_append_frame_parent_directory_run_id_raises(tmp_path: Path) -> None:
    writer = ResultsWriter(tmp_path)
    with pytest.raises(ValueError):
        writer.append_frame(
            "../x", frame_id=1, nbytes=1, parts=1, rtt_ms=1.0, decode_ms=1.0
        )
    assert list((tmp_path / "frames").glob("*.csv")) == []
    assert not (tmp_path.parent / "x.csv").exists()


def _run(run_id: str) -> dict[str, object]:
    return {
        "run_id": run_id,
        "started_at": "2026-11-21T12:00:00Z",
        "device_ua": "test-agent",
        "mode": "synthetic",
        "width": 640,
        "height": 480,
        "quality": 0.8,
        "in_flight": 1,
        "chunk_bytes": 16384,
        "duration_s": 20.0,
        "connect_ms": 15.0,
        "ice_local_type": "host",
        "ice_remote_type": "host",
        "ice_protocol": "udp",
        "frames_sent": 1,
        "frames_echoed": 1,
    }
