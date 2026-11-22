---
apm_category: epic-report
apm_ref: E030
apm_level: epic
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human, Planner
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Epic Report: E030 — Mobilní frontend a GitHub Pages

## Shrnutí epiky

Stránka ve `web/` mluví protokolem v1: typy vznikají ze JSON Schema, binární snímek
odpovídá Python kodeku, PeerJS 1.5.4 pošle `hello` a drží jeden snímek na cestě, kamera
skládá JPEG 640×480 a překryv kreslí geometrii přes letterbox. Jedna obrazovka ukáže stav,
texty, metriky, FPS a latenci. Workflow nasadí build na GitHub Pages pod
`/cam-vision-bridge/v1/`, ale z agenta se nespouštěl. Telefonní end-to-end proti
`PhoneCamera` v téhle epice neproběhlo.

## Dokončené tasky

| Task | Název | Pásmo | Human brána po tasku | Kola revize | BLOCKED | Výsledek |
|------|-------|-------|----------------------|-------------|---------|---------|
| T010 | Kostra Vue v Dockeru | medium | ne | 0 | 0 | ✅ |
| T020 | Typy z JSON Schema | high | ne | 0 | 0 | ✅ |
| T030 | Binární kodek ve stránce | high | ne | 0 | 0 | ✅ |
| T040 | Přepočet souřadnic | medium | ne | 0 | 0 | ✅ |
| T050 | PeerJS relace a tok snímků | high | ne | 0 | 0 | ✅ |
| T060 | Kamera a překryvy | high | ne | 0 | 0 | ✅ |
| T070 | Obrazovka, Wake Lock, fullscreen | medium | ne | 0 | 0 | ✅ |
| T080 | GitHub Actions Pages | high | ne | 0 | 0 | ✅ |

Sloupec „Human brána po tasku“ je všude „ne“ kvůli `910-epic-human-gate.mdc` a
DECISIONS #11: Reviewer schválil každý task, Human schvaluje až epiku. Reviewer `medium`
(`gemini-4-hydrogen-high`) není v nabídce subagentů; T040 a T070 revidoval záskok
`gpt-5.6-sol-medium`, zapsaný v jejich `review.md`.

## Klíčová rozhodnutí a poznatky

- Typy se generují vlastním skriptem ze schématu, bez nového npm balíčku. Test porovná
  čerstvý výstup s uloženým souborem.
- JSON hlavička snímku má pevné pořadí klíčů shodné s Python modelem. `chunkBytes = 0`
  je jedna část a přesný násobek 16 384 B nepřidá prázdný konec.
- PeerJS je injektovaný. Testy nevolají `0.peerjs.com`. Pin je `peerjs@1.5.4`.
- `mapPoint` používá contain/letterbox. Přední kamera zrcadlí jen x kolem středu obrazu.
- Text bez souřadnic a metriky se nekreslí; vrací se do panelu.
- Wake Lock a fullscreen se při chybějícím API neschovají pádem: Wake Lock vrátí
  `unsupported`, tlačítko fullscreen se nezobrazí.
- Pages: lokální `web/dist/index.html` zůstává. Workflow před uploadem posune obsah do
  `web/dist/v1/`, aby projektové Pages seděly na `base` `/cam-vision-bridge/v1/`.
  Akce jsou připnuté na commit SHA. Spouští se jen `push` na `master`.

## Odchylky od Epic Planu

T040 běžel až po T030, ne souběžně s T020. Důvod je sdílený Docker volume `web_node_modules`.
Rozsah tasku se nezměnil. T080 přidal `actions/setup-node` a posun artefaktu do `v1/`;
Reviewer to schválil. Plán jinak sedí.

## Doporučení pro Planner

- E040 má udělat ruční měření telefonem proti této stránce, ne proti spike stránce.
  Spike protokol (`run_start` / echo) s `PhoneCamera` nemluví.
- Workflow Pages se nespouštělo. První nasazení nastane až pushem na `master` a potřebuje
  v repozitáři zapnuté GitHub Pages z Actions.
- Bind mount `web/` a uživatel image (uid 100) pořád vyžadují předem založený zapisovatelný
  `web/dist` pro `docker compose run --rm web npm run build` na tomto stroji.
- Žádný task neměl druhé kolo revize ani `BLOCKED`.

## Využití tokenů (vyplní Human)

—

## Reference

- Epic Plan: [plan.md](plan.md)
- Task Reports: [T010](task-010-vue-docker-skeleton/report.md),
  [T020](task-020-schema-types/report.md),
  [T030](task-030-frame-codec/report.md),
  [T040](task-040-coordinate-map/report.md),
  [T050](task-050-peer-session/report.md),
  [T060](task-060-camera-overlays/report.md),
  [T070](task-070-screen-shell/report.md),
  [T080](task-080-github-pages/report.md)
