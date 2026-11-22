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
thread, prints the pairing URL and an ASCII QR code, and returns the URL.
`frames` / `publish` / `run` block the caller. Diagnostics go through `logging`.

```python
from cam_vision_bridge import PhoneCamera

cam = PhoneCamera(transport)
url = cam.start()
for frame in cam.frames():
    cam.publish(frame, items)
cam.close()
```

`transport` implements `cam_vision_bridge.transport.Transport`. `PhoneCamera()` with
no transport uses `PeerJsWebRtcTransport` (public PeerJS cloud, Google STUN).
Tests inject `FakeTransport`; that argument is kept as given. `run(callback)`
publishes the callback's items and lets callback exceptions propagate. `frames`
raises `ConnectionTimeout` when `connect_timeout_s` elapses with no frame.

## Pairing (overview)

`start` prints a QR code and a URL whose fragment is `#peer=<id>`. The default page
is `https://ivomarvan.github.io/cam-vision-bridge/v1/`. When `peer_id` is omitted the
id is `cvb-` plus 16 hex characters. Details and protocol limits are in
`doc/project-progress/spec.md`.