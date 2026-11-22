---
apm_category: task-report
apm_ref: E035.T010
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E035.T010 — Požadavek velikosti ve welcome

## Co bylo implementováno

- `PhoneCamera` má keyword argument `capture_size: tuple[int, int] | None = None`. Výchozí `None` po `hello` pošle `Welcome(v=1, t="welcome")` bez `width`, `height` i `fps`.
- `(1280, 720)` přidá do stejné zprávy `width=1280` a `height=720`. `fps` se neposílá. JSON dál skládá stávající `_dump_message` s `exclude_none=True`.
- Nula, záporné číslo a necelé číslo vyhodí `ValueError` v konstruktoru, dřív než se přiřadí transport a dřív než kdokoli zavolá `start`.
- Model `Welcome` a JSON schema se neměnily.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-035-capture-size/task-010-welcome-capture-size/spec.md`
- `doc/project-progress/epic-035-capture-size/task-010-welcome-capture-size/dod.md`
- `doc/project-progress/epic-035-capture-size/plan.md`
- `doc/project-progress/DECISIONS.md`
- `doc/apm_config/DESIGN_RULES.user.md`
- `src/cam_vision_bridge/api/phone_camera.py`
- `src/cam_vision_bridge/protocol/messages.py`
- `tests/api/test_phone_camera.py`
- `tests/core/test_frame_hub.py`
- `.cursor/TEMPLATE_VERSION`

### Vytvořeno

- `doc/project-progress/epic-035-capture-size/task-010-welcome-capture-size/report.md`

### Změněno

- `src/cam_vision_bridge/api/phone_camera.py`
- `tests/api/test_phone_camera.py`
- `README.md`
- `doc/project-progress/epic-035-capture-size/task-010-welcome-capture-size/dod.md`

### Nedotčeno (Context Bundle)

- `schema/`
- `web/`
- `experiments/`
- `src/cam_vision_bridge/protocol/messages.py`
- `tests/core/test_frame_hub.py`

## Použité metody a rozhodnutí

### Kdy se velikost kontroluje

Kontrola běží v `__init__` hned po stávající `_validate_options` a před vytvořením `PeerJsWebRtcTransport`. Neplatná dvojice tedy neotevře transport ani nealokuje výchozí PeerJS klienta. Platná hodnota se uloží jako `_capture_size` a do runtime stavu smyčky se neplete.

### Co odejde ve welcome

`_welcome_message` při `None` vrátí `Welcome(v=1, t="welcome")`. Jinak předá jen `width` a `height`. `fps` se nepředává, takže zůstane `None` a do JSON se nedostane. Tvar zprávy je pořád stávající model; povolené presety telefonu řeší T020.

### Co je kladné celé číslo

Každá složka musí být `int` a `>= 1`. `bool` se odmítá, protože v Pythonu je podtřídou `int` a `True` by jinak odešlo jako šířka 1. Dvojice jiné délky a hodnota, která není `tuple`, padá stejnou `ValueError`. Horní mez ani seznam presetů se nekontroluje: PC smí požádat o libovolnou kladnou dvojici a telefon ji mapuje sám (DECISIONS #12, `plan.md`).

### ADR

Nové ADR nevzniklo. Parametr i volitelná pole `welcome` už jsou v DECISIONS #12 a v plánu epiky. Schema, závislosti ani smlouva pro T020 se nemění.

## Odchylky od spec.md

- **`bool` není rozměr.** Spec říká necelé číslo. `True` a `False` jsou v Pythonu `int`, přesto končí `ValueError` v konstruktoru. Dopad: `capture_size=(True, 480)` transport nespustí a do `welcome` neodejde `width=1`.
- **Délka dvojice.** Hodnota, která není `tuple` o dvou prvcích, také končí `ValueError` v konstruktoru. Bez toho by chyba vznikla až při skládání `welcome`, tedy po startu transportu. Požadované případy `(0, 480)`, `(-1, 480)` a necelá čísla se nemění.

## Reference do kódu

| File | Lines | Summary |
| --- | --- | --- |
| `src/cam_vision_bridge/api/phone_camera.py` | 68-99 | `PhoneCamera.__init__`: `capture_size`, validace před transportem |
| `src/cam_vision_bridge/api/phone_camera.py` | 273-279 | `_handle_text`: po `hello` odešle welcome |
| `src/cam_vision_bridge/api/phone_camera.py` | 401-423 | `_validate_capture_size`, `_positive_pixel` |
| `src/cam_vision_bridge/api/phone_camera.py` | 426-431 | `_welcome_message`: bez fps, rozměry jen když jsou zadané |
| `tests/api/test_phone_camera.py` | 138-150 | happy: `hello` pak welcome s 1280×720 |
| `tests/api/test_phone_camera.py` | 153-163 | edge: `capture_size=None` bez `width` a `height` |
| `tests/api/test_phone_camera.py` | 166-176 | error: neplatné dvojice a `ValueError` před `start` |
| `README.md` | 82-85 | veřejný popis `capture_size` |

## Výsledek regresního testu

| Command / scope | Result | Notes |
| --- | --- | --- |
| `.venv/bin/ruff check .` | ✅ exit 0 | All checks passed |
| `.venv/bin/ruff format --check .` | ✅ exit 0 | 25 files already formatted |
| `.venv/bin/mypy src/ --strict` | ✅ exit 0 | 15 source files |
| `.venv/bin/pytest` | ✅ exit 0 | 99 passed in 3.48s |

Nové případy jsou v tom součtu: jeden happy path, jeden edge a šest parametrů error testu (`(0, 480)`, `(-1, 480)`, `(1280, 0)`, `(1.5, 480)`, `(1280, "720")`, `(True, 480)`). Stávající assert, že po snímku odejde `welcome`, dál platí, protože výchozí `capture_size` je `None`. `tests/core/test_frame_hub.py` welcome neskládá přes `PhoneCamera` a prošel beze změny.

## Definition of Done

Všechna kritéria v [dod.md](dod.md) jsou splněná.
