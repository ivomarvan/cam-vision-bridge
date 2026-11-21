# Design Rules — CAM-VISION-BRIDGE

Project override of `.cursor/apm_config/DESIGN_RULES.default.md` — see the Config
Resolution mechanism in `rules/200-project-design-rules.mdc`.

## How to read this file

- **[general]** — a rule that holds regardless of this project. Once proven in practice,
  promote it into `rules/` (this template) and remove it from here.
- **[project]** — genuinely specific to this project; stays here.
- This file **adds to** the general rules in `rules/`, it does not restate them. If you
  find yourself copying something that `rules/070-project-management.mdc` or
  `rules/090-apm-orchestration.mdc` already say, delete it — link instead.

## Source of Truth

**[project]** Ordered list, as in `doc/project-progress/spec.md` § 7:
`doc/project-progress/DECISIONS.md` → `doc/project-progress/spec.md` →
`doc/project-progress/roadmap.md` → `doc/project-progress/brief.md` (context only).

## Overrides of template rules

**[project]** Explicit override of `rules/100-python.mdc` § *Imports and Structure*
(`from src.… import`, `git_root_to_syspath`):

- The Python library uses the **src-layout as an installable package**:
  `src/cam_vision_bridge/`, installed with `pip install -e .`.
- Imports use the **package name**: `from cam_vision_bridge.core import Frame` — never
  `from src.cam_vision_bridge…`, and no `git_root_to_syspath` in library modules.
- Reason: the library is imported by other projects, so it must be importable under its
  own name independent of any repository root.
- `experiments/<name>/py/` uses flat imports with `pythonpath = .` in its `pytest.ini`;
  no `src.` prefix, no `git_root_to_syspath`.

## Product invariants enforced in code

**[project]** Each must be checked by a test or the gate, not just claimed in a report:

- **One protocol source of truth.** Pydantic models in `cam_vision_bridge.protocol` →
  generated JSON Schema in `schema/` (committed) → generated TS types in `web/`. Generated
  files are never hand-edited; the gate fails if `schema/` is stale.
- **Versioned protocol.** Every message carries `v`. A breaking change bumps the major
  version and the frontend is deployed under a new path `/vN/`; old paths stay.
- **Phone input is untrusted.** Header and size limits are validated before any JPEG
  decode or file write; invalid input is dropped and logged, the connection survives.
- **Normalized coordinates.** All result geometry is in 0..1 relative to the sent frame;
  mirroring and letterbox mapping happen only in the frontend's mapping module.
- **Frames stay private.** The library never writes frames to disk or sends them anywhere
  except the paired peer; the signaling server sees only peer IDs and SDP.
- **Lean library.** No heavy CV/ML dependencies (torch, ultralytics, qrdet) in the
  library's dependencies — only under `examples/`.

## Deterministic gate

**[project]** A Task is gate-green when all applicable commands exit 0:

- Library (`src/`, `tests/`): `ruff check .`, `ruff format --check .`,
  `mypy src/ --strict`, `pytest`.
- Frontend (`web/`, in Docker): `vue-tsc --noEmit`, `eslint .`, `vitest run`.
- Spike (`experiments/…`): the commands in the Task's `dod.md` (no mypy requirement).

## Documentation language

**[project]** `README.md` files, ADRs (`doc/architecture/decisions/`), docstrings and code
comments are English (`brief.md`). APM documents in `doc/project-progress/` follow
`LANGUAGE.user.md` (Czech).

## Docker exemptions

**[project]** The Python library (`src/cam_vision_bridge/`, its tests and
`examples/`) runs **natively in a venv**, not in Docker (DECISIONS #4):

- WebRTC needs direct UDP and real host ICE candidates; inside a Docker bridge network
  this fails without `network_mode: host`, which is Linux-only and hides the problem
  being debugged.
- The library is imported into another project's Python process; it is not a standalone
  service, so a container would not reflect how it is actually used.

The frontend Node toolchain (`web/`: build, lint, tests) is **not** exempt — it runs in
Docker with a pinned image per `rules/030-docker-policy.mdc`.
