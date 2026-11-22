---
apm_category: task-report
apm_ref: E035.T030
apm_level: task
created_by: Coder
model: composer-2.5
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E035.T030 — Výběr velikosti na obrazovce

## Co bylo implementováno

Do `CaptureSettings.vue` přibyl select se třemi presety (`640×480`, `1280×720`, `1920×1080`) vedle přepínače kamery. Změna volá `setCapturePreset` ve store; existující `watch` v `App.vue` na `captureSize` znovu otevře kameru. Po zakódování snímku store drží skutečnou velikost bitmapy a UI ji zobrazí, když se liší od vybraného presetu. Reducer `reduceCaptureSize` odmítne neznámé rozměry.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-035-capture-size/task-030-size-picker/spec.md`
- `doc/project-progress/epic-035-capture-size/task-030-size-picker/dod.md`
- `web/src/camera/captureSize.ts`
- `web/src/components/CaptureSettings.vue`
- `web/src/stores/session.ts`
- `web/src/App.vue`

### Vytvořeno

- `doc/project-progress/epic-035-capture-size/task-030-size-picker/report.md`

### Změněno

- `web/src/components/CaptureSettings.vue`
- `web/src/stores/session.ts`
- `web/src/stores/sessionReducer.ts`
- `web/src/stores/session.test.ts`
- `web/src/App.vue`
- `doc/project-progress/epic-035-capture-size/task-030-size-picker/dod.md`

### Nedotčeno (Context Bundle)

- Python, schema, `experiments/`
- `web/src/camera/captureSize.ts` (pouze import v komponentě a reduceru)

## Odchylky od spec.md

—

## Výsledek regresního testu

| Command / scope | Result | Notes |
|-----------------|--------|-------|
| `docker compose run --rm web npx vue-tsc --noEmit` | ✅ exit 0 | |
| `docker compose run --rm web npx eslint .` | ✅ exit 0 | |
| `docker compose run --rm web npx vitest run` | ✅ 65/65 | včetně nových testů `reduceCaptureSize` a store presetů |

## Definition of Done

Všechna kritéria v [dod.md](dod.md) jsou splněna (všechny položky ✅).