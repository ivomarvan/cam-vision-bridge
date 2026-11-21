---
apm_category: task-report
apm_ref: E010.T010
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-21
updated_at: 2026-11-21
---

# Task Report: E010.T010 — Python PeerJS echo peer

## Co bylo implementováno

- Python CLI `run_peer.py` se zaregistruje u veřejného PeerJS cloudu pod id `cvb-<16 hex>`, po `OPEN` vypíše URL stránky a ASCII QR a běží do Ctrl+C.
- Signalizace je minimální klient protokolu PeerJS 1.5.4 (`wss`, heartbeat po 5 s, `ANSWER` jako answerer). Kandidáty Python neposílá; aiortc je vloží do SDP.
- Binární chunky se skládají do JPEG, limity z `plan.md` se vynutí před `cv2.imdecode`. Průběžný součet payloadů nad `total_bytes` zahodí rozpracovaný snímek ještě před uložením části a před `join`. Neplatný vstup skončí jako `error` a DataChannel zůstane otevřený.
- `run_start` / `rtt` / `run_end` zapisují `runs.csv` a `frames/<run_id>.csv`. `run_id` nesmí opustit adresář `results/`.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/DECISIONS.md`
- `doc/apm_config/DESIGN_RULES.user.md`
- `doc/apm_config/LANGUAGE.user.md`
- `doc/project-progress/epic-010-spike-webrtc-peerjs/plan.md`
- `doc/project-progress/epic-010-spike-webrtc-peerjs/task-010-python-peerjs-echo-peer/spec.md`
- `doc/project-progress/epic-010-spike-webrtc-peerjs/task-010-python-peerjs-echo-peer/dod.md`
- `doc/project-progress/epic-010-spike-webrtc-peerjs/task-010-python-peerjs-echo-peer/review.md`
- `doc/project-progress/spec.md`
- `.cursor/rules/100-python.mdc`
- `.cursor/rules/010-general-programming.mdc`
- `.cursor/rules/070-project-management.mdc`
- `.cursor/rules/080-agent-security.mdc`
- `.cursor/TEMPLATE_VERSION`
- `.cursor/skills/execute-task/SKILL.md`
- `.cursor/skills/python-dev/SKILL.md`

### Vytvořeno

- `experiments/2026-11-webrtc-peerjs-aiortc/README.md`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/requirements.txt`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/pytest.ini`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/frame_codec.py`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/peerjs_signaling.py`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/echo_peer.py`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/results_writer.py`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/run_peer.py`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/tests/test_frame_codec.py`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/tests/test_peerjs_signaling.py`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/tests/test_results_writer.py`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/tests/test_echo_peer.py`

### Změněno

- `experiments/2026-11-webrtc-peerjs-aiortc/py/frame_codec.py`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/tests/test_frame_codec.py`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/tests/test_echo_peer.py`
- `doc/project-progress/epic-010-spike-webrtc-peerjs/task-010-python-peerjs-echo-peer/dod.md`

### Nedotčeno (Context Bundle)

- `doc/project-progress/epic-010-spike-webrtc-peerjs/plan.md`
- `doc/project-progress/epic-010-spike-webrtc-peerjs/task-010-python-peerjs-echo-peer/spec.md`
- `doc/project-progress/DECISIONS.md`
- `doc/project-progress/spec.md`
- `doc/project-progress/roadmap.md`
- `doc/architecture/`
- `src/`
- `web/`
- `.cursor/`
- `.gitignore`

## Použité metody a rozhodnutí

### Registrace u PeerJS

Klient emuluje verzi `1.5.4` (příklad ve spec §2). URL je `wss://{host}:{port}{path}peerjs?key&id&token&version`. Po `OPEN` běží čtení zpráv a `{"type":"HEARTBEAT"}` každých 5 s. Token je jen v URL, do logu se nedostane. WebSocket jde přímo na hostitele (`proxy=None`, bez komprese), aby registrace nešla přes cizí proxy.

Živý cloud `wss://0.peerjs.com` tuto registraci přijal (výpis níže). Tvary `OFFER` / `ANSWER` / `CANDIDATE` jsou převzaté ze spec §2; JS balíček PeerJS jsem nestahoval, odchozí síť tasku je PeerJS cloud, STUN a PyPI. Odpor proti těm tvarům se neukázal. TURN `turn:0.peerjs.com:3478` je jen záložní ICE server ze spec, jeho relay se nezkouší.

### Složení snímku a nedůvěryhodný vstup

Hlavička je délka `uint32` BE, UTF-8 JSON a payload. Limity (`header_len`, `parts`, `part`, `total_bytes`, shoda částí, součet payloadů, stáří 2 s) padají jako `FrameProtocolError` dřív, než se zavolá `cv2.imdecode`. Sonda bez dělení (`parts = 1`, velká jedna zpráva) se v Pythonu nedělí; když ji DataChannel zahodí, není to chyba kódu.

Review kolo 1, nález #1: součet se nekontroluje až po složení všech částí. Nová neduplicitní část se uloží jen když `dosavadní součet + len(payload) ≤ total_bytes`. Jinak se rozpracovaný snímek smaže a vyhodí se `FrameProtocolError` (`payload_size`) bez `b"".join`. Nedostatečný součet po poslední části se odmítne stejně, také před spojením. Duplicitní `part` se dál ignoruje a do součtu se nepočítá znovu.

Neúplný snímek starší než 2 s se zahodí při dalším chunku a peer pošle `error` s `reason=incomplete_timeout`. Samostatné časovačové vlákno není: bez další zprávy není komu odpovědět, a telefon stejně po 2 s snímek považuje za ztracený.

### Jedno spojení a testy bez sítě

Nový `OFFER` zavře předchozí `RTCPeerConnection`. `CANDIDATE` před `OFFER` se frontuje podle `connectionId`; prázdný kandidát se ignoruje. aiortc kandidáty do SDP vloží sám, proto Python `CANDIDATE` neposílá.

Integrační test spojí dva `RTCPeerConnection` v jednom procesu s prázdným seznamem ICE serverů, aby se nevolal STUN. CLI dál používá výchozí servery ze spec.

### CSV

Řádek `runs.csv` vznikne při `run_end`, `started_at` je UTC čas `run_start`. Řádek `frames/<run_id>.csv` vznikne při `rtt` z hodnot zapamatovaných u `echo`. `run_id` musí sedět na `[A-Za-z0-9_-]{1,64}` a po `resolve()` zůstat v `frames/`.

### Závislosti a ADR

Verze na PyPI k 2026-11-21, všechny `==`, zdůvodnění v `requirements.txt`: `aiortc==1.16.0`, `websockets==17.4`, `opencv-python-headless==5.1.0.95`, `numpy==2.5.5`, `qrcode==8.2`, `pytest==9.2.0`, `ruff==0.17.6`. Venv je `experiments/2026-11-webrtc-peerjs-aiortc/py/.venv` (gitignored). Žádné ADR: transport se nemění, ADR-001 zůstává na závěr spiku po měření.

## Odchylky od spec.md

Oprava nálezu #1 kontrakt nemění: limit součtu payloadů je v `plan.md`, jen se vynucuje dřív. Dvě odchylky z první implementace zůstávají.

- **Testovací švy.** `PeerJsSignaling` má volitelný `connector` a `heartbeat_interval`, `EchoPeer` volitelný `ice_servers`, `now` a `monotonic`. Výchozí hodnoty jsou cloud, ICE servery ze spec §2 a reálné hodiny. Dopad na CLI: žádný. Integrační test díky tomu nevolá STUN.
- **`run_id` už v chunku.** `unpack_chunk` odmítne identifikátor mimo `[A-Za-z0-9_-]{1,64}` jako `FrameProtocolError`, nejen zápis CSV. Důvod: hlavička z telefonu se nesmí dostat k cestě ani k dekodéru. T020 stejnou abecedu generuje. Dopad: jiný `run_id` skončí jako `error`, spojení zůstane.

## Reference do kódu

| File | Lines | Summary |
|---|---|---|
| `experiments/2026-11-webrtc-peerjs-aiortc/py/frame_codec.py` | 33-142 | `FrameProtocolError`, `ChunkHeader`, `pack_chunk`, `unpack_chunk`, `ensure_run_id` |
| `experiments/2026-11-webrtc-peerjs-aiortc/py/frame_codec.py` | 159-212 | `FrameAssembler.add`: průběžný součet před uložením a před `join` |
| `experiments/2026-11-webrtc-peerjs-aiortc/py/peerjs_signaling.py` | 49-170 | `peerjs_ice_servers`, `build_peerjs_ws_url`, `build_answer_message`, `ice_candidate_from_payload` |
| `experiments/2026-11-webrtc-peerjs-aiortc/py/peerjs_signaling.py` | 181-393 | `PeerJsSignaling.connect` (`OPEN` / `ID-TAKEN`), heartbeat, iterace zpráv |
| `experiments/2026-11-webrtc-peerjs-aiortc/py/echo_peer.py` | 117-345 | `EchoPeer`: offer, answer, fronta kandidátů, stavy ICE |
| `experiments/2026-11-webrtc-peerjs-aiortc/py/echo_peer.py` | 347-430 | binární chunky a `cv2.imdecode` až po limitech |
| `experiments/2026-11-webrtc-peerjs-aiortc/py/results_writer.py` | 39-168 | `ResultsWriter.append_run`, `append_frame`, kontrola `run_id` |
| `experiments/2026-11-webrtc-peerjs-aiortc/py/run_peer.py` | 34-139 | CLI, LAN IP bez odeslání paketu, URL a QR |
| `experiments/2026-11-webrtc-peerjs-aiortc/py/tests/test_frame_codec.py` | 125-132 | unit: průběžný součet nad `total_bytes` zahodí snímek |
| `experiments/2026-11-webrtc-peerjs-aiortc/py/tests/test_peerjs_signaling.py` | 1-199 | unit: URL, ANSWER, ICE, `ID-TAKEN`, heartbeat |
| `experiments/2026-11-webrtc-peerjs-aiortc/py/tests/test_results_writer.py` | 1-64 | unit: hlavička jednou, sloupce, `../x` |
| `experiments/2026-11-webrtc-peerjs-aiortc/py/tests/test_echo_peer.py` | 46-47, 124-137 | integrace: přesah součtu pošle `error`, kanál zůstane `open` |

## Výsledek regresního testu

Po opravě nálezu #1 (review kolo 1, verdikt pořád REQUEST CHANGES, ne APPROVE) znovu spuštěno z `experiments/2026-11-webrtc-peerjs-aiortc/py`. Jiná testovací sada v repozitáři není.

| Command / scope | Result | Notes |
|---|---|---|
| `.venv/bin/ruff check .` | exit 0 | `All checks passed!` |
| `.venv/bin/ruff format --check .` | exit 0 | 9 souborů beze změny |
| `.venv/bin/pytest -v --tb=short` | exit 0, 32 passed | 0,89 s; včetně průběžného přesahu (unit i integrace) |

Ruční registrace se v tomto kole neopakovala. Výpis z prvního běhu, proces potom ukončen:

```text
cd experiments/2026-11-webrtc-peerjs-aiortc/py
.venv/bin/python run_peer.py --log-level INFO --results-dir /tmp/cvb-t010-ajnE/results
```

```text
2026-11-21 21:34:30,224 INFO peerjs_signaling signaling_connecting host=0.peerjs.com port=443 peer_id=cvb-841801ec88411376
2026-11-21 21:34:30,335 INFO peerjs_signaling signaling_message type=OPEN peer_id=cvb-841801ec88411376
http://192.168.0.134:8080/#peer=cvb-841801ec88411376
█▀▀▀▀▀▀▀█▀▀▀███▀▀▀█▀███████▀▀▀▀▀▀▀█
█ █▀▀▀█ █▄▀▀ ▄▀ ▄▀▄▀▀▀█ ▀▀█ █▀▀▀█ █
█ █   █ █▄▄▀ ▀▀██▀▀ ▄█▄▄  █ █   █ █
█ ▀▀▀▀▀ █▀█ ▄▀▄ ▄ ▄ █▀█▀█▀█ ▀▀▀▀▀ █
█▀█▀▀█▀▀▀▄▀▀█▄ █ ▄██▄█▄▄ ▄█▀██▀█▀▀█
█▄▄ ▄▄▀▀  ██   ▄▄ ▄  ▀█  ▀▄▄▀  ▄█▀█
██▄▀▄▀ ▀▄█▀█ ▀█▀▄▀▄█▄▀  █▀▀█▄▄ █  █
██▄█▄█▀▀▀▀▄█ ▀█▄████▀ ▄▀▄▀ ▄▄▀▀▄▄██
█▀  ▄▀ ▀█▄ ▄█▀█▄▄█  █▀█▀█▀█ █ ▀▄███
█▀▀▀▄▀▀▀██ ▄▀▀▀▄█▄█ ▄▀  ▀█▄▀▄▀▄▀ ██
█▄ ▀▀ ▄▀▄▄██ █ ▀▀ ▄▄▀▄▄▄▄██ ▄▀▀▀ ▀█
█▄█  ▀ ▀▄▀▀▀█ ██ ▄ ▀▀ ▄▀▀▄▀▀▄█ █▀ █
█▀▄██ ▀▀▄█▄▀   ▀▄▀█▀▀▄▀      ▀▄▀ ██
█▀▀▀▀▀▀▀█ ▀▄▄▄▀ █▄▀ ▀▄▄▄▀ █▀█ ▄█▀ █
█ █▀▀▀█ █▄▀▄██▄█ ▀  █ █▄█ ▀▀▀ ▀ ███
█ █   █ █ █ █▄█ ▀ ▄▀▄█▄  ▄▀█ ▀▄▄▄██
█ ▀▀▀▀▀ █▀▄▀▄  ▀██▄ ▀▄▄▄▄█ ▀█▀▄██▄█
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
```

`type=OPEN` přišlo za ~110 ms. Peer id `cvb-841801ec88411376`. URL používá LAN adresu zjištěnou UDP `connect` bez odeslání datagramu. V logu není signaling token.

## Definition of Done

Všechna kritéria v [dod.md](dod.md) jsou po opětovném běhu gate znovu ✅, včetně limitu součtu payloadů. Review kolo 1 tím není uzavřené: verdikt APPROVE v tomto reportu není.
