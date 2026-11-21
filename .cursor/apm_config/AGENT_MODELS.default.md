# Agent Models — Default Configuration

Default role → model assignments shipped with the template. A consuming project
overrides this file **in full** by creating `doc/apm_config/AGENT_MODELS.user.md` — see
the Config Resolution mechanism in `rules/200-project-design-rules.mdc`.

## Bands — project-specific hard triggers for `high`

Band definition, granularity, and escalation are a fixed mechanism in
`rules/000-model-policy.mdc`. List here only triggers **specific to this project** (the
generic ones in that rule always apply, in addition to these):

- *(none by default — add project risk areas here, e.g. "billing/payment code paths",
  "data-retention deletion logic")*

## Active Role Assignments

| Role | `low` | `medium` | `high` |
|---|---|---|---|
| Planner | — | `unassigned` | `unassigned` |
| Coder | `unassigned` | `unassigned` | `unassigned` |
| Reviewer | — | `unassigned` | `unassigned` |

`unassigned` means the agent **must ask** the Human before acting in that role. `—` means
the cell does not apply: Planner `low` never occurs (Planner is banded per Epic,
`rules/000-model-policy.mdc`; use `medium` if it ever does), and Reviewer `low` is covered
by the deterministic gate alone — assign a model there only if your `low` Tasks are not
fully gate-checkable. Edit via `/role-assign`, or by hand — see `rules/000-model-policy.mdc`
for the resolution rule.
