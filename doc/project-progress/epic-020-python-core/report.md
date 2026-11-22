---
apm_category: epic-report
apm_ref: E020
apm_level: epic
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human, Planner
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Epic Report: E020 — Python jádro

## Shrnutí epiky

Knihovna `cam_vision_bridge` je instalovatelná z `src/`. Má protokol v1 s generovaným
JSON Schema, binární kodek s limity před dekódováním, `FrameHub`, `FakeTransport`,
synchronní `PhoneCamera` a výchozí `PeerJsWebRtcTransport`. Integrační test spojí dva
`RTCPeerConnection` v procesu a na veřejný PeerJS cloud nesahá.

## Dokončené tasky

| Task | Název | Pásmo | Human brána po tasku | Kola revize | BLOCKED | Výsledek |
|------|-------|-------|----------------------|-------------|---------|---------|
| T010 | Kostra balíčku | medium | ne | 0 | 0 | ✅ |
| T020 | Protokol v1 a JSON Schema | high | přeskočena (DECISIONS #8) | 0 | 0 | ✅ |
| T030 | Binární kodek | high | přeskočena (DECISIONS #8) | 0 | 0 | ✅ |
| T040 | Frame, FrameHub, FakeTransport | medium | ne | 1 | 0 | ✅ |
| T050 | PhoneCamera | high | přeskočena (DECISIONS #8) | 0 | 0 | ✅ |
| T060 | PeerJsWebRtcTransport | high | přeskočena (DECISIONS #8) | 0 | 0 | ✅ |

## Klíčová rozhodnutí a poznatky

- Veřejné API je `PhoneCamera.frames` / `publish` / `run` (DECISIONS #1).
- `OFFER` bez pole `browser` je platný (DECISIONS #6).
- Druhé spojení se při živém prvním odmítne.
- `PhoneCamera()` bez argumentu použije WebRTC transport. Testy dál injektují `FakeTransport`.

## Odchylky od Epic Planu

- T040 kolo 1 chtělo test, že po neplatném chunku hub dál čeká a vydá pozdější snímek.
  Kolo 2 je APPROVE.
- Human brány u `high` tasků se nečekaly, protože DECISIONS #8 říká pokračovat.

## Doporučení pro Planner

- E030 má generovat TypeScript z `schema/cam-vision-bridge-v1.schema.json`, neopisovat modely.
- Wake Lock zůstává potřeba. Výchozí tok na telefonu je jeden snímek na cestě.
- Ruční zkouška s telefonem proti `PhoneCamera` není součástí téhle epiky. Patří do DoD
  projektu, až bude stránka na GitHub Pages.

## Využití tokenů (vyplní Human)

Planner: ~— · Coder: ~— · Reviewer: ~—

## Reference

- Epic Plan: [plan.md](plan.md)
- Task Reports: [T010](task-010-package-skeleton/report.md),
  [T020](task-020-protocol-schema/report.md),
  [T030](task-030-frame-codec/report.md),
  [T040](task-040-frame-hub/report.md),
  [T050](task-050-phone-camera/report.md),
  [T060](task-060-peerjs-transport/report.md)
