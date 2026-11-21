---
apm_category: task-spec
apm_ref: E010.T020
apm_level: task
created_by: Planner
model: claude-opus-5-5-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-21
updated_at: 2026-11-21
---

# Task Specification: E010.T020 — Měřicí stránka (prohlížeč)

## 1. Goal

Vytvořit statickou měřicí stránku (bez build kroku), která se přes PeerJS připojí
k `run_peer.py` z T010, posílá JPEG snímky 640×480 podle konvencí v `plan.md`, měří
round-trip latenci a FPS a jedním tlačítkem projede matici měření. Hotovo je, když
krátká matice (`duration=5`) proběhne v Chrome na desktopu proti `run_peer.py` a v
`results/` vzniknou `runs.csv` a `frames/*.csv` se všemi 9 běhy (8 + sonda; sonda smí
selhat, výsledek musí být viditelný na stránce).

## 2. Inputs

- `plan.md` § Společné konvence spiku (binární formát, JSON zprávy, matice) — závazné.
- Rozhraní z T010: `run_peer.py` (vypíše URL `<page-url>#peer=<id>`), zprávy `echo` /
  `error`, zápis CSV.
- **PeerJS v prohlížeči:** ES modul z pinned CDN (`https://esm.sh/peerjs@<přesná 1.5.x
  verze>`), stejně jako v projektu Astriot. Připojení:
  `peer.connect(pythonId, { reliable: true, serialization: "raw" })`; po `open` nastavit
  `conn.dataChannel.binaryType = "arraybuffer"`. Zprávy z Pythonu jsou textové (JSON).
  Ověřeno 2026-11-21 proti PeerJS 1.5.4 (DECISIONS #6): `OFFER` neobsahuje `browser`.
  To je schválený kontrakt, ne důvod k `BLOCKED`.
- **ICE info:** `conn.peerConnection.getStats()` → vybraný `candidate-pair` (přes
  `transport.selectedCandidatePairId`, fallback `nominated && state === "succeeded"`) →
  `candidateType` lokálního a vzdáleného kandidáta a `protocol`.

## 3. Outputs

V `experiments/2026-11-webrtc-peerjs-aiortc/web/`:

- `frame_codec.js` — čisté funkce (bez DOM): `packChunk(header, payload: Uint8Array):
  Uint8Array`, `splitFrame({runId, frameId, jpeg: Uint8Array, chunkBytes}): Uint8Array[]`
  (`chunkBytes = 0` → jedna zpráva), `parseServerMessage(text): object` (validuje `t`).
  Hlavička = `JSON.stringify` objektu s klíči v pořadí `t, run_id, frame_id, part, parts,
  total_bytes`.
- `spike.js` — ES modul:
  - parametry z `location.hash`: `peer` (povinný), volitelně `host`, `port`, `path`, `key`
    (výchozí PeerJS cloud), `duration` (s; výchozí 20);
  - `connect_ms` = čas od volání `peer.connect` do `open` DataConnection;
  - **syntetické snímky:** canvas 640×480 — posouvající se gradient, ~20 pohyblivých
    barevných obdélníků, text s `frame_id` a časem, šumová oblast 160×120 (realistická
    velikost JPEG);
  - **režim kamera:** povolen jen při `window.isSecureContext &&
    navigator.mediaDevices?.getUserMedia` (jinak disabled s vysvětlením); snímek z videa
    do stejného canvasu 640×480;
  - JPEG přes `canvas.toBlob(…, "image/jpeg", quality)`;
  - **řízení toku:** nový snímek jen pokud je „na cestě“ méně než `in_flight` snímků
    a od posledního odeslání uplynulo ≥ 1000/30 ms; snímek bez `echo` do 2 s = ztracený;
  - po `echo`: `rtt_ms` → poslat zprávu `rtt`; po každém běhu počkat max. 2 s na zbylá
    `echo` a poslat `run_end`;
  - `run_id` = `r<YYYYMMDDTHHMMSS>-<NN>` (index běhu, jen `[A-Za-z0-9_-]`);
  - tlačítko **Run matrix** (8 běhů + sonda dle `plan.md`) a **Single run**
    (formulář: mode, quality, in_flight, chunk_bytes);
  - sonda bez dělení: chybu `send` nebo zavření spojení zachytit, zobrazit a pokračovat
    v UI (bez pádu stránky);
  - UI: stav signalizace / spojení / ICE typy, živě FPS, klouzavý medián RTT, odesláno /
    vráceno; **tabulka souhrnu po bězích** na stránce (pro screenshot z telefonu); log chyb.
- `index.html` — mobilní viewport, jednoduché čitelné UI (bez frameworku, bez build
  kroku), načte `spike.js` jako `type="module"`.
- `tests/frame_codec.test.js` — `node:test` + `node:assert`, spouštěné v Dockeru s pinned
  image: `docker run --rm -v "$PWD/web":/w -w /w node:<přesná verze>-alpine node --test tests/`.
- `results/` — CSV z baseline běhu v Chrome na desktopu (commitovatelné výstupy spiku).
- `README.md` experimentu — doplnit sekci *Measurement page*: spuštění statického serveru
  (`python3 -m http.server 8080 --directory web`), otevření na telefonu (stejná Wi-Fi,
  QR kód z `run_peer.py`), volitelná kamera přes
  `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, poznámka k firewallu
  (příchozí UDP pro ICE, např. `ufw`), parametr `duration`.

## 4. Context Bundle

- **Read:** `plan.md`, T010 `spec.md`, T010 `report.md`, kód v
  `experiments/2026-11-webrtc-peerjs-aiortc/py/` (jen ke čtení),
  `.cursor/rules/220-javascript.mdc`, `.cursor/rules/210-html.mdc`,
  `.cursor/rules/080-agent-security.mdc`.
- **Do not modify:** `experiments/.../py/**` (chyba v T010 → `BLOCKED` Plannerovi);
  `doc/` kromě vlastního `report.md` / `dod.md`; `.cursor/`; `.gitignore`.
- **Interfaces from prior tasks:** T010 — `run_peer.py` CLI, binární formát a JSON zprávy
  (dle `plan.md`), zápis CSV.
- **Síť:** odchozí jen na PeerJS cloud, STUN a CDN s PeerJS.

## 5. Dependencies

T010 (hotový a schválený).

## 6. Test Specification

- **Node unit testy (`frame_codec.test.js`):**
  - happy path: `packChunk` — první 4 B = délka hlavičky big-endian, následuje JSON
    s klíči v předepsaném pořadí, pak payload beze změny;
  - `splitFrame` 100 000 B s `chunkBytes = 16384` → 7 zpráv, `part` 0..6, shodné `parts`
    a `total_bytes`, součet payloadů = 100 000;
  - edge: `chunkBytes = 0` → 1 zpráva s `parts = 1`; JPEG přesně násobek `chunkBytes`
    → bez prázdné poslední části;
  - error: `parseServerMessage` s nevalidním JSON nebo neznámým `t` → výjimka.
- **End-to-end (ručně, Chrome desktop):** `run_peer.py` + statický server + stránka
  s `#peer=<id>&duration=5` → Run matrix → 9 běhů v tabulce stránky; `runs.csv` má
  řádky pro všechny běhy, které doběhly; screenshot stránky a výřez CSV v `report.md`.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `medium` — model podle `000-model-policy.mdc` (AGENT_MODELS: `composer-2.5`).
