---
apm_category: epic-plan
apm_ref: E020
apm_level: epic
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Epic Plan: E020 — Python jádro: protokol, FrameHub, PhoneCamera

## Epic Goal

Instalovatelná knihovna `cam_vision_bridge` se synchronním API `PhoneCamera`, protokolem
v1, skládáním JPEG snímků a transportem WebRTC přes PeerJS. Cizí projekt umí
`pip install -e .` a v testech protáhnout snímek přes `FakeTransport` až do `publish`.
Síťový transport je pokrytý integračním testem aiortc ↔ aiortc bez veřejného cloudu.

Human 2026-11-22 schválil pokračování bez čekání na FE.2 (DECISIONS #8).

## Task List

| Task | Name | Depends on | Coder model | Band |
|------|------|-----------|-------------|------|
| T010 | Kostra balíčku | — | Coder role | medium |
| T020 | Protokol v1 a JSON Schema | T010 | Coder role | high |
| T030 | Binární kodek snímku | T020 | Coder role | high |
| T040 | Frame, FrameHub, FakeTransport | T030 | Coder role | medium |
| T050 | PhoneCamera | T040 | Coder role | high |
| T060 | PeerJsWebRtcTransport | T050 | Coder role | high |

**Modely:** Coder `medium` = `composer-2.5`, Coder `high` = `grok-4.7-high`.
Reviewer `medium` fallback `gpt-5.6-sol-medium` (slug `gemini-4-hydrogen-high` není
v nabídce subagentů). Reviewer `high` = `gpt-5.6-sol-medium`.

## Společné konvence E020

Coder je nesmí měnit. Změna je `BLOCKED` Plannerovi.

- Balíček: `src/cam_vision_bridge/`, import `cam_vision_bridge.*`. Žádný `from src.` a
  žádný `git_root_to_syspath`.
- Kód experimentu v `experiments/` se neimportuje a nesmí se měnit.
- Protokol `v = 1`. Textové zprávy jsou JSON s polem `t`.
- Binární snímek: `[uint32 big-endian header_len][UTF-8 JSON][JPEG této části]`.
  Hlavička: `v`, `t="frame"`, `frame_id`, `captured_at` (ISO 8601), `w`, `h`, `part`,
  `parts`, `total_bytes`. `part` je 0-based.
- Limity před `cv2.imdecode`: `header_len ≤ 4096`, `1 ≤ parts ≤ 256`, `0 ≤ part < parts`,
  `total_bytes ≤ 8 MiB`, shodné `parts` a `total_bytes` v částech jednoho snímku,
  průběžný součet payloadů nesmí překročit `total_bytes`, na konci součet = `total_bytes`.
  Nekompletní snímek starší než 2 s se zahodí. Porušení = výjimka kodeku, peer zaloguje
  `WARNING`, pošle `error`, spojení nechá běžet.
- Souřadnice výsledků jsou float 0..1 včetně. Výsledek bez číselných souřadnic je `text`
  do panelu (`x` a `y` chybí).
- `FrameHub` drží jen nejnovější kompletní snímek. Starší dokončený snímek, který
  uživatel ještě nevzal, se zahodí.
- Veřejné API: `for frame in cam.frames(): cam.publish(frame, items)` a
  `cam.run(callback)`. Jedno aktivní spojení. Další se odmítne.
- Výchozí stránka QR: `https://ivomarvan.github.io/cam-vision-bridge/v1/#peer=<id>`.
  ID: `cvb-` + 16 hex znaků, pokud volající nepředá vlastní.
- Python běží nativně ve venv v kořeni repozitáře (`.venv`), ne v Dockeru.
- Gate: `ruff check .`, `ruff format --check .`, `mypy src/ --strict`, `pytest`.

## Task Specifications

- [T010 — Kostra balíčku](task-010-package-skeleton/spec.md)
- [T020 — Protokol v1](task-020-protocol-schema/spec.md)
- [T030 — Binární kodek](task-030-frame-codec/spec.md)
- [T040 — FrameHub](task-040-frame-hub/spec.md)
- [T050 — PhoneCamera](task-050-phone-camera/spec.md)
- [T060 — WebRTC transport](task-060-peerjs-transport/spec.md)
