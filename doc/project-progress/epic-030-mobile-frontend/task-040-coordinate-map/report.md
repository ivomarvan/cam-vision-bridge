---
apm_category: task-report
apm_ref: E030.T040
apm_level: task
created_by: Coder
model: composer-2.5
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E030.T040 — Přepočet souřadnic

## Co bylo implementováno

Modul `mapPoint` převádí normalizované souřadnice (0..1 vůči odeslanému snímku) na pixely
v prvku zobrazení s chováním **object-fit: contain** — celý snímek se vejde, přebytek je
letterbox. Volitelné `mirrorX` otočí osu x kolem středu obrazu (přední kamera). Souřadnice
mimo interval 0..1 se neclampují. Záporný rozměr view vyvolá `RangeError`.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-030-mobile-frontend/task-040-coordinate-map/spec.md`
- `doc/project-progress/epic-030-mobile-frontend/task-040-coordinate-map/dod.md`
- `doc/project-progress/spec.md` § 4.2 (souřadnice a přepočet na mobilu)

### Vytvořeno

- `web/src/overlay/mapPoint.ts`
- `web/src/overlay/mapPoint.test.ts`
- `doc/project-progress/epic-030-mobile-frontend/task-040-coordinate-map/report.md`

### Změněno

- `doc/project-progress/epic-030-mobile-frontend/task-040-coordinate-map/dod.md` (zaškrtnutí DoD)

### Nedotčeno (Context Bundle)

- Python, `package.json`, protokolové typy, `experiments/`, session soubory

## Výsledek regresního testu

| Příkaz | Výsledek |
|---|---|
| `docker compose run --rm web npx vue-tsc --noEmit` | ✅ exit 0 |
| `docker compose run --rm web npx eslint .` | ✅ exit 0 |
| `docker compose run --rm web npx vitest run` | ✅ 26/26 testů, exit 0 |

## Definition of Done

Všechna kritéria splněna — viz [dod.md](dod.md).

## Odchylky od spec.md

—