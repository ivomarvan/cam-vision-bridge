---
apm_category: epic-report
apm_ref: E035
apm_level: epic
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human, Planner
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Epic Report: E035 — Volba velikosti snímku

## Shrnutí epiky

PC si smí ve `PhoneCamera(capture_size=(šířka, výška))` říct o velikost a ta odejde
ve `welcome`. Telefon nabídne jen 640×480, 1280×720 a 1920×1080, výchozí je první.
JPEG i hlavička snímku nesou velikost, kterou video opravdu má. Delší strana nad
1920 se zmenší se zachováním poměru. Přepínač přední a zadní kamery zůstal.

## Dokončené tasky

| Task | Název | Pásmo | Human brána po tasku | Kola revize | BLOCKED | Výsledek |
|------|-------|-------|----------------------|-------------|---------|---------|
| T010 | Požadavek velikosti ve welcome | high | ne | 0 | 0 | ✅ |
| T020 | Velikost snímku na telefonu | high | ne | 0 | 0 | ✅ |
| T030 | Výběr velikosti na obrazovce | medium | ne | 0 | 0 | ✅ |

Human brána po tasku je „ne“ podle `910-epic-human-gate.mdc`. Reviewer `medium` pro
T030 byl záskok `gpt-5.6-sol-medium`.

## Klíčová rozhodnutí a poznatky

- Schema se neměnila. `Welcome.width` a `Welcome.height` už v protokolu byly.
- Neúplné `welcome` (jen jeden rozměr) telefon nemění. Cizí dvojice se srovná na
  nejbližší počet pixelů, remíza bere menší položku.
- Druhé `hello` se neposílá. PC vidí novou velikost v hlavičce dalšího snímku.
- Když se bitmapa liší od vybrané položky, stránka ukáže text „Actual bitmap“.
- Zkouška v prohlížeči bez kamery ukázala, že změna velikosti bez `#peer` přepsala
  hlášku o spárování chybou kamery. Otevření kamery bez peer id teď stav `idle` nechá.

## Odchylky od Epic Planu

T010 a T020 běžely vedle sebe, jak plán dovolil. Jinak žádné.

## Doporučení pro Planner

- E040 pořád měří DoD na výchozích 640×480. Větší preset je volba, ne nový základ.
- Seznam fyzických senzorů a FPS z `welcome` zůstávají mimo tuto epiku.
- Na telefonu je třeba ověřit, že 1280×720 a 1920×1080 senzor opravdu dá a že
  DataChannel udrží snímkovou frekvenci.

## Využití tokenů (vyplní Human)

—

## Reference

- Epic Plan: [plan.md](plan.md)
- Task Reports: [T010](task-010-welcome-capture-size/report.md),
  [T020](task-020-phone-capture-size/report.md),
  [T030](task-030-size-picker/report.md)
