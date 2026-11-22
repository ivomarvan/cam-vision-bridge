---
apm_category: task-report
apm_ref: E030.T060
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E030.T060 — Kamera a překryvy

## Co bylo implementováno

- `captureFrame` kreslí aktuální snímek videa na canvas 640×480 a vrací `Blob` typu `image/jpeg`. Kvalita je argument `toBlob` v rozsahu 0..1.
- Kameru otevírá `openCamera` přes injektované `getUserMedia`. `facingMode` je `user` nebo `environment`, omezení je `exact`, mikrofon se nežádá.
- JPEG zůstává obrazem ze senzoru. Zrcadlení přední kamery je jen u překryvu: `previewIsMirrored('user')` je `true` a `drawItems` ho předá do `mapPoint` jako `mirrorX`.
- `drawItems` obkreslí `box`, `quad`, `polygon`, `polyline`, `keypoints` včetně hran a text, který má obě souřadnice. Každý vrchol jde přes `mapPoint`.
- Text bez bodu a položky `metrics` se do canvasu nekreslí. Funkce je vrátí v `PanelItems` pro panel v T070. Prázdné `items` na kontext nesáhne.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-030-mobile-frontend/task-060-camera-overlays/spec.md`
- `doc/project-progress/epic-030-mobile-frontend/task-060-camera-overlays/dod.md`
- `doc/project-progress/epic-030-mobile-frontend/plan.md`
- `doc/project-progress/epic-030-mobile-frontend/task-070-screen-shell/spec.md`
- `doc/project-progress/spec.md`
- `doc/project-progress/DECISIONS.md`
- `doc/apm_config/DESIGN_RULES.user.md`
- `web/src/overlay/mapPoint.ts`
- `web/src/overlay/mapPoint.test.ts`
- `web/src/protocol/generated.ts`
- `web/src/protocol/frameCodec.ts`
- `web/src/session/peerSession.ts`
- `src/cam_vision_bridge/protocol/results.py`
- `web/package.json`
- `web/eslint.config.js`
- `web/vite.config.ts`
- `web/README.md`

### Vytvořeno

- `web/src/camera/captureFrame.ts`
- `web/src/camera/captureFrame.test.ts`
- `web/src/camera/README.md`
- `web/src/overlay/drawItems.ts`
- `web/src/overlay/drawItems.test.ts`
- `web/src/overlay/README.md`
- `doc/project-progress/epic-030-mobile-frontend/task-060-camera-overlays/report.md`

### Změněno

- `web/README.md`
- `doc/project-progress/epic-030-mobile-frontend/task-060-camera-overlays/dod.md`

### Nedotčeno (Context Bundle)

- `src/cam_vision_bridge/`
- `schema/`
- `web/scripts/generate-protocol-types.mjs`
- `web/src/protocol/generated.ts`
- `web/src/overlay/mapPoint.ts`
- `web/src/session/peerSession.ts`
- `web/package.json`

## Použité metody a rozhodnutí

### Kamera a JPEG

Otevření zařízení a kódování snímku jsou dvě funkce v jednom modulu. Proud se otevírá jednou, JPEG se bere z každého snímku videa zvlášť. `getUserMedia` je parametr, testy zařízení nevolají.

`facingMode: { exact: 'user' | 'environment' }` je v omezení schválně přísné: na telefonu volba `ideal` často nechá aktuální senzor. Rozlišení je `ideal` 640×480, ale bitmapa canvasu se před `drawImage` vždy nastaví na 640×480. Zdroj libovolné velikosti (v testu 100×100) se škáluje devítiargumentovým `drawImage` na celou plochu. `toBlob` dostane `image/jpeg` a kvalitu.

Kvalita mimo 0..1 skončí jako `RangeError`. Chybějící snímek, chybějící 2D kontext a `toBlob` vracející `null` jsou `CaptureFrameError`. Funkce je `async`, takže obě chyby volající dostane jako odmítnutý příslib.

### Zrcadlení jen v překryvu

Odeslaný JPEG se nepřevrací. Souřadnice výsledků jsou vůči odeslanému snímku (spec § 4.2). Přední kamera předá `mirrorX: true`. Pomocná `previewIsMirrored` tu volbu drží vedle `facingMode`, aby ji T070 neskládal znovu. Zadní kamera má `mirrorX: false`.

Nové ADR není. Zrcadlení přední kamery už je v `mapPoint` a ve specifikaci projektu.

### Kreslení přes mapPoint

`drawItems` bere kontext, který stačí pokrýt volání `beginPath`, `moveTo`, `lineTo`, `closePath`, `stroke`, `fillText` a `arc`. Skutečný `CanvasRenderingContext2D` je s tímto rozhraním kompatibilní (`OverlayContextIsDomContext`). Test podstrčí záznamník volání.

U `box` jdou přes `mapPoint` všechny čtyři rohy, nejen levý horní. Po zrcadlení x se obdélník složí ze zrcadlených rohů a první `moveTo` má jiné x než u zadní kamery. `quad` a `polygon` se uzavřou, `polyline` zůstane otevřená. Keypointy se spojí podle `edges` a každý bod dostane kroužek. Text s oběma souřadnicemi se píše `fillText` na přepočtený bod.

Prázdné pole na kontext nesáhne, takže ani `stroke`. Canvas se tu nemaže — překreslení předchozího výsledku udělá volající v T070, jinak by prázdný výsledek musel sahat na `clearRect`.

### Panel a neúplná geometrie

Do `PanelItems.texts` jdou texty, které nemají číselné `x` i `y` (chybějící pole, `null`, nebo jen jedna osa). Do `PanelItems.metrics` jdou celé položky `metrics` v původním pořadí, bez sloučení vnitřních čísel. Popisky a skóre u tvarů se nekreslí; na položce zůstávají.

Hrana keypointů s indexem mimo seznam se přeskočí a zbytek snímku se dokreslí. Neznámé `t` spadne do `never` a vyhodí chybu — to je chyba programu, ne prázdný seznam.

## Odchylky od spec.md

—

## Reference do kódu

| Soubor | Řádky | Shrnutí |
| --- | --- | --- |
| `web/src/camera/captureFrame.ts` | 9-15 | 640×480 a `image/jpeg` |
| `web/src/camera/captureFrame.ts` | 47-48 | `previewIsMirrored` — přední kamera vrací `true` |
| `web/src/camera/captureFrame.ts` | 58-68 | `cameraConstraints` — `exact` facingMode, bez audia |
| `web/src/camera/captureFrame.ts` | 76-81 | `openCamera` — injektované `getUserMedia` |
| `web/src/camera/captureFrame.ts` | 98-108 | `captureFrame` — kvalita, kresba, JPEG |
| `web/src/camera/captureFrame.ts` | 124-146 | canvas 640×480 a `drawImage` ze zdroje na celou plochu |
| `web/src/overlay/drawItems.ts` | 45-68 | `OverlayContext` — kontext nahraditelný záznamníkem |
| `web/src/overlay/drawItems.ts` | 70-74 | `PanelItems` — texty a metriky pro T070 |
| `web/src/overlay/drawItems.ts` | 114-128 | `drawItems` — prázdný seznam kontext nečte |
| `web/src/overlay/drawItems.ts` | 168-176 | `box`: čtyři rohy přes `mapPoint` |
| `web/src/overlay/drawItems.ts` | 191-207 | keypointy a text se souřadnicemi |
| `web/src/overlay/drawItems.ts` | 214-216 | jediný přepočet bodu, volá `mapPoint` |
| `web/src/overlay/drawItems.ts` | 244-266 | hrany keypointů; index mimo seznam se přeskočí |
| `web/src/camera/captureFrame.test.ts` | 46-69 | snímek 100×100 se kreslí na 640×480, `drawImage` |
| `web/src/camera/captureFrame.test.ts` | 71-96 | `user` / `environment` do injektovaného `getUserMedia` |
| `web/src/overlay/drawItems.test.ts` | 89-111 | box na přední kameře má zrcadlené x proti zadní |
| `web/src/overlay/drawItems.test.ts` | 113-126 | prázdné `items` nehodí výjimku a nevolá `stroke` |
| `web/src/overlay/drawItems.test.ts` | 128-144 | text do panelu a metrics se nekreslí |
| `web/src/overlay/drawItems.test.ts` | 146-182 | quad, polygon, polyline, keypoints, text přes `mapPoint` |

## Výsledek regresního testu

✅ Brána ve `web` je zelená. Nové testy: 8/8 (3 kamera, 5 překryv). Celá sada: 39/39, bez regrese. Před tímto taskem měla sada 31 testů (report T050).

| Příkaz | Výsledek | Poznámka |
| --- | --- | --- |
| `docker compose run --rm web npx vue-tsc --noEmit` | exit 0 | bez diagnostiky |
| `docker compose run --rm web npx eslint .` | exit 0 | 0 chyb |
| `docker compose run --rm web npx vitest run` | exit 0 | 8 souborů, 39 testů, Vitest 4.0.8 |

## Definition of Done

Všechna kritéria jsou splněná. Checklist je v [dod.md](dod.md).
