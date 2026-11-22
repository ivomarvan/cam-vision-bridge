---
apm_category: task-review
apm_ref: E035.T010
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E035.T010 — Požadavek velikosti ve welcome

## Verdikt

APPROVE (round 1)

## Nálezy

Žádné.

## Ověření Definition of Done

- ✅ `capture_size` je na `PhoneCamera`; při `None` vznikne `Welcome(v=1, t="welcome")` a serializace neobsahuje `width`, `height` ani `fps`.
- ✅ `(1280, 720)` se po `hello` odešle jako `width=1280` a `height=720`; `fps` se neposílá.
- ✅ `(0, 480)` a `(-1, 480)` vyhodí `ValueError` přímo v konstruktoru. Parametrizovaný test navíc ověřuje nulovou výšku, necelé a řetězcové hodnoty a `bool`.
- ✅ Model `Welcome` v `src/cam_vision_bridge/protocol/messages.py` a `schema/` nemají změnu.
- ✅ Nové testy prošly jako součást úplné testovací sady.
- ✅ Úplná testovací sada prošla bez regresí.
- ✅ `experiments/` nemá změnu. Ve `web/` jsou souběžné změny jiného tasku; podle zadaného path scope nejsou součástí diffu E035.T010 ani tohoto review.

## Nezávislý výsledek testů

| Příkaz | Skutečný výsledek | Exit code |
|---|---|---:|
| `.venv/bin/ruff check .` | `All checks passed!` | 0 |
| `.venv/bin/ruff format --check .` | 25 souborů již správně formátováno | 0 |
| `.venv/bin/mypy src/ --strict` | Bez problémů v 15 zdrojových souborech | 0 |
| `.venv/bin/pytest` | 99 testů prošlo za 3,38 s | 0 |

Výsledky odpovídají `report.md`; rozdíl je pouze v době běhu pytest (report uvádí 3,48 s).

## Shrnutí

Review bylo path-scoped na `src/cam_vision_bridge/api/phone_camera.py`, taskem změněné testy a T010 `dod.md`/`report.md`; nesouvisející změny pracovního stromu nebyly posuzovány. Implementace i testy splňují specifikaci bez nálezů.
