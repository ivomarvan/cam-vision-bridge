---
apm_category: task-spec
apm_ref: E030.T060
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E030.T060 — Kamera a překryvy

## 1. Goal

Z videa kamery vznikne JPEG 640×480. Přes video se kreslí všechny typy výsledků v1
přes `mapPoint`. Přední kamera se zrcadlí.

## 2. Inputs

- `mapPoint`, relace z T050, typy výsledků
- `spec.md` § 2 a § 4.2

## 3. Outputs

- `web/src/camera/captureFrame.ts` — canvas 640×480, `image/jpeg`, kvalita argument.
  `getUserMedia` je injektovaný. `facingMode` `user` nebo `environment`.
- `web/src/overlay/drawItems.ts` — čisté kreslení do Canvas 2D contextu, který jde
  nahradit v testu záznamem volání: `box`, `quad`, `polygon`, `keypoints` (i s `edges`),
  `polyline`, `text` se souřadnicemi. `text` bez souřadnic a `metrics` funkce nekreslí
  (ty jdou do panelu v T070) a vrátí je zvlášť.

## 4. Context Bundle

- **Read:** T040, T050.
- **Do not modify:** Python, generátor schématu.
- **Interfaces from prior tasks:** `mapPoint`, `peerSession`, generované typy.

## 5. Dependencies

T040, T050.

## 6. Test Specification

- Happy path: fake video frame 100×100 se na canvasu 640×480 vykreslí (volá se `drawImage`).
- Edge: `box` na přední kameře má x zrcadlené proti zadní.
- Error: prázdné `items` nevyvolá výjimku a nevolá `stroke`.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high`. AGENT_MODELS: `grok-4.7-high`.
