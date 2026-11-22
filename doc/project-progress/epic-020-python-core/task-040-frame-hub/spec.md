---
apm_category: task-spec
apm_ref: E020.T040
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E020.T040 — Frame, FrameHub, FakeTransport

## 1. Goal

Z kompletního JPEGu vznikne neměnný `Frame`. `FrameHub` drží jen nejnovější snímek a
`FakeTransport` umí v testu dodat bajty a sebrat odeslaný `Result` bez sítě.

## 2. Inputs

- `plan.md` § Společné konvence E020
- `spec.md` § 4.3
- Kodek z T030 a modely z T020

## 3. Outputs

- `src/cam_vision_bridge/core/frame.py` — dataclass `Frame`: `image` (`numpy.ndarray`
  RGB uint8), `frame_id`, `captured_at`, `width`, `height`, `camera`. Bez setterů.
- `src/cam_vision_bridge/core/frame_hub.py` — `FrameHub`:
  `ingest_chunk(data: bytes) -> None` složí části, při kompletu dekóduje JPEG až po
  úspěšném `FrameAssembler`. Neplatný vstup zaloguje `WARNING` a vrátí důvod přes
  callback `on_protocol_error(reason: str, frame_id: int | None)`, snímek nepublikuje.
  `wait_frame()` čeká na nejnovější snímek, který ještě nebyl vydán. Když mezitím přijde
  novější kompletní snímek, starší se zahodí. `close()` probudí čekajícího.
- `src/cam_vision_bridge/transport/base.py` — `Protocol` `Transport` s
  `async def start(self) -> None`, `async def send_json(self, payload: dict) -> None`,
  `async def receive_bytes(self) -> bytes | None` (`None` = spojení skončilo).
- `src/cam_vision_bridge/transport/fake.py` — `FakeTransport` s frontami, bez sítě.
- Testy: malý JPEG 2×2 přes `pack_chunk` → `ingest_chunk` → `Frame.image.shape`.

## 4. Context Bundle

- **Read:** `plan.md`, T020, T030.
- **Do not modify:** `experiments/`, protokolové modely (chyba → `BLOCKED`).
- **Interfaces from prior tasks:** `FrameHeader`, `FrameAssembler`, `pack_chunk`.

## 5. Dependencies

T030.

## 6. Test Specification

- Happy path: jeden JPEG se složí a `wait_frame` vrátí RGB tvar `(h, w, 3)`.
- Edge: dva kompletní snímky dřív, než si někdo zavolá `wait_frame` → vrátí se jen novější.
- Error: neplatná binární zpráva zavolá `on_protocol_error` a `wait_frame` dál čeká
  na pozdější platný snímek. `cv2.imdecode` se na neplatných bajtech nespustí
  (assembler vyhodí dřív; test může poslat zprávu kratší než 4 B).

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `medium`. AGENT_MODELS: `composer-2.5`.
