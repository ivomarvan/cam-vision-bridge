---
apm_category: task-report
apm_ref: E020.T040
apm_level: task
created_by: Coder
model: composer-2.5
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-23
---

# Task Report: E020.T040 — Frame, FrameHub, FakeTransport

## Co bylo implementováno

- Neměnný dataclass `Frame` s RGB `ndarray` a metadaty snímku.
- Asyncio `FrameHub`: skládání chunků přes `FrameAssembler`, JPEG dekód až po kompletním snímku,
  držení jen nejnovějšího nepřevzatého snímku, `on_protocol_error` a `close()`.
- Protokol `Transport` a frontový `FakeTransport` pro testy bez sítě.
- Jednotkové testy happy path, edge (dva snímky před `wait_frame`), chybný vstup bez `imdecode`
  a zotavení: po neplatném chunku `wait_frame` čeká, platný JPEG vrátí `Frame`.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-020-python-core/plan.md`
- `doc/project-progress/epic-020-python-core/task-040-frame-hub/spec.md`
- `src/cam_vision_bridge/protocol/frame_codec.py`
- `src/cam_vision_bridge/protocol/messages.py`

### Vytvořeno

- `src/cam_vision_bridge/core/frame.py`
- `src/cam_vision_bridge/core/frame_hub.py`
- `src/cam_vision_bridge/transport/base.py`
- `src/cam_vision_bridge/transport/fake.py`
- `tests/core/test_frame_hub.py`
- `doc/project-progress/epic-020-python-core/task-040-frame-hub/report.md`

### Změněno

- `src/cam_vision_bridge/core/__init__.py`
- `src/cam_vision_bridge/transport/__init__.py`
- `doc/project-progress/epic-020-python-core/task-040-frame-hub/dod.md`

## Výsledek regresního testu

Oprava review round 1 (nález #1): rozšířen error test o čekání a následný platný snímek.

| Příkaz | Výsledek |
|--------|----------|
| `.venv/bin/ruff check .` | exit 0 |
| `.venv/bin/ruff format --check .` | exit 0 |
| `.venv/bin/mypy src/ --strict` | exit 0 |
| `.venv/bin/pytest -q --tb=line` | exit 0, 69 passed (0.82 s) |

## Definition of Done

Všechna kritéria splněna — viz [dod.md](dod.md).