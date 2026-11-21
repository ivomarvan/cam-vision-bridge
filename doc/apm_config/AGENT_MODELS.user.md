# Agent Models — CAM-VISION-BRIDGE

Project override of `.cursor/apm_config/AGENT_MODELS.default.md` — see the Config
Resolution mechanism in `rules/200-project-design-rules.mdc`.

## Bands — project-specific hard triggers for `high`

In addition to the generic triggers in `rules/000-model-policy.mdc`:

- Wire protocol changes: binary frame format, message schemas, protocol version
  (`plan.md` spike conventions, later `cam_vision_bridge.protocol` and `schema/`) — the
  library and the GitHub Pages frontend are deployed separately.
- WebRTC / signaling code that parses messages from the PeerJS server or the phone.

## Active Role Assignments

| Role | `low` | `medium` | `high` |
|---|---|---|---|
| Planner | — | `grok-4.7-high` | `grok-4.7-high` |
| Coder | `composer-2.5` | `composer-2.5` | `grok-4.7-high` |
| Reviewer | — | `gemini-4-hydrogen-high` | `gpt-5.6-sol-medium` |

**Subagent fallback:** if a slug is not offered for subagents (currently
`gemini-4-hydrogen-high`), use the Reviewer `high` model `gpt-5.6-sol-medium` — never the
Coder's model — and record the substitution in `review.md`.

`unassigned` means the agent **must ask** the Human before acting in that role. `—` means
the cell does not apply: Planner `low` never occurs (Planner is banded per Epic,
`rules/000-model-policy.mdc`; use `medium` if it ever does), and Reviewer `low` is covered
by the deterministic gate alone. Edit via `/role-assign`, or by hand.
