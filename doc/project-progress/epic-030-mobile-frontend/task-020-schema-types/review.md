---
apm_category: task-review
apm_ref: E030.T020
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E030.T020 — Typy z JSON Schema

## Verdikt

APPROVE (round 1)

## Nálezy

Žádné.

## Ověření Definition of Done

- ✅ `web/src/protocol/generated.ts` vzniká ze `schema/cam-vision-bridge-v1.schema.json`: samostatný běh generátoru vytvořil bajtově shodný soubor. Hlavička obsahuje zákaz ruční editace.
- ✅ Test shody spouští generátor do dočasného souboru a porovnává čerstvý výstup s commitnutým souborem.
- ✅ Error case není formální: kopie s přidaným řádkem se od čerstvého výstupu skutečně liší; nezávislé ověření přes `cmp` potvrdilo shodu před změnou a neshodu po změně.
- ✅ Požadovaná Docker brána skončila s exit code 0.
- ✅ Všech 5 nových testů prošlo.
- ✅ Celá frontendová sada prošla: 3 testovací soubory, 10 testů, bez regresí.
- ✅ Vygenerované typy odpovídají ADR-002 a schématu: pokrývají `hello`, `welcome`, `error`, `frame`, `result` i všechny varianty výsledků; body používají `{x, y}`, hrany dvojice indexů, metriky `{name, value}` a `Text.x`/`Text.y` jsou volitelné a nullable.
- ✅ Npm script `generate:protocol` spouští kontrolovaný generátor bez nové závislosti; `package-lock.json` proto nevyžaduje změnu.

## Nezávislý výsledek testů

- `docker compose run --rm web npx vue-tsc --noEmit && docker compose run --rm web npx eslint . && docker compose run --rm web npx vitest run` — exit 0; Vitest: 3/3 soubory, 10/10 testů.
- `docker compose run --rm web npx vue-tsc --noEmit -p tsconfig.app.json && docker compose run --rm web npx vue-tsc --noEmit -p tsconfig.node.json` — exit 0; doplňkově ověřeny typy aplikace, testu i generátoru.
- Samostatný běh generátoru do dočasného souboru + `cmp` — exit 0; výstup byl shodný a přidaný řádek byl detekován jako drift.

Výsledky a počty souhlasí s `report.md`.

## Shrnutí

Review bylo path-scoped na `web/scripts/**`, `web/src/protocol/**`, `web/package.json`, `web/package-lock.json`, testy generování a soubory `dod.md` a `report.md` úlohy E030.T020. Ostatní změny v pracovním stromu nebyly reviewovány. Implementace ve vymezeném rozsahu splňuje specifikaci, ADR-002, schéma i ověřený DoD.
