---
apm_category: task-spec
apm_ref: E030.T010
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E030.T010 — Kostra Vue v Dockeru

## 1. Goal

Ve `web/` běží Vue 3 + Vite + TypeScript strict + Tailwind + Pinia. Build, typy, lint
a Vitest jdou spustit v Dockeru s připnutým Node. Jedna prázdná obrazovka, bez routeru.

## 2. Inputs

- `plan.md` § Společné konvence E030
- `spec.md` § 4.4 a 4.7
- `.cursor/rules/110-vuejs-vite-tailwind.mdc`, `040-docker-standards.mdc`
- `.cursor/skills/vuejs-dev/SKILL.md`, `.cursor/skills/node-dev/SKILL.md`

## 3. Outputs

- `web/` s `package.json` (`"type": "module"`, `engines.node`), `package-lock.json`,
  `.npmrc` (`save-exact=true`, `engine-strict=true`), `vite.config.ts`
  (`base: "/cam-vision-bridge/v1/"`), `tsconfig.json` strict, Tailwind, ESLint, Vitest,
  Pinia.
- `web/src/App.vue` — jedna obrazovka s textem, že peer id se čte z hashe. Žádný Vue Router.
- `web/src/stores/session.ts` — Pinia store se stavem `idle`.
- `web/Dockerfile` multi-stage, `node:22.12.0-alpine` (ne `latest`), non-root ve
  finálním stage. `docker-compose.yml` služba `web` pro dev (`npm run dev` na portu 5173)
  a příkazy testů. `.dockerignore`.
- `README.docker.md` — jak `docker compose build` a jak spustit `vue-tsc`, `eslint`, `vitest`.
  Zapsat digest image.
- Jeden Vitest test: store začíná ve stavu `idle`.

Závislosti pinovat přes lockfile. Vue Router nepřidávat.

## 4. Context Bundle

- **Read:** soubory ze § 2.
- **Do not modify:** `src/cam_vision_bridge/`, `experiments/`, `schema/`, jiné tasky.
- **Interfaces from prior tasks:** žádné.

## 5. Dependencies

Žádné.

## 6. Test Specification

- Happy path: store `idle`.
- Edge: `import.meta.env.BASE_URL` v testu konfigurace začíná `/cam-vision-bridge/`.
- Error: chybějící peer v hashi store nepřepne z `idle` (funkce `peerIdFromHash("")` vrátí `null`).
- Brána v Dockeru: `vue-tsc --noEmit`, `eslint .`, `vitest run`.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `medium`. AGENT_MODELS: `composer-2.5`.
