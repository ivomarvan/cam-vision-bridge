# Design Rules — Default Configuration

No project-specific design invariants are defined by default. A consuming project
overrides this file **in full** by creating `doc/apm_config/DESIGN_RULES.user.md` — see
the Config Resolution mechanism in `rules/200-project-design-rules.mdc`.

## How to read this file (keep this section when you fill in `.user.md`)

- **[general]** — a rule that holds regardless of this project. Once proven in practice,
  promote it into `rules/` (this template) and remove it from here.
- **[project]** — genuinely specific to this project; stays here.
- This file **adds to** the general rules in `rules/`, it does not restate them. If you
  find yourself copying something that `rules/070-project-management.mdc` or
  `rules/090-apm-orchestration.mdc` already say, delete it — link instead.

## Suggested sections (fill in `DESIGN_RULES.user.md`)

- **Source of Truth** — which document is the active SoT for this project (the *rule*
  for handling SoT conflicts lives in `rules/070-project-management.mdc`; only the pointer
  is project data).
- **Forbidden technologies** — with justification.
- **Product invariants enforced in code** — the handful of promises that must be checked
  by a test/gate, not just claimed in a report (e.g. verified citations, budget caps,
  license flags) — this is normally the bulk of this file.
- **Documentation language outside APM** — `<communication-language>` (`LANGUAGE.user.md`)
  already covers chat and APM reports; state here only if free-form docs (`doc/`,
  `private_doc/`) use a different language.
