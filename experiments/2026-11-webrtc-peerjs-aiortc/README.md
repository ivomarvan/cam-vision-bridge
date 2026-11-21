# WebRTC PeerJS aiortc spike

## Goal

Measure whether a Python `aiortc` peer can open a WebRTC DataChannel to a mobile
browser through the public PeerJS cloud and carry 640×480 JPEG frames quickly
enough for the camera bridge. This directory is a throwaway measurement tool,
not the library.

## Setup (Python)

Requires Python 3.12. Dependencies are pinned in `py/requirements.txt`.

```bash
cd experiments/2026-11-webrtc-peerjs-aiortc/py
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Checks, from the same directory:

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest
```

## Run the peer

```bash
cd experiments/2026-11-webrtc-peerjs-aiortc/py
.venv/bin/python run_peer.py
```

The process registers with `wss://0.peerjs.com`, prints a page URL
(`http://<LAN-IP>:8080/#peer=cvb-…`) and an ASCII QR code, then runs until
Ctrl+C. Metrics are appended under `../results` (`runs.csv`, `frames/<run_id>.csv`).

Useful flags: `--host`, `--port`, `--key`, `--page-url`, `--results-dir`, `--log-level`.

## Measurement page

Static assets live under `web/` (no build step). PeerJS **1.5.4** is loaded from
`https://esm.sh/peerjs@1.5.4` as an ES module. The data-channel `OFFER.payload`
shape is defined in `doc/project-progress/DECISIONS.md` **#6** and
`doc/project-progress/epic-010-spike-webrtc-peerjs/plan.md` § *PeerJS 1.5.4 — OFFER*
(same pin); required fields are `sdp`, `type`, `connectionId`, `metadata`, `label`,
`reliable`, `serialization` — not `browser`. Python may still send `browser: "aiortc"`
in `ANSWER`.

### Start servers (two terminals)

```bash
cd experiments/2026-11-webrtc-peerjs-aiortc/py
.venv/bin/python run_peer.py
```

Copy the printed URL (includes `#peer=cvb-…`), then serve the page:

```bash
cd experiments/2026-11-webrtc-peerjs-aiortc
python3 -m http.server 8080 --directory web
```

Open the URL from `run_peer.py` in Chrome on the same machine. For a shorter
desktop baseline, append `&duration=5`, click **Run matrix** (8 runs + no-chunk
probe last). The probe may drop the DataChannel; the summary table must still
show the outcome.

### Phone (Human)

Use the same Wi-Fi as the PC. Scan the ASCII QR code from `run_peer.py` (it
encodes the LAN URL). Optional camera mode on HTTP LAN origins requires
`chrome://flags/#unsafely-treat-insecure-origin-as-secure` for your page origin.

### Firewall

If ICE stays `failed` or stuck in `checking`, check inbound UDP (and mDNS
`*.local` host candidates) — e.g. `ufw` on the PC — before blaming PeerJS.

### Hash parameters

| Param | Role |
|-------|------|
| `peer` | Required Python peer id from `run_peer.py` |
| `duration` | Run length in seconds (default 20) |
| `host`, `port`, `path`, `key` | PeerJS cloud overrides (defaults match public cloud) |

### Node unit tests (Docker, pinned image)

From `experiments/2026-11-webrtc-peerjs-aiortc/web`:

```bash
docker run --rm -v "$PWD":/w -w /w node:22.12.0-alpine node --test tests/*.test.js
```

(`node --test tests/` on image `22.12.0-alpine` resolves `tests` as a single module;
use the glob above.)

Image digest: `node:22.12.0-alpine@sha256:51eff88af6dff26f59316b6e356188ffa2c422bd3c3b76f2556a2e7e89d080bd`

## Results

`results/summary.md` is generated from the CSV files:

```bash
cd experiments/2026-11-webrtc-peerjs-aiortc/py
.venv/bin/python analyze.py --results-dir ../results
```

The first nine rows are a desktop Chrome baseline on the same PC as the peer
(5 s runs). They check the tools only. They do not describe the phone.

Android Chrome 157 on the same Wi-Fi (20 s, synthetic 640×480), 2026-11-22:

| Run | Quality | In flight | Chunk | Frames | FPS | Median RTT | ICE |
|-----|---------|-----------|-------|--------|-----|------------|-----|
| 1 | 0.6 | 1 | 16384 | 469 | 23.5 | 18 ms | host/prflx udp |
| 2 | 0.6 | 1 | 61440 | 482 | 24.1 | 17 ms | host/host udp |
| 3 | 0.6 | 2 | 16384 | 342 | 17.1 | 21 ms | host/host udp |
| 4 | 0.6 | 2 | 61440 | 152 | 7.6 | 20 ms | host/host udp |
| 5 | 0.8 | 1 | 16384 | 166 | 8.3 | 23 ms | host/host udp |
| 6 | 0.8 | 1 | 61440 | 5 | 0.3 | 32 ms | host/host udp |
| 7 | 0.8 | 2 | 16384 | 4 | 0.2 | 61 ms | host/host udp |
| 8 | 0.8 | 2 | 61440 | 189 | 9.5 | 25 ms | host/host udp |

Connect time was 5.3 s. Every completed run echoed as many frames as it sent.
JPEG decode in Python stayed near 4 ms. JPEGs were 15–22 KB.

Runs 6 and 7 almost stopped sending, then run 8 resumed after about three
minutes. RTT stayed low and losses stayed at zero, so the link was not dropping
frames; the phone stopped offering them.

The final no-split probe (`chunk_bytes` 0, quality 0.8) wrote 429 frame rows
(about 21 KB each, one part, median RTT 19 ms) and did not drop the connection.
`runs.csv` has no row for that probe: `run_end` was not recorded. Frames stayed
under 64 KB, so the over-limit SCTP case was not exercised.

## Outcome

Accepted. WebRTC DataChannel through the public PeerJS cloud is the MVP
transport on a shared LAN. See
`doc/architecture/decisions/ADR-001-transport-webrtc-peerjs.md`. Safari on iOS
was not measured.
