---
apm_category: task-report
apm_ref: E020.T020
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E020.T020 — Protokol v1 a JSON Schema

## Co bylo implementováno

- Pydantic modely protokolu v1 v `cam_vision_bridge.protocol`: zprávy `hello`, `welcome`, `error`, `frame`, `result` s `v: Literal[1]` a diskriminátorem `t`.
- `ResultItem` jako diskriminované sjednocení `box`, `quad`, `polygon`, `keypoints`, `polyline`, `text`, `metrics`. Souřadnice jsou float 0..1 včetně. Neznámé `t`, `v != 1` a souřadnice mimo rozsah skončí `ValidationError`.
- `export_schema(path)` a `python -m cam_vision_bridge.protocol.export_schema` zapisují `schema/cam-vision-bridge-v1.schema.json`. Test porovná soubor na disku s čerstvým během.
- Kodek snímku ani `PhoneCamera` v tomhle tasku nejsou.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-020-python-core/plan.md`
- `doc/project-progress/epic-020-python-core/task-020-protocol-schema/spec.md`
- `doc/project-progress/epic-020-python-core/task-020-protocol-schema/dod.md`
- `doc/project-progress/spec.md`
- `doc/project-progress/DECISIONS.md`
- `doc/apm_config/DESIGN_RULES.user.md`
- `doc/project-progress/epic-020-python-core/task-030-frame-codec/spec.md`
- `pyproject.toml`
- `src/cam_vision_bridge/__init__.py`
- `src/cam_vision_bridge/protocol/__init__.py`
- `tests/test_package_imports.py`

### Vytvořeno

- `src/cam_vision_bridge/protocol/messages.py`
- `src/cam_vision_bridge/protocol/results.py`
- `src/cam_vision_bridge/protocol/export_schema.py`
- `schema/cam-vision-bridge-v1.schema.json`
- `tests/protocol/test_messages.py`
- `tests/protocol/test_results.py`
- `tests/protocol/test_schema.py`
- `doc/architecture/decisions/ADR-002-protocol-v1-json-shapes.md`
- `doc/project-progress/epic-020-python-core/task-020-protocol-schema/report.md`

### Změněno

- `src/cam_vision_bridge/protocol/__init__.py`
- `README.md`
- `doc/project-progress/DECISIONS.md`
- `doc/project-progress/epic-020-python-core/task-020-protocol-schema/dod.md`

### Nedotčeno (Context Bundle)

- `experiments/`
- `.cursor/`
- `doc/project-progress/epic-020-python-core/plan.md`
- `doc/project-progress/spec.md`
- `pyproject.toml`
- `src/cam_vision_bridge/core/`
- `src/cam_vision_bridge/transport/`
- `src/cam_vision_bridge/api/`
- `doc/project-progress/epic-020-python-core/task-010-package-skeleton/`
- `doc/project-progress/epic-020-python-core/task-030-frame-codec/`
- `doc/project-progress/epic-020-python-core/task-040-frame-hub/`
- `doc/project-progress/epic-020-python-core/task-050-phone-camera/`
- `doc/project-progress/epic-020-python-core/task-060-peerjs-transport/`

## Použité metody a rozhodnutí

### Jeden zdroj pravdy

Modely jsou kontrakt. JSON Schema se z nich jen generuje. Ruční úprava souboru neprojde testem, který schéma zapíše znovu a porovná bajty.

### Tvar geometrie a metrik

Spec pojmenovává značky a meze, ne každý JSON klíč. Zvolený tvar je v [ADR-002](../../../architecture/decisions/ADR-002-protocol-v1-json-shapes.md) a v DECISIONS #9:

- bod je `{x, y}` v poli `points` (quad přesně 4, polygon ≥ 3, polyline ≥ 2);
- hrana keypointů je `[i, j]`, index ≥ 0, bez kontroly proti délce `points`;
- metriky jsou seznam `{name, value}` v poli `metrics`;
- `label` a `score` jen u geometrických typů, ne u `text` a `metrics`;
- položka výsledku nenese `v`.

### Textové zprávy

Sjednocení ve schématu je `hello`, `welcome`, `error`, `frame`, `result`. Hlavička snímku je JSON s `t`. JPEG bajty do schématu nepatří. `part`, `parts` a `total_bytes` jsou na `FrameHeader` holá `int` — limity má až kodek v T030.

### Parsování

`parse_text_message` a `parse_result_item` validují už dekódovaný objekt. Neznámé pole je chyba (`extra=forbid`), ať peer nepropašuje klíč, který by se tiše zahodil. Instance jsou zmrazené. `fps` ve `welcome`, pokud je uvedeno, je `int` ≥ 1. Šířka a výška ve `welcome` jsou volitelné `int` bez dolní meze, protože spec tu mez píše jen u `fps`. `frame_id` je všude `int` ≥ 0, stejně jako u hlavičky snímku.

`export_schema` se z balíčku `protocol` znovu neexportuje. Funkce se jmenuje stejně jako modul a vazba na balíčku by zastínila `python -m cam_vision_bridge.protocol.export_schema`.

## Odchylky od spec.md

Žádný rozpor s pojmenovaným polem. Doplnění, která spec výslovně nepsala, jsou rozhodnutí výše a v ADR-002, ne druhý protokol:

- klíč `points` a objekt `{x, y}` — spec říká „body“ a rozsah 0..1;
- klíč `metrics` — spec říká seznam `name` + `value`;
- hrana jako JSON pole `[i, j]` — spec říká dvojici indexů v `edges`;
- `fps` jako `int` — spec říká jen ≥ 1, když je uvedeno;
- hlavička `t=frame` je součástí sjednocení textových zpráv;
- `frame_id` ≥ 0 i u `result` a volitelného `error.frame_id`;
- neznámý klíč je validační chyba, nejen neznámé `t` a špatné `v`.

Dopad: E030 importuje `FrameHeader` a nepřidává druhou hlavičku. Frontend typy půjdou z commitnutého schématu.

## Reference do kódu

| File | Lines | Summary |
| --- | --- | --- |
| `src/cam_vision_bridge/protocol/messages.py` | 23-78 | `Hello`, `Welcome`, `ErrorMessage`, `FrameHeader`, `Result` |
| `src/cam_vision_bridge/protocol/messages.py` | 81-101 | sjednocení `TextMessage`, `parse_text_message` |
| `src/cam_vision_bridge/protocol/results.py` | 33-119 | `Point`, `Metric`, geometrie, `Text`, `Metrics` |
| `src/cam_vision_bridge/protocol/results.py` | 122-141 | `ResultItem`, `parse_result_item` |
| `src/cam_vision_bridge/protocol/export_schema.py` | 29-87 | `export_schema`, `default_schema_path`, `main` |
| `schema/cam-vision-bridge-v1.schema.json` | 1-732 | vygenerované JSON Schema |
| `tests/protocol/test_messages.py` | 1-133 | round-trip zpráv a neplatné `v` / `t` |
| `tests/protocol/test_results.py` | 1-87 | geometrie, text bez/s `x,y`, souřadnice 1.1 |
| `tests/protocol/test_schema.py` | 19-43 | shoda schématu na disku s novým během |
| `doc/architecture/decisions/ADR-002-protocol-v1-json-shapes.md` | 1-44 | tvar `points`, `edges`, `metrics` |

## Výsledek regresního testu

| Command / scope | Result | Notes |
| --- | --- | --- |
| `.venv/bin/ruff check .` | exit 0 | All checks passed |
| `.venv/bin/ruff format --check .` | exit 0 | 13 files already formatted |
| `.venv/bin/mypy src/ --strict` | exit 0 | Success: no issues found in 8 source files |
| `.venv/bin/pytest -q --tb=line` | exit 0 | 38 passed (4 z T010 + nové testy protokolu) |

## Definition of Done

Všechna kritéria jsou splněná. Checklist je v [dod.md](dod.md).
