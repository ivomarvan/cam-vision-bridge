---
apm_category: roadmap
apm_ref: PROJECT
apm_level: project
created_by: Planner
model: claude-opus-5-5-high
template_version: v1.2.0-1-gbb135f1
intended_for: All
created_at: 2026-11-21
updated_at: 2026-11-22
---

# Roadmap: CAM-VISION-BRIDGE

Pořadí epik je „riziko první“: nejistá část (WebRTC mezi aiortc a prohlížečem v mobilu přes
PeerJS cloud) se ověří dřív, než na ní postavíme produkční kód.

## Epic E010 — Spike: WebRTC aiortc ↔ mobil přes PeerJS

**Typ:** spike (`070-project-management.mdc`), větev `spike/webrtc-peerjs-aiortc`, kód
v `experiments/2026-11-webrtc-peerjs-aiortc/`.

**Otázka:** Naváže Python (`aiortc` + minimální PeerJS klient) DataChannel s Chrome na
Androidu ve tvé síti přes veřejný PeerJS cloud a zvládne přenášet JPEG snímky 640×480
dostatečně rychle?

- Minimální Python peer: registrace u PeerJS cloudu, odpověď na OFFER, ICE kandidáti,
  heartbeat, DataChannel s `serialization: "raw"`.
- Minimální stránka: syntetické snímky z canvasu (pohyblivý vzor), takže kamera ani HTTPS
  pro měření nejsou potřeba; volitelně kamera přes
  `chrome://flags/#unsafely-treat-insecure-origin-as-secure`.
- Echo protokol: snímek s `frame_id` → Python vrátí `frame_id` + čas → stránka měří.
- **Metriky:** úspěch spojení (Chrome Android, Chrome desktop, volitelně Safari iOS), čas
  navázání, FPS, medián/p95 round-trip latence pro JPEG kvality 0.6/0.8, chování
  zpráv > 64 KB, vytížení CPU na PC, typy ICE kandidátů (host/mDNS/srflx).
- **Výstup:** tabulka výsledků + `README.md` + ADR-001 (potvrzení transportu, nebo
  fallback — např. WebSocket + certifikát).

Odhad složitosti: střední. Pásmo Planneru: `medium`.

**Stav 2026-11-22:** uzavřeno. ADR-001 transport potvrzuje. FER.2 nechal E020–E040 beze změny.

## Epic E020 — Python jádro: protokol, FrameHub, PhoneCamera

- Kostra balíčku: `pyproject.toml` (src-layout), Ruff, mypy `--strict`, pytest, `.gitignore`.
- Protokol v1 jako Pydantic modely (zprávy + všechny typy výsledků) a generování JSON Schema
  do `schema/`.
- Binární kodek snímku: hlavička, dělení na části, skládání, limity velikosti (nedůvěryhodný
  vstup).
- `Frame` a `FrameHub` (nejnovější snímek, řízení toku) + `FakeTransport`.
- `PhoneCamera` (synchronní fasáda nad asyncio) + `run(callback)` + QR kód s URL v terminálu.
- Produkční `PeerJsWebRtcTransport` (převzetí ověřeného přístupu ze spiku, s testy).
- Integrační test aiortc ↔ aiortc s lokální signalizací.

Odhad složitosti: vysoká. Pásmo Planneru: `high` (zpracování nedůvěryhodného vstupu,
kontrakt, na kterém závisí E030).

## Epic E030 — Mobilní frontend a nasazení na GitHub Pages

- Kostra `web/`: Vue 3 + Vite + TS + Tailwind + Pinia, ESLint, Vitest; Node toolchain
  v Dockeru (DECISIONS #4) + `README.docker.md`.
- TypeScript typy generované z `schema/`.
- Spojení: PeerJS klient, kodek snímků, řízení toku, handshake `hello`/`welcome` s verzí.
- Kamera: výběr přední/zadní, zmenšení, JPEG, cílové FPS.
- Vykreslení překryvů: všechny typy v1, přepočet souřadnic (zrcadlení, letterbox).
- UI: stavy spojení, nastavení, panel textů a metrik, FPS/latence, Wake Lock, fullscreen.
- GitHub Actions: build a nasazení na GitHub Pages pod `/v1/`.

Odhad složitosti: vysoká. Pásmo Planneru: `high` (CI/deploy konfigurace).

## Epic E040 — Ukázka qrdet, dokumentace, ověření DoD projektu

- `examples/qrdet_demo/` s vlastními závislostmi (qrdet + QReader; torch mimo knihovnu).
- Anglické `README.md` (instalace, spárování, API, typy výsledků, omezení).
- Ruční end-to-end ověření DoD projektu (spec § 6) včetně měření FPS a latence.

Odhad složitosti: nízká až střední. Pásmo Planneru: `medium`.

## Kandidáti na později (neplánováno)

Asynchronní veřejné API · WebSocket transport · zdroj z video souboru / webkamery ·
nahrávání snímků jako dataset · režim zmrazeného snímku · WebRTC video track · vlastní
PeerJS server / TURN · zobrazení výsledků i v prohlížeči na PC.
