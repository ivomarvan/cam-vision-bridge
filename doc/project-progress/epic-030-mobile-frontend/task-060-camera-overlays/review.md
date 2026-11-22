---
apm_category: task-review
apm_ref: E030.T060
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E030.T060 — Kamera a překryvy

## Verdikt

APPROVE (round 1)

## Nálezy

Žádné.

## Ověření Definition of Done

- ✅ JPEG jde z kamery ve velikosti 640×480: `captureFrame` nastaví rozměry canvasu,
  vykreslí zdrojový snímek přes devítiargumentové `drawImage` a předá `image/jpeg`
  spolu s argumentem kvality do `toBlob`. Test ověřuje zdroj 100×100, cílových
  640×480 i hodnotu kvality.
- ✅ Kamera používá injektované `getUserMedia`; test ověřuje `facingMode` `user`
  i `environment` a vypnuté audio.
- ✅ Všechny geometrické typy v1 se kreslí přes `mapPoint`: `box`, `quad`,
  `polygon`, `polyline`, body i hrany `keypoints` a text se souřadnicemi používají
  společnou projekci. Přední kamera předává `mirrorX: true`; test porovnává její x
  se zadní kamerou.
- ✅ Text bez úplných souřadnic a položky `metrics` se nekreslí a vracejí se
  odděleně v `PanelItems`; test s kontextem, který při každém přístupu vyhodí chybu,
  potvrzuje nulové kreslení.
- ✅ Prázdné `items` nevyvolají výjimku, nesáhnou na kontext a nevolají `stroke`.
- ✅ Docker brána je zelená: typová kontrola, ESLint i Vitest skončily s exit code 0.
- ✅ Všech 8 nových testů prošlo: 3 pro kameru a 5 pro překryvy.
- ✅ Celá frontendová sada prošla bez regrese: 8 souborů, 39 testů.

## Nezávislý výsledek testů

| Příkaz | Skutečný výsledek | Exit code |
| --- | --- | ---: |
| `docker compose run --rm web npx vue-tsc --noEmit` | bez diagnostiky | 0 |
| `docker compose run --rm web npx eslint .` | bez chyb | 0 |
| `docker compose run --rm web npx vitest run` | 8/8 souborů, 39/39 testů | 0 |

Výsledky, počty testů a exit kódy souhlasí s `report.md`.

## Shrnutí

Review bylo path-scoped na `web/src/camera/**`,
`web/src/overlay/drawItems.ts`, `web/src/overlay/drawItems.test.ts` a soubory
`dod.md` a `report.md` úlohy E030.T060; ostatní změny v pracovním stromu nebyly
reviewovány. `report.md` byl přečten až po implementaci, testech, stavu pracovního
stromu a nezávislém spuštění brány.

Python není v pracovním stromu změněný. `web/src/protocol/generated.ts`,
`web/src/overlay/mapPoint.ts`, `web/src/session/peerSession.ts` a `web/package.json`
jsou v kumulativním pracovním stromu změněné z dříve schválených úloh T020, T040
a T050; T060 je podle vymezených výstupů a doloženého pořadí úloh neměnila.
Implementace ve vymezeném rozsahu splňuje specifikaci a ověřený DoD.
