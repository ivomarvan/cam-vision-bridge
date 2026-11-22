---
apm_category: task-spec
apm_ref: E035.T020
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E035.T020 — Velikost snímku na telefonu

## 1. Goal

Čisté funkce zvolí povolenou velikost a JPEG se kreslí v pixelech, které kamera
opravdu má. `welcome` z PC smí velikost změnit. Výchozí je 640×480.

## 2. Inputs

- DECISIONS #12, `plan.md`
- `web/src/camera/captureFrame.ts` dnes kreslí vždy 640×480
- `welcome.width` / `welcome.height` už parser zná

## 3. Outputs

Modul `web/src/camera/captureSize.ts`:

- seznam `(640, 480)`, `(1280, 720)`, `(1920, 1080)` a výchozí první položka
- `nearestPreset(width, height)` podle počtu pixelů, remíza bere menší
- `sizeFromWelcome(width, height)` vrací preset, nebo `null` když chybí jedno pole
  nebo obě
- `bitmapSize(videoWidth, videoHeight, preset)` vrátí velikost canvasu: skutečné
  video, a když je delší strana nad 1920, zmenšení se zachovaným poměrem na 1920

`captureFrame` kreslí na tuto velikost, ne vždy na 640×480. `hello` a hlavička
snímku dostanou stejná čísla. Druhé `hello` se neposílá.

## 4. Context Bundle

- **Read:** `captureFrame.ts`, `peerSession.ts`, `App.vue`.
- **Do not modify:** Python, schema, `experiments/`, přepínač `facingMode`.
- **Interfaces from prior tasks:** stávající `welcome` a `hello`.

## 5. Dependencies

Žádné vůči T010. T030 smí importovat jen hotové funkce z tohoto tasku.

## 6. Test Specification

- Happy path: `nearestPreset(1280, 720)` je 1280×720. Video 1280×720 dá canvas
  1280×720 a `drawImage` na celou plochu.
- Edge: `nearestPreset(1000, 700)` padne na bližší počet pixelů. `sizeFromWelcome`
  bez jednoho rozměru vrátí `null`. Video 3840×2160 se zmenší na 1920×1080.
- Error: nulová šířka videa vyhodí `RangeError` a JPEG se nevytvoří.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high`. AGENT_MODELS: `grok-4.7-high`.
