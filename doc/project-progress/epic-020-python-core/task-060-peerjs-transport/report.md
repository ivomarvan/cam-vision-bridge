---
apm_category: task-report
apm_ref: E020.T060
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E020.T060 — PeerJsWebRtcTransport

## Co bylo implementováno

- `PeerJsWebRtcTransport` se registruje u PeerJS (výchozí `0.peerjs.com:443`, key `peerjs`, path `/`), posílá `HEARTBEAT` po 5 s a `ID-TAKEN` / `INVALID-KEY` / `ERROR` hlásí jako `SignalingError`.
- Answerer přijme data `OFFER` podle PeerJS 1.5.4 bez pole `browser`, do `ANSWER` smí dát `browser: "aiortc"`. ICE server je `stun:stun.l.google.com:19302`.
- Kandidát před `OFFER` zůstane ve frontě, prázdný kandidát se zahodí. Druhý `OFFER` se odmítne, dokud první peer connection není `failed` nebo `closed`.
- DataChannel předává binární zprávy beze změny a text jako UTF-8 bajty. JPEG neskládá.
- `PhoneCamera()` bez argumentu tento transport vytvoří a před `start` mu předá peer id z QR. Injektovaný `FakeTransport` zůstává tentýž objekt.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-020-python-core/plan.md`
- `doc/project-progress/epic-020-python-core/task-060-peerjs-transport/spec.md`
- `doc/project-progress/epic-020-python-core/task-060-peerjs-transport/dod.md`
- `doc/project-progress/DECISIONS.md`
- `doc/architecture/decisions/ADR-001-transport-webrtc-peerjs.md`
- `doc/project-progress/spec.md`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/peerjs_signaling.py`
- `experiments/2026-11-webrtc-peerjs-aiortc/py/echo_peer.py`
- `src/cam_vision_bridge/api/phone_camera.py`
- `src/cam_vision_bridge/transport/base.py`
- `src/cam_vision_bridge/transport/fake.py`
- `src/cam_vision_bridge/protocol/frame_codec.py`

### Vytvořeno

- `src/cam_vision_bridge/transport/peerjs.py`
- `tests/transport/test_peerjs_local.py`

### Změněno

- `src/cam_vision_bridge/api/phone_camera.py`
- `src/cam_vision_bridge/transport/__init__.py`
- `src/cam_vision_bridge/transport/base.py`
- `tests/api/test_phone_camera.py`
- `README.md`
- `doc/project-progress/epic-020-python-core/task-060-peerjs-transport/dod.md`

### Nedotčeno (Context Bundle)

- `experiments/`
- `src/cam_vision_bridge/protocol/frame_codec.py`
- `schema/`
- `doc/project-progress/epic-020-python-core/plan.md`

## Použité metody a rozhodnutí

### Signalizace

Produkční klient je nový modul. Kód spiku se neimportuje, protože mluví echo protokolem. Registrace čeká na `OPEN`. Token je v URL WebSocketu a do logu se nepíše. `start` se vrací po `OPEN`, ne až po otevření DataChannelu: `PhoneCamera` teprve potom tiskne QR, telefon nabídne `OFFER` až po naskenování. To odpovídá `spec.md` § 4.6 (nedostupná signalizace spadne při startu).

### Jedno živé spojení

Živé je spojení ve stavu jiném než `failed` a `closed`. `disconnected` se bere jako živé, protože ICE se z něj může vzpamatovat a druhý telefon by ho neměl přerušit. Odmítnutí je varování v logu, bez druhého `RTCPeerConnection` a bez druhého `ANSWER`. `OFFER` bez `connectionId` vyhodí `SignalingError` dřív, než peer connection vznikne.

### DataChannel

Prohlížeč kanál vytváří. Python je answerer. Binární payload jde do fronty tak, jak přišel. Text se kóduje jako UTF-8 a dál ho parsuje smyčka `PhoneCamera`. Prázdný trickle kandidát se ignoruje. Kandidát s neznámým `connectionId` čeká v `PendingCandidates`, dokud nepřijde jeho `OFFER`.

### Napojení na PhoneCamera

Signatura `PhoneCamera(transport=None, ...)` se neměnila. `None` znamená `PeerJsWebRtcTransport()`. Před `start` se na něj zapíše totéž peer id, které je v URL. `FakeTransport` tuto větev neprojde. `TransportNotConfigured` zůstává ve veřejném exportu, ale chybějící argument už ho nevyvolá. `close` zavře PeerJS transport; fake transport metodu `close` nemá a nesahá se na něj.

### Testy bez cloudu

Jednotkové testy podstrčí falešný WebSocket (`ID-TAKEN`, `INVALID-KEY`, `ERROR`, heartbeat). Integrační test spojí dva `RTCPeerConnection` v jednom procesu s prázdným seznamem ICE serverů, SDP a kandidáty předá přímo do answereru a ověří, že `pack_chunk` dorazí jako stejné bajty. Modul testů navíc shodí pokus otevřít `_open_peerjs_socket` nebo přeložit `0.peerjs.com`. Veřejný cloud se nevolá. Nové ADR není: volba transportu je ADR-001 a tvar `OFFER` je DECISIONS #6.

## Odchylky od spec.md

Docstring `Transport.start` a `Transport.receive_bytes` v `src/cam_vision_bridge/transport/base.py` je upřesněný. Signatury jsou stejné. `start` se vrací po úspěšné registraci, ne až když je DataChannel od telefonu otevřený — jinak by QR vznikl až po spojení, které bez QR nevznikne. `receive_bytes` popisuje i textové zprávy jako UTF-8 bajty. `FakeTransport` kontrakt dál splňuje. Chování answereru se tím nemění.

## Reference do kódu

| File | Lines | Summary |
|---|---|---|
| `src/cam_vision_bridge/transport/peerjs.py` | 44-55 | Výchozí cloud, STUN, heartbeat 5 s, stavy, kdy je spojení mrtvé |
| `src/cam_vision_bridge/transport/peerjs.py` | 161-203 | `parse_offer` bez `browser`; `ANSWER` smí `browser: "aiortc"` |
| `src/cam_vision_bridge/transport/peerjs.py` | 111-130 | `PendingCandidates` — fronta trickle kandidátů před `OFFER` |
| `src/cam_vision_bridge/transport/peerjs.py` | 403-453 | `start` po `OPEN`, `send_json`, `receive_bytes` |
| `src/cam_vision_bridge/transport/peerjs.py` | 602-619 | Druhý `OFFER` při živém spojení se odmítne |
| `src/cam_vision_bridge/transport/peerjs.py` | 722-750 | DataChannel: bajty beze změny, text jako UTF-8 |
| `src/cam_vision_bridge/api/phone_camera.py` | 89 | `PhoneCamera()` bez argumentu vytvoří `PeerJsWebRtcTransport` |
| `src/cam_vision_bridge/api/phone_camera.py` | 121, 205-209 | Peer id z QR se zapíše jen do PeerJS transportu |
| `src/cam_vision_bridge/transport/base.py` | 12-29 | Upřesněný kontrakt `start` / `receive_bytes` |
| `tests/transport/test_peerjs_local.py` | 34-53 | Zákaz socketu a DNS na `0.peerjs.com` |
| `tests/transport/test_peerjs_local.py` | 99-115 | `OFFER` bez `connectionId`, fronta kandidátů, `ID-TAKEN` |
| `tests/transport/test_peerjs_local.py` | 122-252 | aiortc offer/answer, jeden chunk, odmítnutý druhý `OFFER` |
| `tests/api/test_phone_camera.py` | 61-79 | Výchozí transport a zachovaný `FakeTransport` |

## Výsledek regresního testu

| Command / scope | Result | Notes |
|---|---|---|
| `.venv/bin/ruff check .` | ✅ exit 0 | |
| `.venv/bin/ruff format --check .` | ✅ exit 0 | |
| `.venv/bin/mypy src/ --strict` | ✅ exit 0 | 15 souborů |
| `.venv/bin/pytest -q --tb=line` | ✅ exit 0 | 91 passed |

Nové testy i celá sada prošly. Regrese se neobjevila.

## Definition of Done

Všechna kritéria v [dod.md](dod.md) jsou splněná.
