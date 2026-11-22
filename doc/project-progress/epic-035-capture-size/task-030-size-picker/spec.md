---
apm_category: task-spec
apm_ref: E035.T030
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E035.T030 — Výběr velikosti na obrazovce

## 1. Goal

Na stránce je vedle kamery výběr ze tří velikostí. Po `welcome` s rozměry se výběr
srovná na položku, kterou telefon použil. Přepínač přední/zadní zůstane.

## 2. Inputs

- Funkce z T020
- `CaptureSettings.vue` a Pinia store

## 3. Outputs

- Select se třemi popisky `640×480`, `1280×720`, `1920×1080`.
- Změna znovu otevře kameru a další JPEG i hlavička mají novou skutečnou velikost.
- `welcome` s `1280` a `720` přepne výběr na 1280×720.
- Vedle výběru je text skutečné velikosti bitmapy, když se liší od položky.

## 4. Context Bundle

- **Read:** T020, `App.vue`, `CaptureSettings.vue`.
- **Do not modify:** Python, schema, `captureSize.ts` (jen použít).
- **Interfaces from prior tasks:** `nearestPreset`, `sizeFromWelcome`, `bitmapSize`.

## 5. Dependencies

T020.

## 6. Test Specification

- Happy path: store začíná na 640×480 a `welcome` 1280×720 ho přepne.
- Edge: `welcome` jen s `width` výběr nezmění.
- Error: neznámá hodnota ve stavu se do selectu nedostane. Reducer ji odmítne.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `medium`. AGENT_MODELS: `composer-2.5`.
