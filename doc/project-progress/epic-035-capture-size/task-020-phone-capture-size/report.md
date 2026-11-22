---
apm_category: task-report
apm_ref: E035.T020
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E035.T020 — Velikost snímku na telefonu

## Co bylo implementováno

- Telefon zná jen tři velikosti, v pořadí 640×480, 1280×720 a 1920×1080. Výchozí je první.
- `welcome` s oběma rozměry vybere nejbližší položku podle počtu pixelů. Chybí-li šířka nebo výška, volba zůstane.
- JPEG se kreslí ve skutečné velikosti videa. Delší strana nad 1920 se zmenší se zachováním poměru tak, aby byla 1920. Strany se zaokrouhlí na celá čísla a každá je alespoň 1.
- `hello` i hlavička snímku nesou tuto bitmapu. Po změně velikosti se druhé `hello` neposílá; další snímek má novou šířku a výšku v hlavičce.
- Nulová šířka videa vyhodí `RangeError` a JPEG se nevytvoří. Přepínač přední/zadní kamery a obrazovka výběru velikosti zůstaly beze změny.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-035-capture-size/task-020-phone-capture-size/spec.md`
- `doc/project-progress/epic-035-capture-size/task-020-phone-capture-size/dod.md`
- `doc/project-progress/epic-035-capture-size/plan.md`
- `doc/project-progress/DECISIONS.md`
- `doc/apm_config/DESIGN_RULES.user.md`
- `web/src/camera/captureFrame.ts`
- `web/src/session/peerSession.ts`
- `web/src/App.vue`
- `web/src/stores/session.ts`

### Vytvořeno

- `web/src/camera/captureSize.ts`
- `web/src/camera/captureSize.test.ts`

### Změněno

- `web/src/camera/captureFrame.ts`
- `web/src/camera/captureFrame.test.ts`
- `web/src/camera/README.md`
- `web/src/session/peerSession.ts`
- `web/src/session/peerSession.test.ts`
- `web/src/session/README.md`
- `web/src/stores/session.ts`
- `web/src/stores/session.test.ts`
- `web/src/App.vue`
- `doc/project-progress/epic-035-capture-size/task-020-phone-capture-size/dod.md`

### Nedotčeno (Context Bundle)

- `src/cam_vision_bridge/`
- `tests/`
- `schema/`
- `experiments/`
- `web/src/components/CaptureSettings.vue`
- přepínač `facingMode` v `web/src/App.vue` (watch na přední/zadní kameru)

## Použité metody a rozhodnutí

### Seznam a nejbližší preset

Povolené položky jsou jediný seznam `CAPTURE_PRESETS`, od nejmenšího počtu pixelů. `nearestPreset` bere vzdálenost `|šířka × výška − počet pixelů položky|`. Při rovnosti se menší položka nepřepisuje, protože seznam je seřazený a nahradí se jen přísně bližší vzdálenost. `1000×700` (700 000 px) je blíž k 1280×720 (921 600) než k 640×480 (307 200). Střed mezi prvními dvěma položkami, `960×640`, zůstává 640×480.

### Welcome nemění neúplný požadavek

`sizeFromWelcome` vrací `null`, když chybí šířka, výška, nebo obojí (`null` i `undefined`). `presetAfterWelcome` v tom případě vrátí dosavadní preset. Store `applyWelcomeSize` zapíše novou hodnotu jen když se čísla liší, takže neúplné `welcome` kameru znovu neotevírá.

### Bitmapa je senzor, ne natažený preset

`bitmapSize` vezme `videoWidth` a `videoHeight`. Preset se jen ověří, že má kladné rozměry: je to velikost požadovaná od kamery (`ideal` v `getUserMedia`), ne plátno, na které se obraz natáhne. Delší strana nad 1920 se zmenší stejným koeficientem. `Math.round` a spodní hranice 1 drží obě strany jako kladná celá čísla. Video 1280×720 zůstane 1280×720 i při výchozím presetu 640×480. Video 3840×2160 vyjde 1920×1080.

### Jedno hello, hlavička podle bitmapy

`helloBitmap` použije `bitmapSize`, jakmile má video kladný rozměr. Než snímek existuje, `hello` nese aktuální preset, tedy zpočátku 640×480. `PeerSession.setCaptureSize` přepíše šířku a výšku uložené pro další hlavičku. `hello` se posílá jen při otevření kanálu. Po něm už změna velikosti druhé `hello` neodešle; počítač ji uvidí v dalším snímku.

### Kamera se znovu otevře jen při nové volbě

`App.vue` po každém snímku stavu přečte `welcome` a zavolá `applyWelcomeSize`. Samostatný `watch` na šířku a výšku presetu znovu otevře kameru s novým `ideal`. Watch na `facingMode` se neměnil a `facingMode` v constraints zůstává `{ exact }`. Obrazovkový výběr ze tří položek je T030, `CaptureSettings.vue` se neupravoval.

## Odchylky od spec.md

—

## Reference do kódu

| Soubor | Řádky | Shrnutí |
| --- | --- | --- |
| `web/src/camera/captureSize.ts` | 18–36 | `CAPTURE_PRESETS`, strop 1920, `DEFAULT_CAPTURE_SIZE` |
| `web/src/camera/captureSize.ts` | 52–64 | `nearestPreset` |
| `web/src/camera/captureSize.ts` | 76–107 | `sizeFromWelcome`, `presetAfterWelcome` |
| `web/src/camera/captureSize.ts` | 133–175 | `bitmapSize`, `helloBitmap` |
| `web/src/camera/captureFrame.ts` | 64–121 | constraints s presetem, `captureFrame` kreslí `bitmapSize` |
| `web/src/camera/captureFrame.test.ts` | 61–81 | canvas 1280×720 a zmenšení 3840×2160 |
| `web/src/camera/captureFrame.test.ts` | 142–152 | šířka videa 0 je `RangeError`, JPEG se nevolá |
| `web/src/session/peerSession.ts` | 184–217 | hlavička `w`/`h` a `setCaptureSize` bez druhého `hello` |
| `web/src/session/peerSession.test.ts` | 221–247 | hlavička 1920×1080, textová zpráva zůstane jedna |
| `web/src/stores/session.ts` | 100–109 | `applyWelcomeSize` |
| `web/src/stores/session.test.ts` | 52–62 | neúplné `welcome` nechá 640×480, `1000×700` přepne na 1280×720 |
| `web/src/App.vue` | 53–59 | napojení `welcome` na preset |
| `web/src/App.vue` | 143–147 | JPEG a `setCaptureSize` ze stejné bitmapy |
| `web/src/App.vue` | 211–223 | watch `facingMode` beze změny, nový watch jen na preset |

## Výsledek regresního testu

✅ Brána frontendu prošla. Nové testy jsou v tom součtu.

| Příkaz | Výsledek | Poznámka |
| --- | --- | --- |
| `docker compose run --rm web npx vue-tsc --noEmit` | exit 0 | bez chyb typů |
| `docker compose run --rm web npx eslint .` | exit 0 | bez varování |
| `docker compose run --rm web npx vitest run` | exit 0 | 60/60 testů, 10 souborů |

## Definition of Done

Všechna kritéria jsou splněná. Podrobný seznam je v [dod.md](dod.md).
