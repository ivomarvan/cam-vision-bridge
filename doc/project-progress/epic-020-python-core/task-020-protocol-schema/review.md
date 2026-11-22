---
apm_category: task-review
apm_ref: E020.T020
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E020.T020 — Protokol v1 a JSON Schema

## Verdikt

APPROVE (round 1)

## Nálezy

Žádné.

## Ověření Definition of Done

- ✅ Všechny zprávy a typy výsledků ze `spec.md` § 2 a § 4.2 mají model: zprávy
  `hello`, `welcome`, `error`, `frame`, `result` a položky `box`, `quad`, `polygon`,
  `keypoints`, `polyline`, `text`, `metrics` jsou přítomné v diskriminovaných
  sjednoceních a čerstvě exportovaném schématu.
- ✅ Souřadnice mimo 0..1 a špatná verze neprojdou: rozsah je vynucen pro `box`,
  všechny body i poziční `text`; nezávislá kontrola potvrdila přijetí hranic 0 a 1,
  odmítnutí záporné souřadnice a odmítnutí `v=2`.
- ✅ `schema/cam-vision-bridge-v1.schema.json` je vygenerované a test ho porovná s
  novým během: bajtové porovnání s nezávisle čerstvě exportovaným souborem prošlo.
- ✅ Ruff, mypy `--strict` a pytest končí s exit code 0.
- ✅ Všechny nové testy procházejí.
- ✅ Celá testovací sada prochází bez regrese.

Adversární kontrola navíc potvrdila, že neznámé `t` zprávy i výsledku končí
`ValidationError`, `quad` se třemi body selže a `text` pouze s `x` selže.

## Nezávislý výsledek testů

| Příkaz / rozsah | Skutečný výsledek | Exit code |
|---|---|---:|
| `.venv/bin/ruff check .` | `All checks passed!` | 0 |
| `.venv/bin/ruff format --check .` | 13 souborů již naformátováno | 0 |
| `.venv/bin/mypy src/ --strict` | bez nálezů v 8 zdrojových souborech | 0 |
| `.venv/bin/pytest -q --tb=line` | 38 testů prošlo | 0 |
| Nezávislý adversární Python skript | všechny typy, hraniční souřadnice, chybné `v`/`t` a čerstvý export prošly | 0 |

Výsledky souhlasí s počty a exit kódy uvedenými v `report.md`.

## Shrnutí

Review byl path-scoped na `src/cam_vision_bridge/protocol/**`, `schema/**`,
`tests/protocol/**` a T020 `dod.md`/`report.md`, protože změny T020 nejsou v samostatném
commitu od T010; ostatní změny nebyly předmětem věcné kontroly. `git status` neukazuje
žádnou změnu pod `experiments/`. Specifikace ostatních tasků a `plan.md` jsou v celém
dosud necommitnutém stromu E020 vedené jako untracked, takže Git proti `HEAD` neumí
prokázat jejich historii změn; v rámci path-scoped review nebyly upravovány. T020 je
připravený pro Human review.
