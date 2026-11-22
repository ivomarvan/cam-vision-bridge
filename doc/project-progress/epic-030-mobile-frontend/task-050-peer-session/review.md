---
apm_category: task-review
apm_ref: E030.T050
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E030.T050 — PeerJS relace a tok snímků

## Verdikt

APPROVE (round 1)

## Nálezy

Žádné.

## Ověření Definition of Done

- ✅ Relace mluví protokolem v1 a `peerjs` je přesně `1.5.4` v `web/package.json` i `web/package-lock.json`. Po otevření datového kanálu test ověřuje odeslání `hello` s `v: 1`.
- ✅ Na cestě je nejvýš jeden snímek: druhé `sendFrame` před `result` nic neodešle; po `result` i protokolovém `error` je další snímek povolen.
- ✅ `welcome` s `v !== 1` nastaví `version-mismatch`; stav pak ignoruje další příchozí data a `sendFrame` už nic neposílá.
- ✅ PeerJS je injektovatelný přes `PeerClientFactory`. Testy používají fake, produkční továrnu nevolají a globální `WebSocket` nahrazují funkcí, která případný síťový pokus shodí. Běh testů nevolal `0.peerjs.com`.
- ✅ JPEG o velikosti 16 385 B se dělí pomocí `splitFrame` s `DEFAULT_CHUNK_BYTES` 16 384; test porovnává všechny odeslané části s výstupem kodeku.
- ✅ Echo protokol ze spiku nebyl převzat: v implementaci ani testech nejsou echo/ping/pong zprávy; relace používá pouze protokol v1 a PeerJS volby požadované specifikací.
- ✅ Docker brána je zelená: typová kontrola, ESLint i Vitest skončily s exit code 0.
- ✅ Všech 5 nových testů prošlo.
- ✅ Celá frontendová sada prošla: 6 testovacích souborů, 31 testů, bez regresí.
- ✅ `git status` neukazuje změny v Pythonu, `experiments/` ani `schema/`. `web/src/protocol/generated.ts` je mimo rozsah T050 a v pracovním stromu pochází z předchozí T020; test konzistence generovaného souboru v celé sadě prošel, takže nebyl zjištěn ruční drift.

## Nezávislý výsledek testů

| Příkaz | Skutečný výsledek | Exit code |
| --- | --- | --- |
| `docker compose run --rm web npx vue-tsc --noEmit` | Bez diagnostiky | 0 |
| `docker compose run --rm web npx eslint .` | Bez chyb | 0 |
| `docker compose run --rm web npx vitest run` | 6/6 souborů, 31/31 testů | 0 |

Výsledky, počty testů a exit kódy souhlasí s `report.md`.

## Shrnutí

Review bylo path-scoped na `web/src/session/**`, `web/package.json`, `web/package-lock.json` a soubory `dod.md` a `report.md` úlohy E030.T050; ostatní změny v pracovním stromu nebyly reviewovány. Implementace splňuje specifikaci, DECISIONS #6 i všechny ověřitelné položky DoD a je připravena pro uzavření úlohy v rámci epiky.
