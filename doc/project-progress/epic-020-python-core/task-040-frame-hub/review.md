---
apm_category: task-review
apm_ref: E020.T040
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E020.T040 — Frame, FrameHub, FakeTransport

## Verdikt

REQUEST CHANGES (round 1)

## Nálezy

| # | Severity | Místo | Popis | Doporučená oprava |
|---|----------|-------|-------|-------------------|
| 1 | major | `tests/core/test_frame_hub.py:68-88` | Error scénář ze `spec.md` není pokryt celý. Test ověří callback, nulové volání `cv2.imdecode` a čekání, ale místo následného platného snímku hub zavře. Neprokazuje tedy požadavek, že po neplatném vstupu `wait_frame` dál čeká a pozdější platný snímek vydá. | Po neplatném chunku spusťte `wait_frame`, ověřte, že čeká, vložte platný JPEG chunk a ověřte vrácený `Frame`; zachovejte kontrolu, že `cv2.imdecode` nebylo voláno pro neplatný vstup. |

## Ověření Definition of Done

- ✅ `Frame` je neměnný RGB snímek — `@dataclass(frozen=True, slots=True)`, bez setterů; test ověřuje zákaz změny atributu, RGB tvar a `uint8`.
- ✅ `FrameHub` publikuje jen nejnovější kompletní snímek — `_pending` je při každém dokončení nahrazen a test se dvěma kompletními snímky vrací `frame_id=2`.
- ✅ Neplatný vstup nejde do `cv2.imdecode` — ověřeno testem i nezávislou sondou s mockem; počet volání byl 0.
- ✅ `FakeTransport` nemá síť — implementace používá pouze `asyncio.Queue`; test ověřuje příjem, odeslání i ukončení bez síťového adaptéru.
- ✅ Ruff, mypy `--strict` a pytest končí s exit code 0 — nezávisle ověřeno.
- ✅ All new tests pass — test suite skončila `69 passed`.
- ✅ Full test suite passes (no regressions) — celý nakonfigurovaný pytest scope skončil úspěšně.

## Nezávislý výsledek testů

| Příkaz | Skutečný výsledek | Exit code |
|---|---|---:|
| `.venv/bin/ruff check .` | `All checks passed!` | 0 |
| `.venv/bin/ruff format --check .` | `20 files already formatted` | 0 |
| `.venv/bin/mypy src/ --strict` | `Success: no issues found in 13 source files` | 0 |
| `.venv/bin/pytest -q --tb=line` | `69 passed in 0.72s` | 0 |

Výsledky odpovídají údajům v `report.md`.

## Shrnutí

Review byl path-scoped na zadané soubory T040, protože pracovní strom obsahuje i
necommitnuté a nesledované změny ostatních tasků; ty nebyly hodnoceny. `experiments/`
podle `git status` nemá změny. Implementace požadované chování vykazuje a gate je zelený,
ale chybí trvalý test úplného zotavení po neplatném vstupu, proto je nutná oprava testu.
Reviewer medium původně přiřazený jako `gemini-4-hydrogen-high` nebyl dostupný; review
provedl schválený fallback `gpt-5.6-sol-medium`.

---

# Review Round 2: E020.T040

## Verdikt

APPROVE (round 2)

## Stav nálezů

| # | Původní severity | Stav | Ověření |
|---|-------------------|------|---------|
| 1 | major | ✅ vyřešeno | `tests/core/test_frame_hub.py:67-97` nyní po neplatném chunku spustí `wait_frame`, ověří, že stále čeká, vloží pozdější platný JPEG a ověří vrácený `Frame` s `frame_id=42`. Počet volání `cv2.imdecode` je před platným snímkem 0 a po něm přesně 1, takže neplatné bajty dekódovány nebyly. |

## Nezávislý výsledek testů

| Příkaz | Skutečný výsledek | Exit code |
|---|---|---:|
| `.venv/bin/ruff check .` | `All checks passed!` | 0 |
| `.venv/bin/ruff format --check .` | `20 files already formatted` | 0 |
| `.venv/bin/mypy src/ --strict` | `Success: no issues found in 13 source files` | 0 |
| `.venv/bin/pytest -q --tb=line` | `69 passed in 0.75s` | 0 |

## Shrnutí

Nález z kola 1 je v testovacím kódu úplně napraven a čerstvý gate je zelený. Review
zůstalo path-scoped na E020.T040; implementace nebyla editována. Reviewer medium
`gemini-4-hydrogen-high` nebyl dostupný, proto i kolo 2 provedl fallback
`gpt-5.6-sol-medium`. Task je připraven pro další APM krok.
