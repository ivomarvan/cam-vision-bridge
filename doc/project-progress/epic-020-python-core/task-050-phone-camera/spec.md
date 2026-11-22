---
apm_category: task-spec
apm_ref: E020.T050
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E020.T050 — PhoneCamera

## 1. Goal

Synchronní fasáda nad asyncio: `frames()`, `publish()` a `run(callback)` nad
`FakeTransport`. Po `start()` se vypíše stránková URL s peer ID a ASCII QR kód.
Síťový PeerJS klient je až T060.

## 2. Inputs

- DECISIONS #1, `spec.md` § 4.1, 4.3, 4.6
- `plan.md` § Společné konvence E020
- `FrameHub` a `Transport` z T040

## 3. Outputs

`src/cam_vision_bridge/api/phone_camera.py` a export z `cam_vision_bridge`:

```python
class PhoneCamera:
    def __init__(self, transport: Transport | None = None, *, page_url: str = ".../v1/",
                 peer_id: str | None = None, connect_timeout_s: float | None = None) -> None: ...
    def start(self) -> str: ...          # vrátí URL, vytiskne ji a QR, spustí vlákno s loopem
    def frames(self) -> Iterator[Frame]: ...
    def publish(self, frame: Frame, items: Sequence[ResultItem]) -> None: ...
    def run(self, callback: Callable[[Frame], Sequence[ResultItem]]) -> None: ...
    def close(self) -> None: ...
```

- `frames()` bez spojení čeká. Po `connect_timeout_s` vyhodí `ConnectionTimeout`.
- `publish` pošle JSON `Result` s `processing_ms` změřeným od vydání snímku z `frames()`
  po zavolání `publish`.
- Výjimka z callbacku v `run` se nespolkne.
- `start` bez injektovaného transportu vyhodí `TransportNotConfigured` (T060 dodá výchozí).
- QR přes `qrcode` do stdout. Logy přes `logging`, ne `print`, kromě URL a QR.
- Test použije `FakeTransport`: vloží hello nejdřív ignorovat (smyčka ho smí přijmout a
  poslat `Welcome`), vloží jeden JPEG chunk, `frames()` vrátí `Frame`, `publish` položí
  `Result` do odchozí fronty fake transportu.

## 4. Context Bundle

- **Read:** `plan.md`, T040.
- **Do not modify:** `experiments/`, protokolové limity, `FrameAssembler`.
- **Interfaces from prior tasks:** `Frame`, `FrameHub`, `Transport`, `FakeTransport`, `ResultItem`.

## 5. Dependencies

T040.

## 6. Test Specification

- Happy path: fake JPEG → `frames()` → `publish([box])` → v transportní frontě je `result`
  s týmž `frame_id`.
- Edge: `close()` ukončí `frames()` bez dalšího snímku (`StopIteration` nebo konec iterátoru).
- Error: callback v `run` vyhodí `RuntimeError` a ta vylétne ven. `connect_timeout_s=0.05`
  bez dat vyhodí `ConnectionTimeout`.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high` (veřejné API, na kterém stojí E040). AGENT_MODELS: `grok-4.7-high`.
