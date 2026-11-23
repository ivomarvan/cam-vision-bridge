---
apm_category: epic-plan
apm_ref: E040
apm_level: epic
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Epic Plan: E040 — Ukázka qrdet, dokumentace, ověření DoD

## Epic Goal

Cizí skript dostane snímky z telefonu, najde QR kód a pošle zpět quad plus
dekódovaný text. Torch zůstane mimo knihovnu. Měření FPS a latence ve spec § 6
dělá Human na telefonu.

Human 2026-11-22 zadal pokračování hned po E035. FE.2 se nečeká (DECISIONS #11).

## Task List

| Task | Name | Depends on | Band |
|------|------|-----------|------|
| T010 | Ukázka `examples/qrdet_demo/` | — | medium |
| T020 | Anglické README: instalace, párování, API, typy, limity | — | low |
| T030 | Ruční ověření DoD na telefonu | T010 | — |

T010 a T020 jsou v pracovním stromu `master` a ještě nejsou commitnuté. T030 umí
jen Human: naskenovat QR, přečíst kód telefonem a zapsat FPS a latenci.

## Konvence

- Detekce jde přes `QReader.detect_and_decode(..., return_detections=True)`.
  Rohy se berou z `quad_xyn` (už 0..1) a oříznou se do intervalu.
- Dekódovaný text je položka `text` bez souřadnic, tedy do panelu. Quad nese
  stejný text v `label`.
- Výchozí velikost snímku ukázky je 640×480.
- Párování je stejné jako `examples/run_phone.py`: stránka na portu 5173 a jeden
  QR kód. Druhý způsob se nepřidává.
