---
apm_category: task-spec
apm_ref: E030.T030
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E030.T030 — Binární kodek ve stránce

## 1. Goal

Čisté funkce v `web/src/protocol/frameCodec.ts` složí stejný binární snímek jako
`cam_vision_bridge.protocol.frame_codec`. Hlavička používá vygenerované typy.

## 2. Inputs

- Python `pack_chunk` / `split_jpeg` a `FrameHeader`
- Vygenerované typy z T020
- Konvence v `plan.md`: chunk 16 384 B, `chunk_bytes = 0` znamená jedna část

## 3. Outputs

- `packChunk`, `splitFrame`, `parseServerMessage` (validuje `t` a `v === 1`).
- Vitest: pack hlavičky big-endian, 100 000 B na části po 16 384 bez prázdné poslední
  části, `chunkBytes = 0` → jedna zpráva, neznámé `t` vyhodí chybu.
- Klíče JSON hlavičky v pořadí `v, t, frame_id, captured_at, w, h, part, parts, total_bytes`.

## 4. Context Bundle

- **Read:** Python kodek, T020 typy.
- **Do not modify:** Python, `experiments/`, generované typy ručně.
- **Interfaces from prior tasks:** `generated.ts`.

## 5. Dependencies

T020.

## 6. Test Specification

- Happy path: round-trip délky hlavičky a pořadí klíčů.
- Edge: přesný násobek `chunkBytes` nepřidá prázdnou část.
- Error: `v` jiné než 1 a neznámé `t` vyhodí výjimku.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high`. AGENT_MODELS: `grok-4.7-high`.
