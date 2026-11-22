---
apm_category: task-review
apm_ref: E030.T040
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E030.T040 — Přepočet souřadnic

## Verdikt

APPROVE (round 1)

## Nálezy

Žádné.

## Ověření Definition of Done

- ✅ `mapPoint` řeší contain, letterbox a zrcadlení x: implementace počítá jednotné
  měřítko, oba letterbox offsety a při `mirrorX` převrací normalizované x kolem středu
  obrazu.
- ✅ Testy ze `spec.md` § 6 procházejí: ověřeno pro střed 640×480, vodorovný letterbox
  800×480 s bodem na x = 80, zrcadlení x a záporné rozměry view s `RangeError`.
- ✅ Brána v Dockeru je zelená: typecheck, ESLint i Vitest skončily s exit code 0.
- ✅ Všechny nové testy procházejí: `mapPoint.test.ts` má 5 úspěšných testů.
- ✅ Celá testovací sada prochází bez regrese: 5 souborů, 26 testů.

## Nezávislý výsledek testů

| Příkaz | Skutečný výsledek | Exit code |
|---|---|---:|
| `docker compose run --rm web npx vue-tsc --noEmit` | bez chyb | 0 |
| `docker compose run --rm web npx eslint .` | bez chyb | 0 |
| `docker compose run --rm web npx vitest run` | 5/5 souborů, 26/26 testů | 0 |

Výsledky odpovídají údajům v `report.md`.

## Shrnutí

Revize byla path-scoped na `web/src/overlay/**` a na `dod.md` a `report.md` úlohy
E030.T040; ostatní změny v pracovním stromu nebyly předmětem revize. Diff a stav cest
potvrdily, že Python ani `experiments/` nejsou změněné. `web/package.json` a
`web/src/protocol/**` jsou v pracovním stromu změněné z jiných úloh, ale nepatří do
výstupů ani path scope E030.T040 a tato úloha je podle svého diffu a reportu neměnila.

Předepsaný model Reviewer medium `gemini-4-hydrogen-high` nebyl dostupný; revizi proto
provedl náhradní model `gpt-5.6-sol-medium`. Implementace splňuje specifikaci a je
připravena pro uzavření v rámci epiky.
