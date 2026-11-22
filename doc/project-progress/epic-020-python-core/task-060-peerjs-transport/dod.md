---
apm_category: dod
apm_ref: E020.T060
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Definition of Done: E020.T060

- [x] `PeerJsWebRtcTransport` nevyžaduje pole `browser` v OFFER
- [x] Integrační test aiortc ↔ aiortc nechodí na veřejný cloud
- [x] Druhé spojení se při živém prvním odmítne
- [x] `PhoneCamera()` bez argumentu použije tento transport
- [x] Ruff, mypy `--strict` a pytest končí s exit code 0
- [x] All new tests pass
- [x] Full test suite passes (no regressions)
