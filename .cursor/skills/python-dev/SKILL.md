---
name: python-dev
description: >-
  Python development workflow in Docker: run scripts, pytest tests (by marker, file,
  coverage), Ruff linter + formatter, mypy strict type checking, dependency management.
  Use when running Python scripts, tests, or code quality checks inside the project.
---

# Python Development Workflow


## Prerequisites


- Docker Compose environment is running: `docker compose up -d`
- Check `docker-compose.yml` for the Python service name (commonly `api`, `backend`, `app`).

## Running Scripts


```bash
# Run any script — absolute imports work regardless of cwd (git_root_to_syspath)
docker compose exec <service> python src/module/script.py

# Pass arguments
docker compose exec <service> python src/module/script.py --arg value

# Interactive (stdin open)
docker compose exec -it <service> python src/module/script.py

# Open REPL
docker compose exec -it <service> python
```

## Running Tests (pytest)


```bash
# All tests
docker compose exec <service> pytest

# By marker (defined in pyproject.toml)
docker compose exec <service> pytest -m unit
docker compose exec <service> pytest -m integration
docker compose exec <service> pytest -m "not slow"

# Single file or directory
docker compose exec <service> pytest tests/module/test_parser.py
docker compose exec <service> pytest tests/module/

# Verbose + stop on first failure
docker compose exec <service> pytest -v -x

# Coverage report
docker compose exec <service> pytest --cov=src --cov-report=term-missing
```

## Code Quality


### Ruff — Linter and Formatter


```bash
# Check and auto-fix linting issues
docker compose exec <service> ruff check --fix .

# Format code
docker compose exec <service> ruff format .

# Check only — no changes (for CI)
docker compose exec <service> ruff check .
docker compose exec <service> ruff format --check .
```

### mypy — Static Type Checking


```bash
# Check src/ (uses settings from pyproject.toml)
docker compose exec <service> mypy src/

# Single file
docker compose exec <service> mypy src/module/parser.py

# Override to strict for one-off check
docker compose exec <service> mypy src/ --strict
```

### Deterministic Gate — `make check`


The manual chain above is fine for local auto-fixing, but the Coder, the Reviewer, and
CI need the exact **same** command so "passes" means the same thing in every context —
see `rules/090-apm-orchestration.mdc`. Copy the shipped template once per project:

```bash
# One-time setup per project
cp .cursor/skills/python-dev/templates/Makefile ./Makefile
mkdir -p .github/workflows
cp .cursor/skills/python-dev/templates/ci.yml .github/workflows/ci.yml
# Edit Makefile's SERVICE variable if your docker-compose service isn't named "app"
```

```bash
# Every subsequent run — Coder before writing report.md, Reviewer at Step R3, CI on push
make check
```

`make check` runs `ruff check`, `ruff format --check`, `mypy --strict`, `pytest`, in that
order, and fails on the first non-zero exit. This is the Python instance of the generic
"deterministic gate" concept — JS/TS/Vue (`skills/node-dev/templates/`) and PHP
(`skills/php-dev/templates/`) ship the same shape; C++/ESP32 does not have one yet (see
`README.md`, "Deterministic gate coverage"). The `ci.yml` above only runs `make check`,
so it serves every stack.

### Full Quality Gate (manual, auto-fixing)


```bash
docker compose exec <service> ruff check --fix . \
  && docker compose exec <service> ruff format . \
  && docker compose exec <service> mypy src/
```

## Dependency Management


```bash
# After changing requirements.txt / pyproject.toml — rebuild and restart
docker compose build <service>
docker compose up -d <service>

# Quick test of a new package inside a running container
docker compose exec <service> pip install <package>
# ⚠️ Then add to requirements.txt/pyproject.toml and rebuild — lost on container restart
```

## Container Shell


```bash
# Open bash in container
docker compose exec -it <service> bash

# As root (for debugging permission issues)
docker compose exec -it -u root <service> bash
```
