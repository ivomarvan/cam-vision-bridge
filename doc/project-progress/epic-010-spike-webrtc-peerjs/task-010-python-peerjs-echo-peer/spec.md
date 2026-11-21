---
apm_category: task-spec
apm_ref: E010.T010
apm_level: task
created_by: Planner
model: claude-opus-5-5-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-21
updated_at: 2026-11-21
---

# Task Specification: E010.T010 — Python PeerJS echo peer

## 1. Goal

Vytvořit Python CLI `run_peer.py`, které se zaregistruje u veřejného PeerJS cloudu pod
náhodným ID, přijme WebRTC DataChannel od prohlížeče (aiortc jako *answerer*), skládá
binární snímky z částí, dekóduje JPEG, odpovídá zprávami `echo` a zapisuje měření do CSV
podle konvencí v `plan.md`. Hotovo je, když projdou testy z § 6 a `run_peer.py` se
prokazatelně zaregistruje u PeerJS cloudu (log `OPEN`) a vypíše URL + QR kód.

## 2. Inputs

- `doc/project-progress/epic-010-spike-webrtc-peerjs/plan.md` — **§ Společné konvence spiku**
  (adresáře, binární formát, JSON zprávy, CSV, limity). Je to závazný kontrakt.
- `doc/project-progress/spec.md` § 4.1–4.2, 4.5 (kontext; spike nemusí implementovat vše).
- **Fakta o PeerJS server protokolu** (ověřeno Plannerem v kódu `peerjs.min.js`; Coder je
  ověří proti aktuální verzi PeerJS 1.5.x, kterou použije T020):
  - WebSocket URL: `wss://0.peerjs.com:443/peerjs?key=peerjs&id=<id>&token=<token>&version=<ver>`
    (obecně `wss://{host}:{port}{path}peerjs?key={key}&id=…&token=…`; výchozí `path` = `/`,
    `key` = `peerjs`). `token` = náhodný řetězec; `version` = verze PeerJS klienta, kterou
    emulujeme (např. `1.5.4`).
  - Server → klient: `{"type": "OPEN"}` po úspěšné registraci; chyby `ID-TAKEN`,
    `INVALID-KEY`, `ERROR`; dále `OFFER`, `ANSWER`, `CANDIDATE`, `LEAVE`, `EXPIRE`.
  - Klient → server: `{"type": "HEARTBEAT"}` každých 5 s.
  - Zpráva mezi peery: `{"type": T, "src": <odesílatel>, "dst": <příjemce>, "payload": {...}}`
    (při odesílání klient vyplňuje `dst`, server doplní `src`).
  - `OFFER.payload` (PeerJS 1.5.4, DECISIONS #6): `{sdp: {type: "offer", sdp: str},
    type: "data", connectionId: str, label: str, reliable: bool, serialization: str,
    metadata: any}`. Pole `browser` tato verze neposílá; Python ho nesmí vyžadovat.
  - `ANSWER.payload` (posílá Python): `{sdp: {type: "answer", sdp: str}, type: "data",
    connectionId: <z OFFER>, browser: "aiortc"}`, `dst` = `src` z OFFER.
  - `CANDIDATE.payload`: `{candidate: {candidate: str, sdpMid: str, sdpMLineIndex: int,
    usernameFragment?: str}, type: "data", connectionId: str}`.
  - DataChannel vytváří *originator* (prohlížeč) s `label` z OFFER; Python ho dostane
    v `RTCPeerConnection.on("datachannel")`.
  - Výchozí ICE servery PeerJS: `stun:stun.l.google.com:19302` a TURN
    `turn:0.peerjs.com:3478` (`peerjs` / `peerjsp`) — TURN je jen záložní kandidát; jeho
    funkčnost se neověřuje.
- **Fakta o aiortc:** aiortc netrickluje — kandidáty sesbírá během `setLocalDescription()`
  a vloží je do SDP odpovědi, Python tedy neposílá `CANDIDATE`. Kandidáty prohlížeče
  přidá přes `aiortc.sdp.candidate_from_sdp(<řetězec bez prefixu "candidate:">)`
  s doplněným `sdpMid` / `sdpMLineIndex` a `await pc.addIceCandidate(...)`; prázdný
  kandidát (end-of-candidates) ignorovat. `CANDIDATE` může dorazit dřív, než je zpracován
  `OFFER` — frontovat podle `connectionId`.

## 3. Outputs

V `experiments/2026-11-webrtc-peerjs-aiortc/`:

- `py/requirements.txt` — pinned verze (ověřené na PyPI v době implementace), každá
  s komentářem-zdůvodněním: `aiortc`, `websockets`, `opencv-python-headless`, `numpy`,
  `qrcode` (QR kód URL v terminálu), `pytest`, `ruff`.
- `py/pytest.ini` — `pythonpath = .`, markery `unit`, `integration`.
- `py/frame_codec.py` — `pack_chunk(header: ChunkHeader, payload: bytes) -> bytes`,
  `unpack_chunk(data: bytes) -> tuple[ChunkHeader, bytes]`, třída `FrameAssembler`
  (přidává části, vrací kompletní JPEG, vynucuje limity z `plan.md`, zahazuje nekompletní
  snímky starší než 2 s; čas injektovaný pro testy). Chyby limitů =
  vlastní výjimka `FrameProtocolError`.
- `py/peerjs_signaling.py` — `PeerJsSignaling` (async): `connect()` (čeká na `OPEN`,
  při `ID-TAKEN`/`INVALID-KEY`/`ERROR` vyhodí `SignalingError`), heartbeat task,
  `send(msg)`, asynchronní iterace přijatých zpráv; čisté funkce pro sestavení URL
  a zpráv `ANSWER`, a pro převod `CANDIDATE` payloadu na `RTCIceCandidate`.
- `py/echo_peer.py` — `EchoPeer`: pro každý `OFFER` vytvoří `RTCPeerConnection` (ICE servery
  jako PeerJS výchozí), odpoví `ANSWER`, aplikuje frontované kandidáty, na DataChannelu
  zpracuje binární části (`FrameAssembler` → `cv2.imdecode` → měří `decode_ms` → `echo`)
  a textové zprávy `run_start` / `rtt` / `run_end` (→ `ResultsWriter`). Neplatný vstup =
  `WARNING` log + zpráva `error`, spojení běží dál. Loguje změny `connectionState`
  a `iceConnectionState`. Více současných spojení není potřeba podporovat (další OFFER
  může nahradit předchozí spojení).
- `py/results_writer.py` — `ResultsWriter(results_dir: Path)`: zapisuje `runs.csv`
  (hlavička jen jednou, append) a `frames/<run_id>.csv` přesně podle schémat v `plan.md`;
  `run_id` validovat (`[A-Za-z0-9_-]{1,64}`), aby nešlo zapisovat mimo adresář.
- `py/run_peer.py` — CLI (`argparse`): `--host` (výchozí `0.peerjs.com`), `--port` (443),
  `--key` (`peerjs`), `--page-url` (výchozí `http://<LAN-IP>:8080/`), `--results-dir`
  (výchozí `../results`), `--log-level`. Vygeneruje ID `cvb-<16 hex>`, připojí se, vypíše
  URL `<page-url>#peer=<id>` a QR kód (`qrcode`, ASCII) do terminálu, běží do Ctrl+C
  a ukončí se čistě. LAN IP zjistit bez odesílání dat (UDP socket `connect` trik).
- `py/tests/` — testy podle § 6.
- `README.md` experimentu — sekce *Goal*, *Setup (Python)*, *Run the peer*; sekce pro
  stránku a výsledky doplní T020/T030 (ponechat nadpisy *Measurement page*, *Results*,
  *Outcome* s textem „to be filled“).

## 4. Context Bundle

- **Read:** `plan.md` (celý), `doc/project-progress/spec.md`, `DECISIONS.md`,
  `doc/apm_config/DESIGN_RULES.user.md`, `.cursor/rules/100-python.mdc`,
  `.cursor/rules/010-general-programming.mdc`, `.cursor/rules/080-agent-security.mdc`.
- **Do not modify:** cokoliv v `doc/` kromě vlastního `report.md` a `dod.md` tohoto tasku;
  `.cursor/`; `.gitignore`; soubory mimo `experiments/2026-11-webrtc-peerjs-aiortc/py/`
  a `README.md` experimentu.
- **Interfaces from prior tasks:** žádné.
- **Síť:** jediné povolené odchozí spojení je na PeerJS cloud (`0.peerjs.com`) a STUN —
  pro ruční ověření registrace. Neposílat žádná data z repozitáře ani prostředí.

## 5. Dependencies

Žádné.

## 6. Test Specification

Spuštění: `cd experiments/2026-11-webrtc-peerjs-aiortc/py && .venv/bin/pytest`.

- **Unit (`-m unit`), bez sítě:**
  - `frame_codec`: pack → unpack zachová hlavičku i payload (happy path); složení snímku
    ze 3 částí v pořadí i mimo pořadí; `parts = 1` (bez dělení).
  - Edge: nekompletní snímek starší než 2 s je zahozen (injektovaný čas); duplicitní část
    nezmění výsledek.
  - Error: `header_len > 4096`, `parts = 0`, `parts > 256`, `part ≥ parts`,
    `total_bytes > 8 MiB`, nesoulad `parts`/`total_bytes` mezi částmi, součet payloadů
    ≠ `total_bytes`, nevalidní JSON hlavičky, zpráva kratší než 4 B → `FrameProtocolError`.
  - `peerjs_signaling`: sestavení URL (výchozí i vlastní host/port/path/key); sestavení
    `ANSWER` z OFFER; převod `CANDIDATE` payloadu na `RTCIceCandidate` (UDP host
    kandidát, srflx kandidát, prázdný kandidát → `None`); `ID-TAKEN` → `SignalingError`
    (s fake WebSocketem).
  - `results_writer`: dva běhy → `runs.csv` má hlavičku jednou a 2 řádky; frames CSV má
    správné sloupce; nevalidní `run_id` (`../x`) → `ValueError`.
- **Integration (`-m integration`), bez externí sítě:** in-process dvojice
  `RTCPeerConnection` (offerer simuluje prohlížeč: vytvoří DataChannel, signalizace
  předávaná přímo v paměti místo PeerJS) ↔ `EchoPeer` logika: odeslat `run_start`,
  snímek 640×480 JPEG rozdělený na části po 16 384 B, přijmout `echo` se správným
  `frame_id`, `bytes`, `parts`; odeslat `rtt` a `run_end` → v dočasném adresáři vzniknou
  CSV s očekávaným obsahem. Neplatná binární zpráva → `error` a spojení zůstane `open`.
- `ruff check .` a `ruff format --check .` bez chyb.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high` (externí síťový vstup) — model podle `000-model-policy.mdc`
(AGENT_MODELS: `grok-4.7-high`).
