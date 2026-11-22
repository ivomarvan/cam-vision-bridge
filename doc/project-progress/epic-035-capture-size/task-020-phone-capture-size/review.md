---
apm_category: task-review
apm_ref: E035.T020
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E035.T020 — Velikost snímku na telefonu

## Verdikt

APPROVE (round 1)

## Nálezy

Bez nálezů.

## Ověření Definition of Done

- ✅ Seznam obsahuje pouze 640×480, 1280×720 a 1920×1080; výchozí je první položka.
- ✅ Úplné `welcome` se mapuje přes `nearestPreset` podle počtu pixelů, při remíze zůstává menší preset. Neúplné `welcome` vrací `null` a aktuální volbu nemění.
- ✅ Canvas používá skutečné `videoWidth`/`videoHeight`; 3840×2160 se zmenší na 1920×1080 se zachovaným poměrem stran.
- ✅ Nulová šířka videa vyvolá `RangeError` před kreslením a před vytvořením JPEG.
- ✅ Jediné `hello` používá velikost dostupnou při otevření relace; hlavička každého snímku dostane rozměry právě vytvořeného canvasu přes `setCaptureSize`.
- ✅ `PeerSession` neposílá druhé `hello`; samostatný test ověřuje jednu textovou zprávu i po změně velikosti hlavičky snímku.
- ✅ Přepínač `facingMode` i jeho watch zůstávají zapojené a constraints nadále používají přesný režim kamery.
- ✅ V rozsahu tasku nebyly změněny `schema/` ani `experiments/`. Změny Pythonu ve společném pracovním stromu patří k nesouvisejícímu T010 a nebyly důvodem k neúspěchu tohoto review.
- ✅ Nové testy prošly.
- ✅ Celá frontendová sada prošla bez regrese.

## Nezávislý výsledek testů

| Příkaz | Skutečný výsledek | Exit code |
| --- | --- | --- |
| `docker compose run --rm web npx vue-tsc --noEmit` | bez chyb | 0 |
| `docker compose run --rm web npx eslint .` | bez chyb a varování | 0 |
| `docker compose run --rm web npx vitest run` | 10 souborů, 60/60 testů | 0 |

První souběžný běh Vitestu skončil chybou fondu workerů (`Timeout starting forks runner`).
Samostatné opakování stejného příkazu prošlo celé s exit code 0. Údaje v `report.md`
odpovídají úspěšnému nezávislému běhu.

## Shrnutí

Review bylo path-scoped na `web/src/camera/**`, nezbytné zapojení v session/store a
`App.vue` a dokumenty T020; nesouvisející změny ve společném pracovním stromu nebyly
reviewovány. Implementace i testy splňují specifikaci a task je připraven pro Human review.
