"""Build ``results/summary.md`` from spike CSV measurements.

Uses only the standard library. Frame metrics come from
``frames/<run_id>.csv``; a missing or empty frame file yields ``n/a`` rather
than a crash. Non-numeric frame cells are skipped and logged.
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
import statistics
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SUMMARY_COLUMNS = [
    "run_id",
    "device",
    "mode",
    "quality",
    "in_flight",
    "chunk_bytes",
    "frames",
    "lost",
    "fps",
    "mean_kb",
    "rtt_med",
    "rtt_p95",
    "decode_med",
    "ice_local",
    "ice_remote",
    "ice_proto",
    "connect_ms",
]
_NA = "n/a"
_FRAME_NUMBERS = ("bytes", "rtt_ms", "decode_ms")


def load_runs(results_dir: Path) -> list[dict[str, str]]:
    """Load ``runs.csv`` rows from a results directory.

    Args:
        results_dir: Directory that contains ``runs.csv``.

    Returns:
        One dict per data row, with the CSV header as keys.

    Raises:
        FileNotFoundError: If ``runs.csv`` is not in ``results_dir``.
    """
    path = results_dir / "runs.csv"
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize_run(run: dict[str, str], results_dir: Path) -> dict[str, str]:
    """Turn one ``runs.csv`` row plus its frame file into a table row.

    Args:
        run: One row from :func:`load_runs`.
        results_dir: Directory that contains ``frames/<run_id>.csv``.

    Returns:
        String cells in :data:`SUMMARY_COLUMNS` order. Frame metrics are
        ``n/a`` when the frame file is missing or has no usable rows.
    """
    sent = int(float(run["frames_sent"]))
    echoed = int(float(run["frames_echoed"]))
    duration = float(run["duration_s"])
    samples = _load_frame_samples(results_dir, run["run_id"])
    frame_metrics = _frame_metrics(samples)
    return {
        "run_id": run["run_id"],
        "device": device_label(run.get("device_ua", "")),
        "mode": run["mode"],
        "quality": _fmt(float(run["quality"])),
        "in_flight": str(int(float(run["in_flight"]))),
        "chunk_bytes": str(int(float(run["chunk_bytes"]))),
        "frames": str(echoed),
        "lost": str(sent - echoed),
        "fps": _NA if duration == 0 else _fmt(echoed / duration),
        "mean_kb": frame_metrics["mean_kb"],
        "rtt_med": frame_metrics["rtt_med"],
        "rtt_p95": frame_metrics["rtt_p95"],
        "decode_med": frame_metrics["decode_med"],
        "ice_local": run["ice_local_type"],
        "ice_remote": run["ice_remote_type"],
        "ice_proto": run["ice_protocol"],
        "connect_ms": _fmt(float(run["connect_ms"])),
    }


def render_markdown(rows: list[dict[str, str]]) -> str:
    """Render summary rows as a Markdown table.

    Args:
        rows: Cells produced by :func:`summarize_run`.

    Returns:
        A Markdown document with one header and one row per run.
    """
    header = "| " + " | ".join(SUMMARY_COLUMNS) + " |"
    separator = "| " + " | ".join("---" for _ in SUMMARY_COLUMNS) + " |"
    body = [
        "| " + " | ".join(row[column] for column in SUMMARY_COLUMNS) + " |"
        for row in rows
    ]
    lines = ["# Spike results", "", header, separator, *body, ""]
    return "\n".join(lines)


def device_label(user_agent: str) -> str:
    """Shorten a User-Agent to ``OS/browser``.

    Args:
        user_agent: Raw ``device_ua`` from ``runs.csv``.

    Returns:
        OS token (``Android``, ``iOS``, ``Linux``, ``Windows``, ``macOS``,
        or ``other``) and browser token (``Chrome``, ``Safari``, ``Firefox``,
        or ``other``), joined by ``/``.
    """
    return f"{_os_token(user_agent)}/{_browser_token(user_agent)}"


def nearest_rank_p95(values: list[float]) -> float:
    """Return the nearest-rank 95th percentile.

    Args:
        values: At least one sample. Order does not matter.

    Returns:
        The ``ceil(0.95 · n)``-th value of the sorted samples (1-based).
    """
    ordered = sorted(values)
    rank = math.ceil(0.95 * len(ordered))
    return ordered[rank - 1]


def main(argv: list[str] | None = None) -> int:
    """Write ``summary.md`` for a results directory.

    Args:
        argv: CLI arguments excluding the program name. ``None`` reads
            ``sys.argv``.

    Returns:
        ``0`` on success, ``2`` when ``runs.csv`` is missing.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Summarize spike CSV results.")
    parser.add_argument("--results-dir", default="../results")
    args = parser.parse_args(argv)
    results_dir = Path(args.results_dir)
    try:
        runs = load_runs(results_dir)
    except FileNotFoundError as exc:
        logger.error("runs.csv missing: path=%s", exc.filename)
        print(f"runs.csv not found: {exc.filename}", file=sys.stderr)
        return 2
    rows = [summarize_run(run, results_dir) for run in runs]
    destination = results_dir / "summary.md"
    destination.write_text(render_markdown(rows), encoding="utf-8")
    print(f"Wrote {destination}")
    return 0


def _load_frame_samples(results_dir: Path, run_id: str) -> list[dict[str, float]]:
    path = results_dir / "frames" / f"{run_id}.csv"
    if not path.is_file():
        logger.warning("Frame CSV missing: run_id=%s path=%s", run_id, path)
        return []
    samples: list[dict[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            parsed = _parse_frame_row(run_id, row)
            if parsed is not None:
                samples.append(parsed)
    return samples


def _parse_frame_row(run_id: str, row: dict[str, str]) -> dict[str, float] | None:
    try:
        return {key: float(row[key]) for key in _FRAME_NUMBERS}
    except (KeyError, TypeError, ValueError):
        logger.warning("Skipping frame row: run_id=%s reason=non_numeric", run_id)
        return None


def _frame_metrics(samples: list[dict[str, float]]) -> dict[str, str]:
    if not samples:
        return {"mean_kb": _NA, "rtt_med": _NA, "rtt_p95": _NA, "decode_med": _NA}
    return {
        "mean_kb": _fmt(statistics.fmean(item["bytes"] for item in samples) / 1024),
        "rtt_med": _fmt(statistics.median(item["rtt_ms"] for item in samples)),
        "rtt_p95": _fmt(nearest_rank_p95([item["rtt_ms"] for item in samples])),
        "decode_med": _fmt(statistics.median(item["decode_ms"] for item in samples)),
    }


def _fmt(value: float) -> str:
    return f"{value:.1f}"


def _os_token(user_agent: str) -> str:
    if "Android" in user_agent:
        return "Android"
    if any(token in user_agent for token in ("iPhone", "iPad", "iPod")):
        return "iOS"
    if "Windows" in user_agent:
        return "Windows"
    if "Mac OS X" in user_agent or "Macintosh" in user_agent:
        return "macOS"
    if "Linux" in user_agent:
        return "Linux"
    return "other"


def _browser_token(user_agent: str) -> str:
    if "Firefox" in user_agent:
        return "Firefox"
    if "Chrome" in user_agent or "Chromium" in user_agent:
        return "Chrome"
    if "Safari" in user_agent:
        return "Safari"
    return "other"


if __name__ == "__main__":
    raise SystemExit(main())
