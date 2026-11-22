---
apm_category: task-review
apm_ref: E020.T050
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E020.T050 — PhoneCamera

## Verdikt

APPROVE (round 1)

## Nálezy

Žádné.

## Ověření Definition of Done

- ✅ `PhoneCamera.frames`, `publish` a `run` fungují nad `FakeTransport`: testy ověřují
  příjem JPEG snímku, odeslání výsledku se stejným `frame_id` a pomocnou smyčku `run`.
- ✅ `start` vypíše URL s `#peer=`: ověřeno testem včetně generovaného ID a ASCII QR.
- ✅ Timeout a výjimka uživatele odpovídají `spec.md` § 6: `ConnectionTimeout` nastane bez
  dat a `RuntimeError` z callbacku se propaguje beze změny.
- ✅ Ruff, mypy `--strict` a pytest skončily s exit code 0 při nezávislém spuštění.
- ✅ Veřejný import `from cam_vision_bridge import PhoneCamera` existuje a je otestovaný.
- ✅ Všechny nové testy prošly.
- ✅ Celá testovací sada prošla bez regresí.

Další explicitní kontroly zadání: `start()` bez injektovaného transportu vyhazuje
`TransportNotConfigured`; `publish()` sestaví protokolový `Result` a měří
`processing_ms` od vydání snímku z `frames()`; test happy path kontroluje shodné
`frame_id`; testy používají pouze `FakeTransport` a neprovádějí PeerJS síťovou komunikaci.
`experiments/` nemá podle `git status --short -- experiments` žádné změny.

## Nezávislý výsledek testů

| Příkaz | Výsledek | Skutečný výstup |
|---|---|---|
| `.venv/bin/ruff check` | exit 0 | All checks passed |
| `.venv/bin/ruff format --check` | exit 0 | 22 files already formatted |
| `.venv/bin/mypy src/ --strict` | exit 0 | bez nálezů ve 14 zdrojových souborech |
| `.venv/bin/pytest -q --tb=line` | exit 0 | 79 passed in 0.93 s |

Výsledky souhlasí s `report.md`: stejné exit kódy, 22 formátovaných souborů,
14 zdrojových souborů pro mypy a 79 úspěšných testů.

## Shrnutí

Review byl záměrně path-scoped na `src/cam_vision_bridge/api/**`,
`src/cam_vision_bridge/__init__.py`, testy `PhoneCamera` a T050 `dod.md`/`report.md`;
ostatní necommitnuté a nesledované soubory nebyly předmětem review. Změna
`src/cam_vision_bridge/transport/fake.py` uvedená v reportu proto nebyla hodnocena jako
součást T050, pouze byl použit její veřejný kontrakt při ověření testů. Implementace ve
vymezeném rozsahu odpovídá specifikaci a je připravena pro Human review.
