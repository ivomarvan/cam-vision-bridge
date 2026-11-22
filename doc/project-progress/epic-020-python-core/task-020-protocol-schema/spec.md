---
apm_category: task-spec
apm_ref: E020.T020
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E020.T020 — Protokol v1 a JSON Schema

## 1. Goal

Pydantic modely protokolu v1 jsou jediný zdroj pravdy. Z nich se generuje
`schema/cam-vision-bridge-v1.schema.json`. Ruční úprava schématu neprojde testem,
který schéma vygeneruje znovu a porovná.

## 2. Inputs

- `plan.md` § Společné konvence E020
- `spec.md` § 2 (typy výsledků) a § 4.2

## 3. Outputs

V `src/cam_vision_bridge/protocol/`:

- `messages.py` — modely s `v: Literal[1]` a diskriminátorem `t`:
  - `Hello`: `device_ua: str`, `camera: Literal["user","environment"] | None`,
    `width: int`, `height: int` (oba ≥ 1)
  - `Welcome`: volitelné `width`, `height`, `fps` (fps ≥ 1, když je uvedeno)
  - `ErrorMessage`: `reason: str`, volitelné `frame_id`
  - `FrameHeader`: `frame_id: int ≥ 0`, `captured_at: str`, `w`, `h` ≥ 1,
    `part`, `parts`, `total_bytes` (limity až v T030; zde jen typy a `v`/`t`)
  - `Result`: `frame_id`, `items: list[ResultItem]`, `processing_ms: float ≥ 0`
- `results.py` — `ResultItem` jako diskriminované sjednocení, pole `t`:
  `box` (`x,y,w,h`), `quad` (přesně 4 body), `polygon` (≥ 3), `keypoints`
  (body a volitelné `edges` jako dvojice indexů), `polyline` (≥ 2), `text`
  (`text`, volitelné `x,y` jen obě najednou), `metrics` (seznam `name` + `value: float`).
  Každá souřadnice `Field(ge=0, le=1)`. Volitelné `label: str` a `score: float` u
  geometrických typů kromě `text` a `metrics`.
- `export_schema.py` — funkce `export_schema(path: Path) -> None`, která zapíše JSON Schema
  modelu sjednocení všech textových zpráv. Spuštění: `python -m cam_vision_bridge.protocol.export_schema`.
- `schema/cam-vision-bridge-v1.schema.json` commitnutý výstup.
- Testy v `tests/protocol/`.

Parsování neznámého `t` nebo `v != 1` selže validační chybou Pydantic. Žádné tiché
přečtení.

## 4. Context Bundle

- **Read:** `plan.md`, `spec.md` § 4.2, T010 výstupy.
- **Do not modify:** `experiments/`, jiné tasky, `.cursor/`. Kodek a transport se nepíší.
- **Interfaces from prior tasks:** instalovaný balíček z T010.

## 5. Dependencies

T010.

## 6. Test Specification

- Happy path: jeden platný objekt každého `t` včetně `text` bez souřadnic a `text` s `x,y`.
- Edge: souřadnice 0 a 1 projdou; `quad` se 3 body selže; `text` jen s `x` selže.
- Error: `v=2`, neznámé `t`, souřadnice 1.1 → validační chyba.
- Schéma na disku se rovná nově vygenerovanému.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high` (kontrakt protokolu). AGENT_MODELS: `grok-4.7-high`.
