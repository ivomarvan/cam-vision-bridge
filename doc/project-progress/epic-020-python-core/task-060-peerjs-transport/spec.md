---
apm_category: task-spec
apm_ref: E020.T060
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E020.T060 — PeerJsWebRtcTransport

## 1. Goal

`PhoneCamera()` bez argumentu použije `PeerJsWebRtcTransport`. Integrační test spojí dva
`RTCPeerConnection` v jednom procesu (bez PeerJS cloudu) a protáhne jeden JPEG tam a
`Result` zpět. Veřejný cloud se v testech nevolá.

## 2. Inputs

- `plan.md`, DECISIONS #6 a #7, ADR-001
- Spike `experiments/2026-11-webrtc-peerjs-aiortc/py/peerjs_signaling.py` a `echo_peer.py`
  jen ke čtení. Produkční kód je nový a mluví protokolem v1, ne echo protokolem spiku.
- T050 `PhoneCamera`

## 3. Outputs

- `src/cam_vision_bridge/transport/peerjs.py` — `PeerJsWebRtcTransport`:
  - parametry host/port/path/key s výchozími hodnotami cloudu `0.peerjs.com:443`, key
    `peerjs`, path `/`;
  - registrace, heartbeat 5 s, `OPEN`, chyby `ID-TAKEN` / `INVALID-KEY` / `ERROR` jako
    `SignalingError`;
  - `OFFER` podle PeerJS 1.5.4 bez povinného pole `browser` (DECISIONS #6);
  - answerer, DataChannel od prohlížeče, ICE servery `stun:stun.l.google.com:19302`;
  - kandidáty prohlížeče přidat, prázdný kandidát ignorovat, kandidát před OFFER
    frontovat;
  - další OFFER odmítnout, dokud první spojení žije (spec § 4.5);
  - binární zprávy předat dál jako bajty, textové JSON taky jako bajty UTF-8, ať je
    smyčka `PhoneCamera` parsuje mimo transport. Transport sám JPEG neskládá.
- `PhoneCamera()` bez `transport` vytvoří tento transport. Pořád jde injektovat
  `FakeTransport`.
- `tests/transport/test_peerjs_local.py` marker `integration`: offerer v procesu vytvoří
  DataChannel, předá SDP a kandidáty přímo do answereru (bez WebSocketu), pošle jeden
  `pack_chunk` a přečte z answereru `Welcome` nebo přijme bajty, které smyčka pošle.
  Test nesmí otevřít socket na `0.peerjs.com`.

## 4. Context Bundle

- **Read:** spike signalizace, T050, DECISIONS #6.
- **Do not modify:** `experiments/`, limity kodeku, schéma.
- **Interfaces from prior tasks:** `Transport`, `PhoneCamera`, `pack_chunk`.

## 5. Dependencies

T050.

## 6. Test Specification

- Happy path: lokální offer/answer, jeden chunk dorazí na answerer jako bajty.
- Edge: `CANDIDATE` dřív než `OFFER` se neztratí (fronta) — ověřit jednotkově na čisté
  funkci nebo malém objektu, bez sítě.
- Error: `OFFER` bez `connectionId` vyhodí `SignalingError` a druhé spojení nevznikne.
  `ID-TAKEN` na falešném WebSocketu vyhodí `SignalingError`.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high` (síťový vstup z PeerJS a z telefonu). AGENT_MODELS: `grok-4.7-high`.
