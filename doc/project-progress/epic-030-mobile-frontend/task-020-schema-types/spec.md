---
apm_category: task-spec
apm_ref: E030.T020
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E030.T020 — Typy z JSON Schema

## 1. Goal

TypeScript typy protokolu v1 se generují ze `schema/cam-vision-bridge-v1.schema.json`.
Ruční úprava vygenerovaného souboru spadne v testu, který schéma vygeneruje znovu.

## 2. Inputs

- `schema/cam-vision-bridge-v1.schema.json`, ADR-002
- `plan.md` § Společné konvence E030

## 3. Outputs

- Generátor v `web/scripts/generate-protocol-types.mjs` (nebo npm balíček přidaný s
  odůvodněním), výstup `web/src/protocol/generated.ts`. Soubor má v hlavičce komentář,
  že se needituje.
- npm script `generate:protocol`.
- Test, který spustí generátor do dočasného souboru a porovná ho s commitnutým.
- Typy pokryjí `hello`, `welcome`, `error`, `frame`, `result` a položky výsledků.

## 4. Context Bundle

- **Read:** schéma, ADR-002, T010 `web/`.
- **Do not modify:** `schema/` (jen číst), Python, `experiments/`.
- **Interfaces from prior tasks:** kostra `web/`.

## 5. Dependencies

T010.

## 6. Test Specification

- Happy path: vygenerovaný soubor exportuje typ pro `result` a `box`.
- Edge: `text` má volitelné souřadnice.
- Error: přidaný řádek do `generated.ts` test shody selže (ověřit na kopii, commitnutý
  soubor nechat shodný).

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high` (kontrakt). AGENT_MODELS: `grok-4.7-high`.
