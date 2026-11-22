---
apm_category: task-review
apm_ref: E020.T060
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E020.T060 — PeerJsWebRtcTransport

## Verdikt

APPROVE (round 1)

## Nálezy

| # | Severity | Místo | Popis | Doporučená oprava |
|---|----------|-------|-------|-------------------|
| — | — | — | Nebyly nalezeny žádné blocker, major ani minor nálezy. | — |

## Ověření Definition of Done

- ✅ `PeerJsWebRtcTransport` nevyžaduje pole `browser` v `OFFER`: `parse_offer` pole nečte a jednotkové testy ověřují chybějící i přítomné pole.
- ✅ Integrační test aiortc ↔ aiortc nechodí na veřejný cloud: SDP a ICE kandidáty předává v paměti, autouse fixture blokuje otevření PeerJS socketu i DNS překlad `0.peerjs.com`; cílený test prošel.
- ✅ Druhé spojení se při živém prvním odmítne: druhý `OFFER` nevytvoří odpověď ani nenahradí aktivní peer connection; původní DataChannel po odmítnutí dál přenáší bajty.
- ✅ `PhoneCamera()` bez argumentu použije tento transport: konstruktor vytváří `PeerJsWebRtcTransport`, zatímco injektovaný transport ponechá beze změny.
- ✅ Ruff, mypy `--strict` a pytest skončily s exit code 0.
- ✅ Všechny nové testy prošly: `tests/transport/test_peerjs_local.py` má 11 úspěšných testů.
- ✅ Celá testovací sada prošla bez regresí: 91 testů.

Další cílené kontroly:

- ✅ `OFFER` bez pole `browser` je přijat.
- ✅ Druhé živé spojení je odmítnuto.
- ✅ Binární DataChannel payload se předává beze změny; transport neparsuje chunk ani neskládá JPEG. Skládání zůstává nad transportem ve `PhoneCamera`/`FrameHub`.
- ✅ `experiments/` nemá podle `git status` žádnou změnu.
- ✅ DECISIONS #6 je dodrženo; `browser: "aiortc"` zůstává pouze ve zprávě `ANSWER`.

## Nezávislý výsledek testů

| Příkaz | Skutečný výsledek | Exit code |
|---|---|---:|
| `.venv/bin/ruff check` | `All checks passed!` | 0 |
| `.venv/bin/ruff format --check` | 24 souborů již naformátováno | 0 |
| `.venv/bin/mypy src/ --strict` | Bez nálezů v 15 zdrojových souborech | 0 |
| `.venv/bin/pytest -q --tb=line` | 91 passed in 1.15s | 0 |
| `.venv/bin/pytest -q --tb=line tests/transport/test_peerjs_local.py` | 11 passed in 0.76s | 0 |

Počty a exit kódy úplné sady odpovídají `report.md`.

## Shrnutí

Review byl výslovně path-scoped na `src/cam_vision_bridge/transport/peerjs.py`, změnu `PhoneCamera` nutnou pro výchozí transport, `tests/transport/**` a T060 `dod.md`/`report.md`; ostatní změněné či untracked soubory nebyly předmětem kontroly. Scoped soubory jsou v pracovním stromu untracked, proto byla ground truth ověřena z jejich skutečného obsahu a pro nové implementační soubory také přes `git diff --no-index`; výsledek je připraven pro Human review.
