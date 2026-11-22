---
apm_category: task-spec
apm_ref: E030.T040
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E030.T040 — Přepočet souřadnic

## 1. Goal

Jeden modul převede normalizovaný bod 0..1 na pixel v prvku, který zobrazuje video
s letterboxem. Přední kamera (`user`) zrcadlí jen osu x. Zadní kamera nezrcadlí.

## 2. Inputs

- `spec.md` § 4.2 (souřadnice a zrcadlení)
- `plan.md`

## 3. Outputs

`web/src/overlay/mapPoint.ts`:

```ts
mapPoint(point: {x:number,y:number}, view: {width,height}, frame: {width,height}, mirrorX: boolean): {x:number,y:number}
```

Video se vejde celé (contain). Přebytečný pás je letterbox. Bod mimo 0..1 funkce
neupravuje; volající ho nedostane z validovaného protokolu.

## 4. Context Bundle

- **Read:** spec § 4.2, T010.
- **Do not modify:** Python, protokolové typy.
- **Interfaces from prior tasks:** kostra `web/`.

## 5. Dependencies

T010. Na T020 nezávisí.

## 6. Test Specification

- Happy path: snímek 640×480 ve view 640×480, bod (0.5, 0.5) → (320, 240), bez zrcadlení.
- Edge: view 800×480 a snímek 640×480 dá vodorovný letterbox; bod (0, 0.5) leží na
  levém okraji obrazu, ne prvku. `mirrorX` převrátí x kolem středu obrazu.
- Error: záporný rozměr view vyhodí `RangeError`.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `medium`. AGENT_MODELS: `composer-2.5`.
