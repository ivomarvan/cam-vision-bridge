---
apm_category: task-report
apm_ref: E020.T050
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E020.T050 — PhoneCamera

## Co bylo implementováno

- Synchronní fasáda `PhoneCamera` nad asyncio smyčkou ve vlákně na pozadí: `start`, `frames`, `publish`, `run` a `close`.
- `start` po úspěšném `transport.start()` vytiskne stránkovou URL s fragmentem `#peer=` a ASCII QR kód (`qrcode`) a URL vrátí. Bez injektovaného transportu vyhodí `TransportNotConfigured`.
- Čtecí smyčka bere bajty z `Transport`: JSON `hello` nastaví kameru na `FrameHub` a pošle `welcome`, ostatní bajty jdou do `ingest_chunk`. `publish` odesílá JSON `result` s `processing_ms` od vydání snímku z `frames()`.
- `run` předá výjimku z callbacku volajícímu. `frames` bez snímku po `connect_timeout_s` vyhodí `ConnectionTimeout`. `close` iterátor ukončí. PeerJS klient v tomto tasku není.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-020-python-core/plan.md`
- `doc/project-progress/epic-020-python-core/task-050-phone-camera/spec.md`
- `doc/project-progress/epic-020-python-core/task-050-phone-camera/dod.md`
- `doc/project-progress/DECISIONS.md`
- `doc/project-progress/spec.md`
- `doc/project-progress/epic-020-python-core/task-060-peerjs-transport/spec.md`
- `src/cam_vision_bridge/core/frame.py`
- `src/cam_vision_bridge/core/frame_hub.py`
- `src/cam_vision_bridge/transport/base.py`
- `src/cam_vision_bridge/transport/fake.py`
- `src/cam_vision_bridge/protocol/messages.py`
- `src/cam_vision_bridge/protocol/results.py`

### Vytvořeno

- `src/cam_vision_bridge/api/phone_camera.py`
- `tests/api/test_phone_camera.py`
- `doc/project-progress/epic-020-python-core/task-050-phone-camera/report.md`

### Změněno

- `src/cam_vision_bridge/__init__.py`
- `src/cam_vision_bridge/api/__init__.py`
- `src/cam_vision_bridge/transport/fake.py`
- `README.md`
- `doc/project-progress/epic-020-python-core/task-050-phone-camera/dod.md`

### Nedotčeno (Context Bundle)

- `experiments/`
- `src/cam_vision_bridge/protocol/frame_codec.py`
- `src/cam_vision_bridge/core/frame_hub.py`

## Použité metody a rozhodnutí

### Fasáda nad asyncio

`start` založí daemon vlákno s vlastním event loopem a na něm zavolá `Transport.start` a čtecí task. `frames` a `publish` přecházejí na smyčku přes `run_coroutine_threadsafe`. Vláčno je daemon, aby zapomenuté `close` nezablokovalo konec procesu; `close` smyčku zastaví a vlákno joine. Odpovídá DECISIONS #1: synchronní API je fasáda, jádro zůstává asyncio.

### Párování

Výchozí stránka je `https://ivomarvan.github.io/cam-vision-bridge/v1/`. Chybějící `peer_id` je `cvb-` a 16 hex znaků (`secrets.token_hex`). Fragment existující URL se nahradí `#peer=<id>`. Na stdout jde jen URL (`print`) a ASCII QR (`qrcode.QRCode.print_ascii`). Ostatní diagnostika jde přes `logging`. QR se tiskne až poté, co `transport.start()` doběhne, aby se při chybě startu nevypisoval kód k mrtvé smyčce.

### Hello, výsledky a jedno spojení

Bajty začínající na `{` se parsují jako textová zpráva protokolu. `hello` zapíše `camera` do `FrameHub` a pošle `welcome` bez volitelných polí. Další `hello` na stejném transportu kameru aktualizuje a `welcome` pošle znovu. Odmítnutí druhého WebRTC OFFER zůstává v T060; tady je jedno aktivní spojení tím, že fasáda drží jeden `Transport`. Binární chunk zpracuje `FrameHub`. Důvod z `on_protocol_error` se pošle jako `error` a čtení pokračuje. `processing_ms` je `time.monotonic` od `yield` ve `frames` po vstup do `publish`. Snímek bez tohoto času zaloguje varování a odejde s `0.0`.

### Timeout a close

`connect_timeout_s` omezuje každé čekání ve `frames`. Po vypršení vznikne `ConnectionTimeout`. `close` zavře hub (čekající `wait_frame` skončí `FrameHubClosed`) a zruší čtecí task. Iterátor pak skončí bez dalšího snímku a bez výjimky za samotné zavření.

### ADR

Nové ADR nevzniklo. Signatura `Transport` ani `FakeTransport` se nemění; úprava `feed_bytes` jen budí už existující frontu. Výchozí síťový transport se nepřidává.

## Odchylky od spec.md

- **`FakeTransport` budí smyčku z jiného vlákna.** `feed_bytes` a `close_inbound` při běžící smyčce v jiném vlákně zařadí bajty přes `call_soon_threadsafe`. Spec mezi výstupy tento soubor nemá. Bez toho `asyncio.Queue.put_nowait` z vlákna volajícího data vloží, ale selektor smyčky `PhoneCamera` neprobudí a `frames()` zůstane viset. Ve stejném vlákně zůstává přímé `put_nowait`. Testy T040 prošly.
- **Export výjimek.** `from cam_vision_bridge import PhoneCamera` platí. Vedle toho jsou exportované `TransportNotConfigured` a `ConnectionTimeout`, protože na nich stojí chování ze spec § 3 a § 6 a volající je musí chytit. T060 je může použít beze změny jmen.
- **`ValueError` v konstruktoru.** Záporné `connect_timeout_s`, prázdné `page_url` a `peer_id` prázdné, s mezerou nebo s `#` skončí `ValueError`. Spec to nevyžaduje. Platné volání (výchozí URL, vygenerované nebo běžné peer id, timeout `None` nebo `>= 0`) se nemění.

## Reference do kódu

| File | Lines | Summary |
| --- | --- | --- |
| `src/cam_vision_bridge/api/phone_camera.py` | 53-63 | `TransportNotConfigured`, `ConnectionTimeout` |
| `src/cam_vision_bridge/api/phone_camera.py` | 65-193 | `PhoneCamera`: `start`, `frames`, `publish`, `run`, `close` |
| `src/cam_vision_bridge/api/phone_camera.py` | 257-302 | čtecí smyčka, `hello` → `welcome`, přeposlání `error` |
| `src/cam_vision_bridge/api/phone_camera.py` | 414-431 | peer id `cvb-` + 16 hex, URL `#peer=`, ASCII QR |
| `src/cam_vision_bridge/transport/fake.py` | 37-74 | vložení inbound bajtů z vlákna mimo smyčku |
| `src/cam_vision_bridge/__init__.py` | 7-16 | veřejný export `PhoneCamera` a výjimek |
| `tests/api/test_phone_camera.py` | 52-208 | happy path, `run`, `close`, callback, timeout, neplatný chunk, export |

## Výsledek regresního testu

| Command / scope | Result | Notes |
| --- | --- | --- |
| `.venv/bin/ruff check .` | ✅ exit 0 | z kořene repozitáře |
| `.venv/bin/ruff format --check .` | ✅ exit 0 | 22 souborů už zformátováno |
| `.venv/bin/mypy src/ --strict` | ✅ exit 0 | 14 zdrojových souborů |
| `.venv/bin/pytest -q --tb=line` | ✅ exit 0 | 79 passed |

Nové testy v `tests/api/test_phone_camera.py` jsou v tom součtu. Regrese v dřívějších testech nebyla.

## Definition of Done

Všechna kritéria v [dod.md](dod.md) jsou splněná.
