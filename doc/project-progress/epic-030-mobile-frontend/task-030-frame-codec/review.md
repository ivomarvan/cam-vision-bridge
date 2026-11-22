---
apm_category: task-review
apm_ref: E030.T030
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E030.T030 — Binární kodek ve stránce

## Verdikt

APPROVE (round 1)

## Nálezy

Žádné.

## Ověření Definition of Done

- ✅ **Kodek sedí na hlavičku protokolu v1:** `packChunk` zapisuje čtyřbajtovou
  big-endian délku UTF-8 JSON hlavičky a za ni JPEG bajty dané části. Hlavička má
  pořadí klíčů `v`, `t`, `frame_id`, `captured_at`, `w`, `h`, `part`, `parts`,
  `total_bytes`.
- ✅ **Testy ze `spec.md` § 6 procházejí v Dockeru:** ověřeno 11 testy kodeku,
  včetně 100 000 / 16 384 bez prázdného konce, přesného násobku, `chunkBytes = 0`,
  neznámého `t` a `v !== 1`.
- ✅ **Brána je zelená:** všechny tři předepsané frontendové příkazy skončily s
  exit code 0.
- ✅ **All new tests pass:** `web/src/protocol/frameCodec.test.ts` — 11/11.
- ✅ **Full test suite passes (no regressions):** 4/4 testovací soubory, 21/21 testů.

## Nezávislý výsledek testů

| Příkaz | Skutečný výsledek | Exit code | Porovnání s `report.md` |
| --- | --- | ---: | --- |
| `docker compose run --rm web npx vue-tsc --noEmit` | bez diagnostik | 0 | shoda |
| `docker compose run --rm web npx eslint .` | bez diagnostik | 0 | shoda |
| `docker compose run --rm web npx vitest run` | 4/4 soubory, 21/21 testů; kodek 11/11 | 0 | shoda |
| `docker compose run --rm web npx vue-tsc --noEmit -p tsconfig.app.json` | bez diagnostik | 0 | shoda s doplňkovým tvrzením reportu |

## Shrnutí

Revize byla kvůli necommitnutým změnám více Tasků **path-scoped** na
`web/src/protocol/frameCodec.ts`, `web/src/protocol/frameCodec.test.ts`, místní
`dod.md` a `report.md`; ostatní soubory nebyly věcně revidovány. Stav repozitáře
neukazuje změny v Pythonu, `experiments/` ani `schema/`. `generated.ts` je v
pracovním stromu stále untracked artefakt předchozího T020, ale jeho čas změny
předchází oběma souborům T030 a v rozsahu T030 nebyl změněn. Implementace splňuje
specifikaci a je připravena pro uzavření Tasku v rámci Epicu.
