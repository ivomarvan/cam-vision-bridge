---
apm_category: task-report
apm_ref: E030.T030
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E030.T030 — Binární kodek ve stránce

## Co bylo implementováno

- `web/src/protocol/frameCodec.ts` skládá stejný binární chunk jako Python `pack_chunk`: uint32 big-endian délka hlavičky, UTF-8 JSON `FrameHeader`, JPEG bajty této části.
- Klíče JSON jdou v pořadí modelu: `v`, `t`, `frame_id`, `captured_at`, `w`, `h`, `part`, `parts`, `total_bytes`. Objekt se skládá znovu v tomto pořadí, takže pořadí v objektu volajícího na drát nepronikne.
- `splitFrame` má výchozí část 16 384 B. `chunkBytes` 0 je jedna část. Přesný násobek nepřidá prázdný konec. Prázdný JPEG zůstane jedna část.
- `parseServerMessage` přijme textovou zprávu protokolu v1 jen když je `t` známý tag a `v === 1`. Tvar polí a položek `result` se kontroluje proti vygenerovaným typům. Neznámý klíč je chyba.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-030-mobile-frontend/task-030-frame-codec/spec.md`
- `doc/project-progress/epic-030-mobile-frontend/task-030-frame-codec/dod.md`
- `doc/project-progress/epic-030-mobile-frontend/plan.md`
- `src/cam_vision_bridge/protocol/frame_codec.py`
- `src/cam_vision_bridge/protocol/messages.py`
- `src/cam_vision_bridge/protocol/results.py`
- `web/src/protocol/generated.ts`
- `schema/cam-vision-bridge-v1.schema.json`
- `doc/apm_config/DESIGN_RULES.user.md`
- `web/package.json`
- `web/tsconfig.json`
- `web/tsconfig.app.json`
- `web/eslint.config.js`

### Vytvořeno

- `web/src/protocol/frameCodec.ts`
- `web/src/protocol/frameCodec.test.ts`

### Změněno

- `web/README.md`
- `doc/project-progress/epic-030-mobile-frontend/task-030-frame-codec/dod.md`

### Nedotčeno (Context Bundle)

- `src/cam_vision_bridge/protocol/frame_codec.py`
- `experiments/`
- `schema/`
- `web/src/protocol/generated.ts`
- `web/package.json`
- `web/src/overlay/`

## Použité metody a rozhodnutí

### Drátový obraz hlavičky

Délka v prvních čtyřech bajtech je `DataView.setUint32` s `littleEndian = false`, tedy stejné `>I` jako Python `struct`. Tělo je `JSON.stringify` bez mezer a `TextEncoder` (UTF-8). Délka se počítá z bajtů, ne ze `string.length`, aby znak mimo ASCII (test s `café`) neseděl na UTF-16.

### Dělení snímku

Výchozí konstanta je `DEFAULT_CHUNK_BYTES = 16384`. `chunkBytes ?? default` nechává nulu být nulou. Řez je `subarray` v kroku `chunkBytes` dokud `start < length`, takže násobek délky nemá prázdný ocas. `packChunk` kopíruje payload do nového bufferu přesné délky zprávy.

### Textová zpráva

`parseServerMessage` vrací `CamVisionBridgeV1TextMessage`. Známé `t` jsou `hello`, `welcome`, `error`, `frame` a `result`. Nejdřív se ověří tag, potom `v === 1`. Chybí-li `t` nebo je neznámé, důvod je `unknown_type`. Známý tag s jiným `v` je `unsupported_version`. Položky výsledku se skládají pole po poli (souřadnice 0..1, párové `text` x/y, tuple u quad/polygon/polyline). Cizí klíč skončí `invalid_message`, stejně jako `extra=forbid` v Pydantic modelech.

### Limity při odeslání

`packChunk` drží stejné stropy jako Python kodek: hlavička nejvýš 4096 B, `parts` 1..256, `part` v rozsahu, `total_bytes` 0..8 MiB, payload části nejvýš `total_bytes`. Záporné nebo necelé `chunkBytes` je `RangeError` volajícího. `FrameProtocolError.reason` je stabilní kód a zároveň text `Error`. Konstruktor `Error` v `tsconfig.app.json` bere jen message, proto se `cause` nepředává.

## Odchylky od spec.md

—

## Reference do kódu

| Soubor | Řádky | Shrnutí |
| --- | --- | --- |
| `web/src/protocol/frameCodec.ts` | 28 | `DEFAULT_CHUNK_BYTES` = 16384 |
| `web/src/protocol/frameCodec.ts` | 81-96 | `FrameProtocolError` |
| `web/src/protocol/frameCodec.ts` | 127-137 | `packChunk` |
| `web/src/protocol/frameCodec.ts` | 150-161 | `splitFrame` |
| `web/src/protocol/frameCodec.ts` | 173-180 | `parseServerMessage` |
| `web/src/protocol/frameCodec.ts` | 192-206 | limity `parts`, `part`, `total_bytes` |
| `web/src/protocol/frameCodec.ts` | 211-224 | pořadí klíčů a UTF-8 JSON |
| `web/src/protocol/frameCodec.ts` | 257-266 | řezy JPEG, nula a prázdný snímek bez prázdného ocasu |
| `web/src/protocol/frameCodec.test.ts` | 25-50 | round-trip délky hlavičky a pořadí klíčů |
| `web/src/protocol/frameCodec.test.ts` | 52-75 | délka hlavičky v UTF-8 (`café`) |
| `web/src/protocol/frameCodec.test.ts` | 78-108 | 100000 B / 16384, 7 částí, poslední není prázdná |
| `web/src/protocol/frameCodec.test.ts` | 110-127 | přesný násobek 2×16384 bez třetí části |
| `web/src/protocol/frameCodec.test.ts` | 129-146 | `chunkBytes` 0 → jedna zpráva |
| `web/src/protocol/frameCodec.test.ts` | 211-219 | neznámé nebo chybějící `t`, `v` jiné než 1 |

## Výsledek regresního testu

| Příkaz / rozsah | Výsledek | Poznámka |
| --- | --- | --- |
| `docker compose run --rm web npx vue-tsc --noEmit` | ✅ exit 0 | Příkaz brány. Solution má `files: []`, zdrojáky ve `src/` nenačte |
| `docker compose run --rm web npx vue-tsc --noEmit -p tsconfig.app.json` | ✅ exit 0 | Kontroluje `frameCodec.ts` a test |
| `docker compose run --rm web npx eslint .` | ✅ exit 0 | 0 chyb |
| `docker compose run --rm web npx vitest run` | ✅ exit 0, 21/21 | 4 soubory; 11 v `frameCodec.test.ts`, 10 původních (5+3+2) |

## Definition of Done

Všechna kritéria jsou splněná. Checklist je v [dod.md](dod.md).
