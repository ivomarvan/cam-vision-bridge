"""Unit tests for the spike results summary. No network."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from analyze import (
    load_runs,
    main,
    nearest_rank_p95,
    render_markdown,
    summarize_run,
)

pytestmark = pytest.mark.unit

_RUN_HEADER = [
    "run_id",
    "started_at",
    "device_ua",
    "mode",
    "width",
    "height",
    "quality",
    "in_flight",
    "chunk_bytes",
    "duration_s",
    "connect_ms",
    "ice_local_type",
    "ice_remote_type",
    "ice_protocol",
    "frames_sent",
    "frames_echoed",
]
_LINUX_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_ANDROID_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
)


def test_summarize_two_runs_computes_metrics_and_devices(tmp_path: Path) -> None:
    _write_runs(
        tmp_path,
        [
            _run("run-linux", _LINUX_UA, duration_s=2, sent=20, echoed=20),
            _run("run-android", _ANDROID_UA, duration_s=4, sent=5, echoed=3),
        ],
    )
    _write_frames(
        tmp_path,
        "run-linux",
        [
            {"bytes": 1024, "rtt_ms": value, "decode_ms": value}
            for value in range(1, 21)
        ],
    )
    _write_frames(
        tmp_path,
        "run-android",
        [
            {"bytes": 1024, "rtt_ms": 10, "decode_ms": 1},
            {"bytes": 2048, "rtt_ms": 20, "decode_ms": 2},
            {"bytes": 3072, "rtt_ms": 30, "decode_ms": 3},
        ],
    )
    rows = [summarize_run(run, tmp_path) for run in load_runs(tmp_path)]
    assert rows[0]["device"] == "Linux/Chrome"
    assert rows[0]["fps"] == "10.0"
    assert rows[0]["lost"] == "0"
    assert rows[0]["mean_kb"] == "1.0"
    assert rows[0]["rtt_med"] == "10.5"
    assert rows[0]["rtt_p95"] == "19.0"
    assert rows[0]["decode_med"] == "10.5"
    assert rows[1]["device"] == "Android/Chrome"
    assert rows[1]["fps"] == "0.8"
    assert rows[1]["lost"] == "2"
    assert rows[1]["mean_kb"] == "2.0"
    assert rows[1]["rtt_p95"] == "30.0"
    text = render_markdown(rows)
    assert text.splitlines()[2].startswith("| run_id | device |")
    assert "run-linux" in text
    assert "run-android" in text
    assert nearest_rank_p95([float(value) for value in range(1, 21)]) == 19


def test_summarize_missing_or_empty_frames_uses_na(tmp_path: Path) -> None:
    _write_runs(
        tmp_path,
        [
            _run("missing", _LINUX_UA, duration_s=1, sent=1, echoed=0),
            _run("empty", _LINUX_UA, duration_s=1, sent=0, echoed=0),
        ],
    )
    frames = tmp_path / "frames"
    frames.mkdir()
    (frames / "empty.csv").write_text(
        "frame_id,bytes,parts,rtt_ms,decode_ms\n", encoding="utf-8"
    )
    rows = [summarize_run(run, tmp_path) for run in load_runs(tmp_path)]
    for row in rows:
        assert row["mean_kb"] == "n/a"
        assert row["rtt_med"] == "n/a"
        assert row["rtt_p95"] == "n/a"
        assert row["decode_med"] == "n/a"


def test_summarize_non_numeric_frame_row_is_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write_runs(tmp_path, [_run("bad", _LINUX_UA, duration_s=1, sent=2, echoed=2)])
    _write_frames(
        tmp_path,
        "bad",
        [
            {"bytes": "nope", "rtt_ms": 5, "decode_ms": 1},
            {"bytes": 2048, "rtt_ms": 8, "decode_ms": 2},
        ],
    )
    with caplog.at_level("WARNING"):
        row = summarize_run(load_runs(tmp_path)[0], tmp_path)
    assert row["mean_kb"] == "2.0"
    assert row["rtt_med"] == "8.0"
    assert "reason=non_numeric" in caplog.text


def test_main_missing_runs_csv_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["--results-dir", str(tmp_path)])
    assert code == 2
    assert "runs.csv not found" in capsys.readouterr().err


def test_main_writes_summary_markdown(tmp_path: Path) -> None:
    _write_runs(tmp_path, [_run("only", _LINUX_UA, duration_s=1, sent=1, echoed=1)])
    _write_frames(tmp_path, "only", [{"bytes": 1024, "rtt_ms": 4, "decode_ms": 1}])
    assert main(["--results-dir", str(tmp_path)]) == 0
    text = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "| only |" in text
    assert "Linux/Chrome" in text


def _run(
    run_id: str,
    user_agent: str,
    *,
    duration_s: float,
    sent: int,
    echoed: int,
) -> dict[str, str]:
    return {
        "run_id": run_id,
        "started_at": "2026-11-21T00:00:00Z",
        "device_ua": user_agent,
        "mode": "synthetic",
        "width": "640",
        "height": "480",
        "quality": "0.6",
        "in_flight": "1",
        "chunk_bytes": "16384",
        "duration_s": str(duration_s),
        "connect_ms": "12.34",
        "ice_local_type": "host",
        "ice_remote_type": "host",
        "ice_protocol": "udp",
        "frames_sent": str(sent),
        "frames_echoed": str(echoed),
    }


def _write_runs(results_dir: Path, rows: list[dict[str, str]]) -> None:
    with (results_dir / "runs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_RUN_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def _write_frames(
    results_dir: Path, run_id: str, rows: list[dict[str, object]]
) -> None:
    frames = results_dir / "frames"
    frames.mkdir(exist_ok=True)
    with (frames / f"{run_id}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["frame_id", "bytes", "parts", "rtt_ms", "decode_ms"]
        )
        writer.writeheader()
        for index, row in enumerate(rows):
            writer.writerow(
                {
                    "frame_id": index,
                    "bytes": row["bytes"],
                    "parts": 1,
                    "rtt_ms": row["rtt_ms"],
                    "decode_ms": row["decode_ms"],
                }
            )
