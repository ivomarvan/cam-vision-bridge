---
apm_category: dod
apm_ref: E030.T010
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Definition of Done: E030.T010

- [x] ✅ `web/` je Vue 3 + Vite + TS strict + Tailwind + Pinia, bez Vue Router
- [x] ✅ `base` je `/cam-vision-bridge/v1/`
- [x] ✅ Docker image je `node:22.12.0-alpine` s digestem v `README.docker.md`
- [x] ✅ `vue-tsc`, ESLint a Vitest prošly v Dockeru
- [x] ✅ Python knihovna a `experiments/` zůstaly nedotčené
- [x] ✅ All new tests pass
- [x] ✅ Full test suite passes (no regressions)