---
apm_category: dod
apm_ref: E020.T050
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Definition of Done: E020.T050

- [x] `PhoneCamera.frames`, `publish` a `run` fungují nad `FakeTransport`
- [x] `start` vypíše URL s `#peer=`
- [x] Timeout a výjimka uživatele mají vlastní chování ze `spec.md` § 6
- [x] Ruff, mypy `--strict` a pytest končí s exit code 0
- [x] Veřejný import je `from cam_vision_bridge import PhoneCamera`
- [x] All new tests pass
- [x] Full test suite passes (no regressions)
