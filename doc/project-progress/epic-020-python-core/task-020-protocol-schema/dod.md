---
apm_category: dod
apm_ref: E020.T020
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Definition of Done: E020.T020

- [x] Všechny zprávy a typy výsledků ze `spec.md` § 2 a § 4.2 mají model
- [x] Souřadnice mimo 0..1 a špatná verze neprojdou
- [x] `schema/cam-vision-bridge-v1.schema.json` je vygenerované a test ho porovná s novým během
- [x] Ruff, mypy `--strict` a pytest končí s exit code 0
- [x] All new tests pass
- [x] Full test suite passes (no regressions)
