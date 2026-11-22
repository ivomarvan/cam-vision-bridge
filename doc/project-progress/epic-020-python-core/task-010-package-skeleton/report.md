---
apm_category: task-report
apm_ref: E020.T010
apm_level: task
created_by: Coder
model: composer-2.5
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E020.T010 — Kostra balíčku

## Co bylo implementováno

Instalovatelný balíček `cam_vision_bridge` ve src-layout (`pyproject.toml`, čtyři prázdné
podbalíčky s module docstringy, `__version__`), kořenové `README.md` s venv a bránou, smoke
testy importů a v kořeni repozitáře vytvořené venv `.venv` (3.12) s `pip install -e ".[dev]"`.
V `pyproject.toml` je Ruff `extend-exclude` pro `experiments/`, `doc/`, `.cursor/` a `web/`, aby
brána z kořene nevyžadovala úpravy nedotknutelných stromů.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/DECISIONS.md`
- `doc/apm_config/DESIGN_RULES.user.md`
- `doc/project-progress/epic-020-python-core/plan.md` (§ Společné konvence E020)
- `doc/project-progress/epic-020-python-core/task-010-package-skeleton/spec.md`
- `doc/project-progress/epic-020-python-core/task-010-package-skeleton/dod.md`
- `.cursor/rules/100-python.mdc`

### Vytvořeno

- `pyproject.toml`
- `README.md`
- `src/cam_vision_bridge/__init__.py`
- `src/cam_vision_bridge/protocol/__init__.py`
- `src/cam_vision_bridge/core/__init__.py`
- `src/cam_vision_bridge/transport/__init__.py`
- `src/cam_vision_bridge/api/__init__.py`
- `tests/test_package_imports.py`
- `.venv/` (lokální, gitignored)

### Změněno

- `doc/project-progress/epic-020-python-core/task-010-package-skeleton/dod.md`
- `doc/project-progress/epic-020-python-core/task-010-package-skeleton/report.md`

### Nedotčeno (Context Bundle)

- `experiments/`
- `.cursor/`
- `.gitignore`
- ostatní tasky v E020

## Výsledek regresního testu

| Příkaz | Výsledek | Exit code |
|--------|----------|-----------|
| `.venv/bin/ruff check .` | All checks passed | 0 |
| `.venv/bin/ruff format --check .` | 7 files already formatted | 0 |
| `.venv/bin/mypy src/ --strict` | Success: no issues found in 5 source files | 0 |
| `.venv/bin/pytest` | 4 passed | 0 |

## Definition of Done

Všechna kritéria splněna — viz [dod.md](dod.md), každá položka ✅.