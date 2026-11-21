---
apm_category: dod
apm_ref: E010.T030
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-21
updated_at: 2026-11-21
---

# Definition of Done: E010.T030

- ✅ `py/analyze.py` existuje, používá jen standardní knihovnu, má typy a docstringy
- ✅ `summary.md` obsahuje sloupce v pořadí dle `spec.md` § 3
- ✅ p95 je počítán metodou nearest-rank; test to ověřuje na 20 hodnotách
- ✅ Testy z `spec.md` § 6 (happy path, edge, error) existují a procházejí
- ✅ `ruff check .` a `ruff format --check .` bez chyb
- ✅ `README.md` experimentu, sekce *Results*, popisuje spuštění `analyze.py`
- ✅ Pokud existují baseline CSV z T020: `summary.md` z nich vygenerováno
- ✅ All new tests pass
- ✅ Full test suite passes (no regressions)
