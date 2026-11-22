---
apm_category: task-review
apm_ref: E020.T030
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E020.T030 — Binární kodek snímku

## Verdikt

APPROVE (round 1)

## Nálezy

| # | Severity | Místo | Popis | Doporučená oprava |
|---|----------|-------|-------|-------------------|
| — | — | — | Nebyly nalezeny žádné závady. | — |

## Ověření Definition of Done

- ✅ `pack_chunk`, `unpack_chunk`, `FrameAssembler` a `split_jpeg` existují v `src/cam_vision_bridge/protocol/frame_codec.py`.
- ✅ Průběžný přesah se v `_store_part` odmítne před zápisem do `partial.payloads`; po chybě `add` zahodí rozpracovaný snímek daného `frame_id`.
- ✅ Spojení payloadů nastane v `_join_exact` až po kontrole, že průběžný součet přesně odpovídá `total_bytes`; nevzniká předčasný velký spojený buffer.
- ✅ Testy požadované v `spec.md` § 6 pokrývají happy path, pořadí částí, timeout, duplicitu, limity a chybné vstupy. Existující test průběžného přesahu selže pro staré chování bez kontroly před dokončením snímku.
- ✅ Ruff, formátování, mypy `--strict` a úplná sada pytest skončily s exit code 0.
- ✅ Modul neimportuje `cv2` ani nevolá `cv2.imdecode`; JPEG pouze balí, rozděluje a skládá.
- ✅ Všechny nové testy prošly: `tests/protocol/test_frame_codec.py` obsahuje 25 úspěšných testů v rámci úplné sady.
- ✅ Úplná sada prošla bez regresí: 63 testů.
- ✅ `experiments/` je podle `git status` a scoped kontroly beze změn.

## Nezávislý výsledek testů

| Příkaz | Skutečný výsledek | Exit code |
|---|---|---:|
| `.venv/bin/ruff check .` | `All checks passed!` | 0 |
| `.venv/bin/ruff format --check .` | `15 files already formatted` | 0 |
| `.venv/bin/mypy src/ --strict` | `Success: no issues found in 9 source files` | 0 |
| `.venv/bin/pytest -q --tb=line` | `63 passed in 0.35s` | 0 |

Výsledky a počty odpovídají tvrzením v `report.md`.

## Shrnutí

Review byl path-scoped na `src/cam_vision_bridge/protocol/frame_codec.py`,
`tests/protocol/test_frame_codec.py`, `dod.md` a `report.md` tasku E020.T030; ostatní
necommitnuté a nesouvisející soubory nebyly hodnoceny. Implementace odpovídá specifikaci,
včetně bezpečnostního pořadí kontroly průběžného součtu, a je připravena pro Human review.
