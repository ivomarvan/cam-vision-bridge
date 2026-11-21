# Deterministic quality gate for PHP projects.
#
# `make check` is the single command the Coder, the Reviewer, and CI all run — see
# skills/php-dev/SKILL.md and rules/090-apm-orchestration.mdc. "Passes" means the
# same thing in every one of those three contexts, because it is the same target.
#
# Copy this file to your project root and adjust:
#   SERVICE  docker-compose.yml service name (commonly php, app, backend)
#   RUNNER   how commands are executed. Default runs inside the compose service;
#            override for projects/spikes that run natively (Docker-exempt per
#            rules/030-docker-policy.mdc):  make check RUNNER=
#
# Tool configuration lives in the project, not here: .php-cs-fixer.dist.php,
# phpstan.neon(.dist), phpunit.xml(.dist).

SERVICE ?= app
RUNNER  ?= docker compose exec -T $(SERVICE)

.PHONY: validate format-check typecheck test check audit

validate:
	$(RUNNER) composer validate --strict

format-check:
	$(RUNNER) vendor/bin/php-cs-fixer check --diff

typecheck:
	$(RUNNER) vendor/bin/phpstan analyse --no-progress

test:
	$(RUNNER) vendor/bin/phpunit

## check — the deterministic gate: everything must pass, in this order, before a Task
## is considered done (Coder) or approved (Reviewer).
check: validate format-check typecheck test

## audit — known-vulnerability scan of dependencies. Not part of `check`: its result
## changes when new advisories are published, without any code change.
audit:
	$(RUNNER) composer audit
