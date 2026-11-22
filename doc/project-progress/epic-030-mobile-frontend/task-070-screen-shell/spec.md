---
apm_category: task-spec
apm_ref: E030.T070
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E030.T070 — Obrazovka, Wake Lock, fullscreen

## 1. Goal

Jedna mobilní obrazovka ukáže stav spojení, volbu kamery, kvalitu JPEG, živé video
s překryvem, panel textů a metrik, FPS a latenci. Zapne Screen Wake Lock a nabídne
fullscreen. Chyba verze a chybějící `#peer` jsou čitelné.

## 2. Inputs

- T060 kamera a kreslení, T050 relace
- `spec.md` § 2 (UI) a § 4.4

## 3. Outputs

- `web/src/App.vue` a malé komponenty ve `web/src/components/`.
- Wake Lock přes `navigator.wakeLock` s kontrolou podpory. Fullscreen přes standardní
  API, tlačítko se schová, když API není.
- Pinia store drží stav `idle | connecting | open | version-mismatch | error`,
  poslední texty, metriky, fps a latenci.
- Vitest na reducer nebo store: `welcome` v1 → `open`; `welcome` v2 → `version-mismatch`;
  prázdný hash zůstane `idle` s hláškou.

## 4. Context Bundle

- **Read:** T050, T060, `.cursor/rules/210-html.mdc`.
- **Do not modify:** Python, kodek.
- **Interfaces from prior tasks:** relace, kreslení, kamera.

## 5. Dependencies

T060.

## 6. Test Specification

- Happy path: store po `welcome` v1 je `open`.
- Edge: Wake Lock API chybí a komponenta to přežije (funkce vrátí `unsupported`).
- Error: hash bez `peer` nenastaví `connecting`.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `medium`. AGENT_MODELS: `composer-2.5`.
