# Deterministic quality gate for JavaScript / TypeScript (Node.js, Vite, Vue) projects.
#
# `make check` is the single command the Coder, the Reviewer, and CI all run — see
# skills/node-dev/SKILL.md and rules/090-apm-orchestration.mdc. "Passes" means the
# same thing in every one of those three contexts, because it is the same target.
#
# Copy this file to your project root (or frontend/) and adjust:
#   SERVICE    docker-compose.yml service name (commonly frontend, web, app)
#   LINT_PATHS paths passed to ESLint and Prettier (default: .)
#   TYPECHECK  type-check command; Vue projects: TYPECHECK="npx --no vue-tsc --noEmit"
#   RUNNER     how commands are executed. Default runs inside the compose service;
#              override for projects/spikes that run natively (Docker-exempt per
#              rules/030-docker-policy.mdc):  make check RUNNER=
#
# `npx --no` refuses to download a missing tool — the gate only runs the versions pinned
# in package-lock.json.

SERVICE    ?= app
LINT_PATHS ?= .
NPX        ?= npx --no
TYPECHECK  ?= $(NPX) tsc --noEmit
RUNNER     ?= docker compose exec -T $(SERVICE)

.PHONY: lint format-check typecheck test check audit

lint:
	$(RUNNER) $(NPX) eslint --max-warnings=0 $(LINT_PATHS)

format-check:
	$(RUNNER) $(NPX) prettier --check $(LINT_PATHS)

typecheck:
	$(RUNNER) $(TYPECHECK)

test:
	$(RUNNER) $(NPX) vitest run

## check — the deterministic gate: everything must pass, in this order, before a Task
## is considered done (Coder) or approved (Reviewer).
check: lint format-check typecheck test

## audit — known-vulnerability scan of production dependencies. Not part of `check`:
## its result changes when new advisories are published, without any code change.
audit:
	$(RUNNER) npm audit --omit=dev --audit-level=high
