---
apm_category: task-report
apm_ref: E020.T030
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E020.T030 — Binární kodek snímku

## Co bylo implementováno

- Binární kodek v `cam_vision_bridge.protocol.frame_codec`: zpráva je `[uint32 BE header_len][UTF-8 JSON FrameHeader][JPEG této části]`.
- `pack_chunk` a `unpack_chunk` skládají a čtou jednu část. `split_jpeg` ji pro testy a budoucí transport rozdělí; `chunk_bytes == 0` znamená jednu část a přesný násobek nepřidá prázdný konec.
- `FrameAssembler.add` skládá části jednoho `frame_id` i mimo pořadí. Duplicitní `part` se ignoruje. Čas je injektovaný (`now`), nekompletní snímek starší než 2 s se zahodí.
- Průběžný součet se porovná s `total_bytes` dřív, než se nová část uloží. Po chybě se rozpracovaný snímek tohoto `frame_id` zahodí. JPEG se nedekóduje.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-020-python-core/plan.md`
- `doc/project-progress/epic-020-python-core/task-030-frame-codec/spec.md`
- `doc/project-progress/epic-020-python-core/task-030-frame-codec/dod.md`
- `src/cam_vision_bridge/protocol/messages.py`
- `src/cam_vision_bridge/protocol/__init__.py`
- `src/cam_vision_bridge/protocol/results.py`
- `doc/apm_config/DESIGN_RULES.user.md`
- `doc/project-progress/DECISIONS.md`
- `pyproject.toml`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/frame_codec.py`

### Vytvořeno

- `src/cam_vision_bridge/protocol/frame_codec.py`
- `tests/protocol/test_frame_codec.py`
- `doc/project-progress/epic-020-python-core/task-030-frame-codec/report.md`

### Změněno

- `doc/project-progress/epic-020-python-core/task-030-frame-codec/dod.md`

### Nedotčeno (Context Bundle)

- `experiments/2026-11-webrtc-peerjs-aiortc/py/frame_codec.py`
- `src/cam_vision_bridge/protocol/messages.py`
- `src/cam_vision_bridge/protocol/__init__.py`
- `doc/project-progress/epic-020-python-core/plan.md`
- `schema/cam-vision-bridge-v1.schema.json`

## Použité metody a rozhodnutí

### Limity na modelu, který je nehlídá

`FrameHeader` nechává `part`, `parts` a `total_bytes` jako holé `int`. Kodek je kontroluje sám: `header_len ≤ 4096`, `1 ≤ parts ≤ 256`, `0 ≤ part < parts`, `0 ≤ total_bytes ≤ 8 MiB`. Model se neměnil. `captured_at` zůstává řetězec, jak ho model definuje; druhý parser ISO 8601 by část platných hlaviček odmítl, a výčet limitů ho neobsahuje.

### Součet dřív než uložení

Nová, dosud neviděná část se do slovníku zapíše až po `dosavadní součet + len(payload) ≤ total_bytes`. Když by součet přetekl, výjimka `payload_sum` přijde před přiřazením a `add` rozpracovaný snímek tohoto `frame_id` smaže. Duplicitní `part` se do součtu nepočítá znovu. Po poslední části se JPEG spojí jen když součet je přesně `total_bytes`.

### Shoda částí a pád jen jednoho snímku

Shodná metadata jsou `parts` a `total_bytes`, jak je jmenuje `plan.md`. `w`, `h` a `captured_at` se mezi částmi neporovnávají. Klíč rozpracovaného snímku je samotné `frame_id` (hlavička nemá `run_id`). Chyba zahodí jen tento `frame_id`.

### Čas a timeout

`now` je volitelný. Bez něj se použije `time.monotonic`, testy předají vlastní hodiny. Hranice je přísně nad 2 s: v čase 2,0 s snímek zůstane, v čase 2,01 s se zahodí a další část začíná znovu. Zahodení zapíše `WARNING` (`incomplete_timeout`). Nevyhazuje výjimku a nepřidává metodu mimo specifikaci. `FrameProtocolError` nese `reason` a `frame_id`, aby je další task mohl předat dál.

### `split_jpeg`

Záporné `chunk_bytes` je chyba volajícího (`ValueError`), ne porušení drátového limitu. Prázdný JPEG je jedna prázdná část, ne nula částí.

## Odchylky od spec.md

—

## Reference do kódu

| File | Lines | Summary |
| --- | --- | --- |
| `src/cam_vision_bridge/protocol/frame_codec.py` | 34-46 | `FrameProtocolError` s `reason` a `frame_id` |
| `src/cam_vision_bridge/protocol/frame_codec.py` | 48-96 | `pack_chunk`, `unpack_chunk` |
| `src/cam_vision_bridge/protocol/frame_codec.py` | 98-146 | `split_jpeg` |
| `src/cam_vision_bridge/protocol/frame_codec.py` | 149-228 | `FrameAssembler` |
| `src/cam_vision_bridge/protocol/frame_codec.py` | 240-257 | `_store_part`: součet před uložením části |
| `src/cam_vision_bridge/protocol/frame_codec.py` | 326-341 | limity `parts`, `part`, `total_bytes` |
| `tests/protocol/test_frame_codec.py` | 26-77 | pack/unpack, 3 části, `parts = 1`, čas 2 s, duplicita |
| `tests/protocol/test_frame_codec.py` | 79-126 | `split_jpeg`: přesný násobek, `chunk_bytes == 0` |
| `tests/protocol/test_frame_codec.py` | 128-244 | limity, neplatný JSON, zpráva kratší než 4 B, bez dekodéru |

## Výsledek regresního testu

| Command / scope | Result | Notes |
| --- | --- | --- |
| `.venv/bin/ruff check .` | ✅ exit 0 | All checks passed |
| `.venv/bin/ruff format --check .` | ✅ exit 0 | 15 files already formatted |
| `.venv/bin/mypy src/ --strict` | ✅ exit 0 | 9 source files, no issues |
| `.venv/bin/pytest -q --tb=line` | ✅ exit 0 | 63 passed, včetně 25 nových v `test_frame_codec.py` |

## Definition of Done

Všechna kritéria v [dod.md](dod.md) jsou splněná. Kodek limity vynutí před vrácením JPEG bajtů a modul nevolá dekodér.
