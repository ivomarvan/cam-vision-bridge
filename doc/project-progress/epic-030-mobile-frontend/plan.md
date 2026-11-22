---
apm_category: epic-plan
apm_ref: E030
apm_level: epic
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Epic Plan: E030 — Mobilní frontend a GitHub Pages

## Epic Goal

Stránka ve `web/` mluví protokolem v1 s `PhoneCamera`, kreslí výsledky přes živé video
a jde sestavit v Dockeru. Nasazení na GitHub Pages je workflow pod cestou
`/cam-vision-bridge/v1/`.

Human schválil E020 (DECISIONS #10) a požádal pokračovat.

## Task List

| Task | Name | Depends on | Coder model | Band |
|------|------|-----------|-------------|------|
| T010 | Kostra Vue v Dockeru | — | Coder role | medium |
| T020 | Typy z JSON Schema | T010 | Coder role | high |
| T030 | Binární kodek ve stránce | T020 | Coder role | high |
| T040 | Přepočet souřadnic | T010 | Coder role | medium |
| T050 | PeerJS relace a tok snímků | T030 | Coder role | high |
| T060 | Kamera a překryvy | T040, T050 | Coder role | high |
| T070 | Obrazovka, Wake Lock, fullscreen | T060 | Coder role | medium |
| T080 | GitHub Actions Pages | T010 | Coder role | high |

T040 může běžet po T010 vedle T020. T080 až po zeleném buildu z T010; nasazení se
nepouští z agenta, jen se zapíše workflow.

**Modely:** Coder `medium` = `composer-2.5`, Coder `high` = `grok-4.7-high`.
Reviewer `medium` fallback `gpt-5.6-sol-medium`. Reviewer `high` = `gpt-5.6-sol-medium`.

## Společné konvence E030

- Adresář je `web/`, ne `frontend/`. Pravidlo `110-vuejs-vite-tailwind.mdc` platí pro
  kód uvnitř `web/src`. Vue Router se nepoužije (spec § 4.4, jedna obrazovka, hash).
- Veřejná cesta buildu: `/cam-vision-bridge/v1/`. Hash `#peer=<id>` se na Pages neposílá.
- PeerJS **1.5.4**, `serialization: "raw"`, `reliable: true`. Pole `browser` v OFFER
  stránka nečeká (DECISIONS #6).
- Typy zpráv jen ze `schema/cam-vision-bridge-v1.schema.json` (ADR-002). Ruční opis
  polí je zakázaný.
- Binární snímek je stejný jako v Python kodeku: uint32 délka hlavičky, JSON
  `FrameHeader`, JPEG části. `in_flight` výchozí 1. Nad 64 KB se snímek dělí po 16 384 B.
- Node toolchain jen v Dockeru, image `node:22.12.0-alpine` s digestem zapsaným v
  `README.docker.md`. Brána: `vue-tsc --noEmit`, `eslint .`, `vitest run`.
- Python knihovna a `experiments/` se nemění.

## Task Specifications

- [T010](task-010-vue-docker-skeleton/spec.md)
- [T020](task-020-schema-types/spec.md)
- [T030](task-030-frame-codec/spec.md)
- [T040](task-040-coordinate-map/spec.md)
- [T050](task-050-peer-session/spec.md)
- [T060](task-060-camera-overlays/spec.md)
- [T070](task-070-screen-shell/spec.md)
- [T080](task-080-github-pages/spec.md)
