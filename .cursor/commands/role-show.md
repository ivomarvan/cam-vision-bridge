---
description: >-
  Show the current APM role → model assignments from the resolved AGENT_MODELS config
  (doc/apm_config/AGENT_MODELS.user.md or .cursor/apm_config/AGENT_MODELS.default.md).
  Use when: user says "/role-show", "jaké role/modely", "which model for which role", or
  similar.
---

# Command: role-show

## What this command does

Displays which model each APM role (Planner, Coder, Reviewer) is currently assigned to.

## Steps for the agent

### Step 1 — Read assignments

Read the resolved *Active Role Assignments* table: `doc/apm_config/AGENT_MODELS.user.md`
if it exists, otherwise `.cursor/apm_config/AGENT_MODELS.default.md` (see the Config
Resolution mechanism in `rules/200-project-design-rules.mdc`).

### Step 2 — Present

Show the role × band table (`low`/`medium`/`high`, see `rules/000-model-policy.mdc`). For
any cell marked `unassigned`, note that the agent will **ask** the Human before acting in
that role/band (and that `/role-assign` can set it). A `—` cell (Planner `low`, Reviewer
`low`) means "not applicable" — never occurs / gate only — not "unassigned".

### Step 3 — Reminder

Note the Cursor limitation: the parent window's model is not auto-switched per role — the
Human selects it in the model selector; subagents get the model via the call's `model`
parameter (`rules/000-model-policy.mdc`, Resolution rule step 2).
