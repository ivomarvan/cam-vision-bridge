---
apm_category: dod
apm_ref: E020.T040
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Definition of Done: E020.T040

- [x] `Frame` je neměnný RGB snímek
- [x] `FrameHub` publikuje jen nejnovější kompletní snímek
- [x] Neplatný vstup nejde do `cv2.imdecode`
- [x] `FakeTransport` nemá síť
- [x] Ruff, mypy `--strict` a pytest končí s exit code 0
- [x] All new tests pass
- [x] Full test suite passes (no regressions)