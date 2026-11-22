---
apm_category: dod
apm_ref: E020.T010
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Definition of Done: E020.T010

- [x] `pip install -e ".[dev]"` ve `.venv` projde
- [x] `pyproject.toml` pinuje runtime i dev závislosti a má komentář u každé
- [x] Ruff, mypy `--strict` a pytest končí s exit code 0
- [x] Import balíčku a podbalíčků je otestovaný
- [x] `experiments/` a cizí tasky zůstaly nedotčené
- [x] All new tests pass
- [x] Full test suite passes (no regressions)