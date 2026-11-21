"""Append-only CSV metrics for one spike measurement directory.

``runs.csv`` gains one row when a run ends. ``frames/<run_id>.csv`` gains one
row when a round-trip sample arrives. ``run_id`` is restricted to a path-safe
alphabet so a DataChannel message cannot choose a path outside ``results/``.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from frame_codec import ensure_run_id

logger = logging.getLogger(__name__)

RUN_COLUMNS = [
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
FRAME_COLUMNS = ["frame_id", "bytes", "parts", "rtt_ms", "decode_ms"]


class ResultsWriter:
    """Write ``runs.csv`` and ``frames/<run_id>.csv`` under one directory.

    The runs header is written only when the file is created. Later runs append.

    Args:
        results_dir: Directory that will contain ``runs.csv`` and ``frames/``.
            Created if it does not exist.
    """

    def __init__(self, results_dir: Path) -> None:
        self._results_dir = Path(results_dir)
        self._frames_dir = self._results_dir / "frames"
        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._frames_dir.mkdir(parents=True, exist_ok=True)

    def append_run(
        self,
        *,
        run_id: str,
        started_at: str,
        device_ua: str,
        mode: str,
        width: int,
        height: int,
        quality: float,
        in_flight: int,
        chunk_bytes: int,
        duration_s: float,
        connect_ms: float,
        ice_local_type: str,
        ice_remote_type: str,
        ice_protocol: str,
        frames_sent: int,
        frames_echoed: int,
    ) -> None:
        """Append one measurement-run row.

        Args:
            run_id: Path-safe run identifier.
            started_at: ISO 8601 UTC timestamp taken when ``run_start`` arrived.
            device_ua: Browser user agent reported by the page.
            mode: ``synthetic`` or ``camera``.
            width: Frame width in pixels.
            height: Frame height in pixels.
            quality: JPEG quality passed to the page.
            in_flight: Maximum frames the page kept outstanding.
            chunk_bytes: Chunk size. ``0`` means the JPEG was not split.
            duration_s: Planned run length in seconds.
            connect_ms: Time to open the DataChannel, measured by the page.
            ice_local_type: Selected local ICE candidate type.
            ice_remote_type: Selected remote ICE candidate type.
            ice_protocol: Selected candidate-pair protocol.
            frames_sent: Frames the page says it sent.
            frames_echoed: Frames the page says it got an echo for.

        Raises:
            ValueError: If ``run_id`` is not a safe path component.
        """
        ensure_run_id(run_id)
        row = [
            run_id,
            started_at,
            device_ua,
            mode,
            width,
            height,
            quality,
            in_flight,
            chunk_bytes,
            duration_s,
            connect_ms,
            ice_local_type,
            ice_remote_type,
            ice_protocol,
            frames_sent,
            frames_echoed,
        ]
        self._append(self._results_dir / "runs.csv", RUN_COLUMNS, row)
        logger.info("run_recorded run_id=%s frames_sent=%s", run_id, frames_sent)

    def append_frame(
        self,
        run_id: str,
        *,
        frame_id: int,
        nbytes: int,
        parts: int,
        rtt_ms: float,
        decode_ms: float,
    ) -> None:
        """Append one per-frame row under ``frames/<run_id>.csv``.

        Args:
            run_id: Path-safe run identifier. Becomes the file name.
            frame_id: Frame counter within the run.
            nbytes: Complete JPEG size in bytes.
            parts: Number of chunks the JPEG arrived in.
            rtt_ms: Round-trip time reported by the page.
            decode_ms: Time spent in ``cv2.imdecode``.

        Raises:
            ValueError: If ``run_id`` could write outside ``frames/``.
        """
        path = self._frame_path(run_id)
        row = [frame_id, nbytes, parts, rtt_ms, decode_ms]
        self._append(path, FRAME_COLUMNS, row)
        logger.info(
            "frame_recorded run_id=%s frame_id=%s bytes=%s parts=%s",
            run_id,
            frame_id,
            nbytes,
            parts,
        )

    def _frame_path(self, run_id: str) -> Path:
        safe_id = ensure_run_id(run_id)
        frames_dir = self._frames_dir.resolve()
        path = (frames_dir / f"{safe_id}.csv").resolve()
        if path.parent != frames_dir:
            raise ValueError(f"invalid run_id: {run_id!r}")
        return path

    def _append(self, path: Path, header: list[str], row: list[object]) -> None:
        write_header = not path.exists() or path.stat().st_size == 0
        with path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            if write_header:
                writer.writerow(header)
            writer.writerow(row)
