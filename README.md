# cam-vision-bridge

Python library and mobile web client that turn a phone into a camera and live overlay
display for computer-vision experiments on a PC. A foreign Python project installs this
package, receives the latest JPEG frame over WebRTC, and publishes structured results
(boxes, quads, text, metrics) that the phone renders on top of the live preview.

## Requirements

- Python **3.11+** (3.12 recommended for local development)
- Network access for PeerJS signaling (MVP uses the public PeerJS cloud)

Heavy CV/ML stacks (torch, ultralytics, qrdet) belong in your own project or under
`examples/`, not in the core library dependencies.

## Development setup

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[dev]"
```

The package uses **src layout** (`src/cam_vision_bridge/`). After editable install,
import by package name:

```python
import cam_vision_bridge
from cam_vision_bridge import PhoneCamera
from cam_vision_bridge.protocol import Hello, parse_text_message
```

Do not use `from src.…` or `git_root_to_syspath` in library code.

## Deterministic gate (library)

Run from the repo root with the project venv:

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src/ --strict
.venv/bin/pytest
```

## Protocol v1

Pydantic models in `cam_vision_bridge.protocol` are the message contract. Regenerate
the committed schema from the repository root (do not edit the JSON by hand):

```bash
.venv/bin/python -m cam_vision_bridge.protocol.export_schema
```

That writes `schema/cam-vision-bridge-v1.schema.json`. The test suite fails if the
file drifts from the models.

## Public API

`PhoneCamera` is a synchronous façade. `start` runs an asyncio loop on a background
thread and returns the pairing URL. `show_pairing_qr` prints that URL and an ASCII QR code. A loopback host in the
URL is replaced with this computer's LAN address before the code is drawn.
`frames` / `publish` / `run` block the caller. Diagnostics go through `logging`.

```python
from cam_vision_bridge import PhoneCamera, show_pairing_qr

cam = PhoneCamera()
url = cam.start()
show_pairing_qr(url)
for frame in cam.frames():
    cam.publish(frame, items)
cam.close()
```

`transport` implements `cam_vision_bridge.transport.Transport`. `PhoneCamera()` with
no transport uses `PeerJsWebRtcTransport` (public PeerJS cloud, Google STUN).
Tests inject `FakeTransport`; that argument is kept as given. `run(callback)`
publishes the callback's items and lets callback exceptions propagate. `frames`
raises `ConnectionTimeout` when `connect_timeout_s` elapses with no frame.
`capture_size=(width, height)` asks for that size in `welcome` (`width` and
`height` only; `fps` is omitted). The default `None` sends `welcome` without
dimensions. A zero, a negative number, or a non-integer raises `ValueError`
before the transport starts.

## Result types

`publish` and `run` accept protocol v1 items. Coordinates are fractions of the
sent frame, from 0 to 1. The phone draws `box`, `quad`, `polygon`, `keypoints`,
and `polyline` on the preview. `text` without `x` and `y` goes to the text
panel; with both coordinates it is drawn on the frame. `metrics` is a list of
named numbers for the metrics panel. An optional `color` (`#RRGGBB`) sets the
stroke. When it is omitted the phone uses cyan.

`detect_tiled` splits a frame into overlapping tiles, runs a quad detector on
each, and merges the quads back into full-frame coordinates.

## Limits

The PC and the phone need internet for the public PeerJS cloud and STUN. There
is no TURN server. One `PhoneCamera` talks to one phone. The library does not
install torch.

## QR demo

```bash
python3.12 -m venv .venv-qrdet
.venv-qrdet/bin/pip install -e .
.venv-qrdet/bin/pip install -r examples/qrdet_demo/requirements.txt
.venv-qrdet/bin/python examples/qrdet_demo/run_demo.py
```

The environment has to be Python 3.12. The library requires Python 3.11 or newer,
so an older `python` on `PATH` will refuse the install and the script will not
find the package. Details are in
[`examples/qrdet_demo/README.md`](examples/qrdet_demo/README.md).

## Try it

From the repository root:

```bash
.venv/bin/python examples/run_phone.py
```

The script starts the phone page when it is not already running, then calls
`show_pairing_qr`. Scan that one code with the phone or with a PC camera. The
address in the code is chosen by the library. The Chrome HTTP exception is in
[`examples/README.md`](examples/README.md).

## Pairing (overview)

The pairing URL ends with `#peer=<id>`. When `peer_id` is omitted the id is `cvb-`
plus 16 hex characters. The default page is
`https://ivomarvan.github.io/cam-vision-bridge/v1/`. That host does not serve this
working tree until a Pages deploy. Details and protocol limits are in
`doc/project-progress/spec.md`.