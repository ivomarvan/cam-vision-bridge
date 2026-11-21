---
name: node-dev
description: >-
  JavaScript / TypeScript / Node.js development workflow in Docker: npm ci, tsc type
  checking, ESLint, Prettier, Vitest unit tests, Playwright E2E, html-validate and axe
  accessibility checks, npm audit, and the `make check` deterministic gate. Use when
  running JS/TS tests, linting, type checking, validating HTML, auditing npm
  dependencies, or setting up the quality gate for a Node.js, Vite, or Vue project.
---

# JavaScript / TypeScript Development Workflow


Coding standards: `rules/210-html.mdc`, `rules/220-javascript.mdc`, `rules/230-typescript.mdc`.
Vue-specific commands (dev server, `vue-tsc`): `skills/vuejs-dev/SKILL.md`.

## Prerequisites


- Docker Compose environment is running: `docker compose up -d`.
- Check `docker-compose.yml` for the Node service name (commonly `frontend`, `web`, `app`).
- `package-lock.json` exists and is committed; `package.json` declares `"type": "module"`
  and `engines.node`.

## Installing Dependencies


```bash
# Reproducible install from the lockfile (Dockerfile, CI) — fails if lockfile is out of sync
npm ci

# Add a runtime / dev dependency — exact version (see .npmrc below)
docker compose exec <service> npm install <package>
docker compose exec <service> npm install -D <package>

# After any package.json change — rebuild the image (node_modules live in the image)
docker compose build <service> && docker compose up -d <service>
```

Project `.npmrc` (committed):

```ini
save-exact=true
engine-strict=true
```

> Before adding a package, run the `050-new-technology.mdc` checklist: maintainers,
> weekly downloads, last release, install scripts (`npm view <package> scripts`).
>
## Type Checking


```bash
docker compose exec <service> npx --no tsc --noEmit

# Watch mode during development
docker compose exec -it <service> npx --no tsc --noEmit --watch
```

## Linting and Formatting


```bash
# Lint — zero warnings allowed in the gate
docker compose exec <service> npx --no eslint --max-warnings=0 .

# Auto-fix
docker compose exec <service> npx --no eslint --fix .
docker compose exec <service> npx --no prettier --write .

# Check only (CI)
docker compose exec <service> npx --no prettier --check .
```

Minimal `eslint.config.js` (flat config, type-aware):

```js
import { defineConfig, globalIgnores } from 'eslint/config';
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier/flat';

export default defineConfig(
  globalIgnores(['dist/', 'coverage/']),
  js.configs.recommended,
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  { languageOptions: { parserOptions: { projectService: true } } },
  prettier, // last — turns off rules that conflict with Prettier
);
```

## Unit Tests (Vitest)


```bash
# All tests once
docker compose exec <service> npx --no vitest run

# Watch mode
docker compose exec -it <service> npx --no vitest

# Single file / by test name
docker compose exec <service> npx --no vitest run src/text/chunk-text.test.ts
docker compose exec <service> npx --no vitest run -t "returns an empty array"

# Coverage
docker compose exec <service> npx --no vitest run --coverage
```

## E2E and Accessibility (Playwright + axe)


```bash
# Use the official Playwright image (browsers preinstalled) as a compose service/profile
docker compose run --rm e2e npx --no playwright test
docker compose run --rm e2e npx --no playwright show-report
```

Accessibility check inside E2E tests — fails on WCAG 2.2 A/AA violations:

```ts
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test('orders page has no detectable WCAG A/AA violations', async ({ page }) => {
  await page.goto('/orders');
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);
});
```

## HTML Validation


```bash
# Static HTML and server-side templates rendered to HTML
docker compose exec <service> npx --no html-validate "public/**/*.html" "dist/**/*.html"
```

Minimal `.htmlvalidate.json`:

```json
{ "extends": ["html-validate:recommended", "html-validate:a11y"] }
```

## Dependency Audit


```bash
# Known vulnerabilities in production dependencies
docker compose exec <service> npm audit --omit=dev --audit-level=high

# Registry signatures / provenance of installed packages
docker compose exec <service> npm audit signatures

# Outdated packages (review, then update deliberately — never blind `npm update`)
docker compose exec <service> npm outdated
```

## Deterministic Gate — `make check`


The Coder, the Reviewer, and CI run the exact **same** command (see
`rules/090-apm-orchestration.mdc`). Copy the shipped template once per project:

```bash
# One-time setup per project
cp .cursor/skills/node-dev/templates/Makefile ./Makefile
mkdir -p .github/workflows
cp .cursor/skills/python-dev/templates/ci.yml .github/workflows/ci.yml   # stack-agnostic: runs `make check`
# Edit SERVICE (and TYPECHECK for Vue) in the Makefile
```

```bash
make check                                               # lint, format-check, typecheck, test
make check TYPECHECK="npx --no vue-tsc --noEmit"         # Vue project
make check RUNNER=                                       # native run (Docker-exempt project)
make audit                                               # separate: npm audit (not deterministic)
```

`make check` fails on the first non-zero exit. `npx --no` never downloads a missing tool,
so only the versions pinned in `package-lock.json` run.

## Container Shell


```bash
# Alpine-based images
docker compose exec -it <service> sh

# Debian-based images
docker compose exec -it <service> bash
```
