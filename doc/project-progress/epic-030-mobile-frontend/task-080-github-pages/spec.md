---
apm_category: task-spec
apm_ref: E030.T080
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E030.T080 — GitHub Actions Pages

## 1. Goal

Push na `master` sestaví `web/` a nasadí obsah na GitHub Pages tak, aby platila URL
`https://ivomarvan.github.io/cam-vision-bridge/v1/`. Workflow se z agenta nespouští.

## 2. Inputs

- `spec.md` § 4.1 a § 6 (cesta `/v1/` na Pages projektu `cam-vision-bridge`)
- Zelený `npm run build` z T010 a pozdějších tasků

## 3. Outputs

- `.github/workflows/pages.yml` — pinned `actions/checkout` a `actions/upload-pages-artifact`
  a `actions/deploy-pages` (major verze, kterou ověříš v dokumentaci akce v době
  implementace). Node stejný jako Docker, 22.12.0.
- Build s `base` `/cam-vision-bridge/v1/`. Artifact je `web/dist`.
- `README.md` dostane odstavec, jak stránku otevřít a že peer id je v hashi.
- Workflow nemá tajemství v repozitáři. `permissions` jen `contents: read` a
  `pages: write` / `id-token: write` podle aktuálního pages deploy.

## 4. Context Bundle

- **Read:** `web/vite.config.ts`, `README.docker.md`.
- **Do not modify:** aplikační logiku kamery a protokolu, Python.
- **Interfaces from prior tasks:** build skript.

## 5. Dependencies

T010. Spouštět až když `web/` má fungující `npm run build`. Když pozdější task build
rozbije, oprava patří tomu tasku, ne tiché změně base.

## 6. Test Specification

- Happy path: `docker compose run --rm web npm run build` skončí 0 a v `web/dist` je
  `index.html`.
- Edge: v `dist/index.html` je asset prefix `/cam-vision-bridge/v1/`.
- Error: workflow soubor je platný YAML a nespouští se na pull_request z forku s
  write právy (jen `push` na `master`).

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high` (CI). AGENT_MODELS: `grok-4.7-high`.
