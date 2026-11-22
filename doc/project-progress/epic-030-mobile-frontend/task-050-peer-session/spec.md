---
apm_category: task-spec
apm_ref: E030.T050
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E030.T050 — PeerJS relace a tok snímků

## 1. Goal

Modul relace se připojí k peer id z hashe, pošle `hello`, přijme `welcome` jen při `v=1`,
posílá JPEG části a drží nejvýš jeden snímek na cestě. Cizí verze protokolu nastaví
srozumitelnou chybu a snímky dál neposílá.

## 2. Inputs

- DECISIONS #6, ADR-001, ADR-002
- Kodek z T030
- Spike `web/spike.js` jen jako popis PeerJS 1.5.4 (`connect`, `serialization: "raw"`,
  `binaryType = "arraybuffer"`). Echo protokol se nekopíruje.

## 3. Outputs

- `web/src/session/peerSession.ts` bez DOM kamery. Závislost na PeerJS jde injektovat.
- Pin `peerjs@1.5.4` v `package.json`.
- Po `open` poslat `hello`. `welcome` s `v !== 1` → stav `version-mismatch`.
- `sendFrame(jpeg)` nedělá nic, když už jeden snímek čeká na `result` nebo `error`.
  Po `result`/`error` smí další. Snímek větší než 16 384 B se dělí kodekem.
- Odchozí síť v testech se mockuje. Testy nevolají `0.peerjs.com`.

## 4. Context Bundle

- **Read:** T030, DECISIONS #6.
- **Do not modify:** Python, `experiments/`.
- **Interfaces from prior tasks:** `frameCodec`, generované typy.

## 5. Dependencies

T030.

## 6. Test Specification

- Happy path: fake PeerJS přijme `hello` a po `sendFrame` malého JPEGu jednu binární zprávu.
- Edge: druhé `sendFrame` před `result` nic nepošle; po `result` pošle.
- Error: `welcome` s `v: 2` zastaví posílání.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high`. AGENT_MODELS: `grok-4.7-high`.
