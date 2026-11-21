---
apm_category: dod
apm_ref: E010.T010
apm_level: task
created_by: Planner
model: claude-opus-5-5-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-21
updated_at: 2026-11-21
---

# Definition of Done: E010.T010

- ✅ `py/requirements.txt` existuje, všechny verze pinned (`==`), každá závislost má komentář-zdůvodnění
- ✅ Moduly `frame_codec.py`, `peerjs_signaling.py`, `echo_peer.py`, `results_writer.py`, `run_peer.py` existují s rozhraními podle `spec.md` § 3 a docstringy (Google style)
- ✅ Binární formát, JSON zprávy, limity a CSV schémata odpovídají `plan.md` § Společné konvence spiku (beze změn)
- ✅ Unit testy (`pytest -m unit`) pokrývají všechny případy z `spec.md` § 6 a procházejí
- ✅ Integrační test (`pytest -m integration`) aiortc ↔ EchoPeer v paměti prochází
- ✅ `ruff check .` a `ruff format --check .` bez chyb
- ✅ Ručně ověřeno: `run_peer.py` dostane od PeerJS cloudu `OPEN` a vypíše URL + QR kód (výpis logu v `report.md`)
- ✅ `README.md` experimentu má sekce *Goal*, *Setup (Python)*, *Run the peer* a připravené nadpisy *Measurement page*, *Results*, *Outcome*
- ✅ Žádné soubory mimo povolený rozsah (`spec.md` § 4) nejsou změněny
- ✅ All new tests pass
- ✅ Full test suite passes (no regressions)
