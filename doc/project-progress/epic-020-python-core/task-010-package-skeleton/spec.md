---
apm_category: task-spec
apm_ref: E020.T010
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E020.T010 — Kostra balíčku

## 1. Goal

Vytvořit instalovatelný balíček `cam_vision_bridge` ve src-layout tak, aby
`pip install -e .` ve venv a brána Ruff, mypy `--strict` a pytest prošly na prázdných
modulech.

## 2. Inputs

- `doc/project-progress/spec.md` § 4.3 a 4.7
- `doc/apm_config/DESIGN_RULES.user.md`
- `doc/project-progress/epic-020-python-core/plan.md` § Společné konvence E020
- `.cursor/rules/100-python.mdc`

## 3. Outputs

- `pyproject.toml` — `name = "cam-vision-bridge"`, `requires-python = ">=3.11"`,
  setuptools src-layout. Runtime závislosti, každá pinned a s komentářem: `pydantic`,
  `opencv-python-headless`, `numpy`, `aiortc`, `websockets`, `qrcode`. Dev: `pytest`,
  `ruff`, `mypy`. Verze ověřit na PyPI. Ruff (E, F, I, UP, B, SIM, line-length 100,
  target py311), mypy strict, pytest markery `unit`, `integration`, `slow` a
  `pythonpath` tak, aby šel import balíčku.
- `src/cam_vision_bridge/__init__.py` a prázdné balíčky `protocol`, `core`, `transport`,
  `api` s `__init__.py` a module docstringem.
- `tests/test_package_imports.py` — import kořenového balíčku a čtyř podbalíčků.
- `README.md` v kořeni — anglicky: co knihovna je, `python3.12 -m venv .venv`,
  `pip install -e ".[dev]"`, příkazy brány. Sekce API zatím „filled in E020.T050“.
- Venv `.venv` v kořeni (gitignored). Nepřidávat závislost torch, ultralytics, qrdet.

## 4. Context Bundle

- **Read:** soubory ze § 2.
- **Do not modify:** `experiments/`, `doc/` kromě tohoto `report.md` a `dod.md`,
  `.cursor/`, `.gitignore` (už obsahuje `.venv`).
- **Interfaces from prior tasks:** žádné.

## 5. Dependencies

Žádné.

## 6. Test Specification

- Happy path: `import cam_vision_bridge` a podbalíčky.
- Edge: `cam_vision_bridge.__version__` je neprázdný řetězec.
- Error: import neexistujícího `cam_vision_bridge.missing` vyhodí `ModuleNotFoundError`.
- Brána: `ruff check .`, `ruff format --check .`, `mypy src/ --strict`, `pytest`.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `medium`. AGENT_MODELS: `composer-2.5`.
