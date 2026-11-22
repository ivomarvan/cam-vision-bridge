---
apm_category: task-report
apm_ref: E030.T050
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E030.T050 — PeerJS relace a tok snímků

## Co bylo implementováno

- `web/src/session/peerSession.ts` drží relaci k peer id bez DOM kamery. Klient PeerJS se předává továrnou, takže testy konstruktor `Peer` nevolají.
- Po otevření datového kanálu se nastaví `binaryType` na `arraybuffer` a odešle se `hello` (`v: 1`, `t: "hello"`) ve tvaru generovaného typu.
- `welcome` s `v` jiným než 1 přepne stav na `version-mismatch` a další `sendFrame` nic nepošle. Po `welcome` v1 je na cestě nejvýš jeden snímek, dokud nepřijde `result` nebo protokolové `error`.
- JPEG nad 16 384 B se dělí `splitFrame` / `packChunk`. Menší snímek je jedna binární zpráva. `peerjs` je v `web/package.json` přesně `1.5.4`.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-030-mobile-frontend/task-050-peer-session/spec.md`
- `doc/project-progress/epic-030-mobile-frontend/task-050-peer-session/dod.md`
- `doc/project-progress/epic-030-mobile-frontend/plan.md`
- `doc/project-progress/DECISIONS.md`
- `doc/architecture/decisions/ADR-001-transport-webrtc-peerjs.md`
- `doc/project-progress/spec.md`
- `doc/project-progress/epic-010-spike-webrtc-peerjs/task-020-measurement-page/spec.md`
- `web/src/protocol/frameCodec.ts`
- `web/src/protocol/generated.ts`
- `web/src/utils/peer-id-from-hash.ts`
- `src/cam_vision_bridge/protocol/messages.py`
- `src/cam_vision_bridge/api/phone_camera.py`
- `src/cam_vision_bridge/transport/peerjs.py`
- `doc/apm_config/DESIGN_RULES.user.md`
- `web/package.json`
- `web/eslint.config.js`
- `web/tsconfig.app.json`

### Vytvořeno

- `web/src/session/peerSession.ts`
- `web/src/session/peerSession.test.ts`
- `web/src/session/README.md`

### Změněno

- `web/package.json`
- `web/package-lock.json`
- `web/README.md`
- `doc/project-progress/epic-030-mobile-frontend/task-050-peer-session/dod.md`

V `web/package.json` tento task přidal jen závislost `peerjs` `1.5.4`. Řádek skriptu `generate:protocol` v pracovním stromu už byl a neměnil se.

### Nedotčeno (Context Bundle)

- `src/cam_vision_bridge/`
- `experiments/`
- `schema/`
- `web/src/protocol/generated.ts`
- `web/src/overlay/mapPoint.ts`

## Použité metody a rozhodnutí

### Injektovaný klient

Relace závisí na rozhraní `SessionPeer`, ne na importu PeerJS v testech. `importPeerJsFactory` načte `peerjs` až při zavolání a teprve pak udělá `new Peer()`. To otevře broker (výchozí `0.peerjs.com`). Vitest tuto funkci nevolá. Test navíc podstrčí `WebSocket`, který při konstrukci spadne, takže omylné spojení na cloud test shodí.

Lockfile se aktualizoval `npm install --save-exact peerjs@1.5.4` v kontejneru `web`. Uživatel `appuser` nesmí zapisovat na bind mount a uživatel hostitele nesmí zapisovat do volume `node_modules`, proto instalace běžela jako root v kontejneru a vlastnictví `package.json`, `package-lock.json` a `node_modules` se vrátilo.

### Spojení PeerJS 1.5.4

`peer.connect` dostane `reliable: true` a `serialization: "raw"`. V balíčku 1.5.4 je `"raw"` hodnota `SerializationType.None`: odeslání jde na data channel beze změny a příjem se nepřebaluje. Soubor `experiments/.../web/spike.js` ve stromu není; stejné volby jsou ve specifikaci T050 a v E010.T020. Po události open se `dataChannel.binaryType` nastaví na `arraybuffer`, jak spike popisuje. Pole `browser` se do OFFER nepřidává (DECISIONS #6). Nové ADR není: tvar nabídky je v DECISIONS #6 a volba transportu v ADR-001.

### Hello a welcome

`hello` se skládá jako generovaný typ `Hello` a posílá se jako text až po open kanálu. Klíče jdou v pořadí modelu. `welcome` se před `parseServerMessage` podívá na `t` a `v`, protože kodek u `v !== 1` hodí `unsupported_version` a nerozliší handshake. Cizí verze nastaví `version-mismatch` a srozumitelný `statusDetail`. Snímky se smí poslat jen ve stavu `open`, tedy až po `welcome` s `v` 1. Protokolové `error` spojení neshodí; vyčistí snímek na cestě a důvod nechá v `statusDetail`.

### Jeden snímek a dělení

`DEFAULT_IN_FLIGHT` je 1. Druhé `sendFrame` před `result` nebo `error` skončí hned. Části jednoho JPEGu se pošlou v tom samém volání a počítají se jako jeden snímek. `splitFrame` dostane `chunkBytes: 16384`. Snímek do této délky včetně je jedna binární zpráva, delší se rozdělí. Věta plánu „nad 64 KB“ je tím splněná vůči limitu SCTP: každá část zůstane na 16 384 B payloadu kodeku. Specifikace tasku říká práh 16 384 B, proto se nedělí až od 64 KB.

## Odchylky od spec.md

—

## Reference do kódu

| Soubor | Řádky | Shrnutí |
| --- | --- | --- |
| `web/src/session/peerSession.ts` | 16 | `DEFAULT_IN_FLIGHT` = 1 |
| `web/src/session/peerSession.ts` | 23-26 | `PEER_CONNECT_OPTIONS`: `reliable: true`, `serialization: "raw"` |
| `web/src/session/peerSession.ts` | 149-168 | `start` — továrna a čekání na open peeru |
| `web/src/session/peerSession.ts` | 180-196 | `sendFrame` — zámek in-flight a `splitFrame` |
| `web/src/session/peerSession.ts` | 228-235 | po open: `arraybuffer` a textové `hello` |
| `web/src/session/peerSession.ts` | 237-255 | `welcome` s cizím `v` zastaví příjem i další snímky |
| `web/src/session/peerSession.ts` | 282-296 | `result` / `error` uvolní slot; cizí verze je `version-mismatch` |
| `web/src/session/peerSession.ts` | 309-311 | povolené poslání jen ve stavu `open` a bez snímku na cestě |
| `web/src/session/peerSession.ts` | 328-331 | `importPeerJsFactory` — jediné místo, které načte `peerjs` |
| `web/src/session/peerSession.ts` | 408-427 | `buildHello` z generovaného typu `Hello` |
| `web/src/session/peerSession.test.ts` | 111-139 | happy: `hello`, pak jeden binární snímek |
| `web/src/session/peerSession.test.ts` | 141-165 | edge: druhé `sendFrame` až po `result` |
| `web/src/session/peerSession.test.ts` | 167-176 | protokolové `error` uvolní další snímek |
| `web/src/session/peerSession.test.ts` | 178-189 | `welcome` `v: 2` zastaví posílání |
| `web/src/session/peerSession.test.ts` | 191-219 | JPEG 16 385 B se rovná výstupu `splitFrame` |
| `web/package.json` | 19 | `"peerjs": "1.5.4"` |

## Výsledek regresního testu

✅ Brána ve `web` je zelená. Nové testy: 5/5. Celá sada: 31/31, bez regrese (původní sada bez tohoto tasku měla 26 testů).

| Příkaz | Výsledek | Poznámka |
| --- | --- | --- |
| `docker compose run --rm web npx vue-tsc --noEmit` | exit 0 | bez diagnostiky |
| `docker compose run --rm web npx eslint .` | exit 0 | 0 chyb |
| `docker compose run --rm web npx vitest run` | exit 0 | 6 souborů, 31 testů, Vitest 4.0.8 |

## Definition of Done

Všechna kritéria v [dod.md](dod.md) jsou ✅. PeerJS 1.5.4 je pinned, na cestě je nejvýš jeden snímek, `welcome` s cizí verzí posílání zastaví a testy na broker nejdou. Brána v Dockeru prošla.
