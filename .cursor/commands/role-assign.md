---
description: >-
  Assign an AI model to an APM role (Planner, Coder, Reviewer) by updating the
  Active Role Assignments table in doc/apm_config/AGENT_MODELS.user.md. Ask if role/model
  is missing.
  Use when: user says "/role-assign", "přiřaď roli/model", "set Planner model", or similar.
---

# Command: role-assign

## What this command does

Records which model a given APM role should use, by updating the **Active Role Assignments**
table in `doc/apm_config/AGENT_MODELS.user.md` (the resolved AGENT_MODELS config — see the
Config Resolution mechanism in `rules/200-project-design-rules.mdc`). Roles are not bound to
fixed models — this command is how the Human assigns them.

## Steps for the agent

### Step 1 — Determine role(s) and model

Parse the Human's message for:
- **Role**: one or more of `Planner` | `Coder` | `Reviewer`.
- **Band**: one or more of `low` | `medium` | `high` (see `rules/000-model-policy.mdc`).
  Default to **all bands of the role** if the Human doesn't name one.
- **Model**: the model id/name to assign (verbatim, as the Human writes it).

If the role or the model is missing or ambiguous, **ASK** the Human — list the roles ×
bands and their current assignments, and let the Human name the model. Do **not** guess a
model or a band.

### Step 2 — Update the assignments table

If `doc/apm_config/AGENT_MODELS.user.md` does not exist yet, create it by copying
`.cursor/apm_config/AGENT_MODELS.default.md` first. Then, in its *Active Role Assignments*
table (rows = role, columns = band), set the cell(s) for each chosen role × band to the
model. Change only those cells. To clear an assignment, set the cell back to `unassigned`.
The Planner `low` / Reviewer `low` cells may legitimately read `—` (not applicable) —
leave `—` alone unless the Human explicitly asks to change it.

### Step 3 — Confirm

- Echo the new assignment(s).
- Remind: Cursor does **not** auto-switch models — the Human must pick the model in the
  model selector when acting in that role.

## Notes

- This edits a project config file (`doc/apm_config/AGENT_MODELS.user.md`), never
  anything under `.cursor/`; it is **not** a git commit. No git operations here.
- See `/role-show` to display current assignments.
