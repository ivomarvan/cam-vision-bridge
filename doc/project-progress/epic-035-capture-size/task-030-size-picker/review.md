---
apm_category: task-review
apm_ref: E035.T030
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Review: E035.T030 — Výběr velikosti na obrazovce

## Verdikt

APPROVE (round 1)

Přiřazený model Reviewer medium `gemini-4-hydrogen-high` nebyl dostupný; revizi provedl
náhradní model `gpt-5.6-sol-medium`.

## Nálezy

Bez nálezů.

## Ověření Definition of Done

- ✅ Obrazovka nabízí jen `640×480`, `1280×720` a `1920×1080`; výchozí stav store je
  `640×480`.
- ✅ `welcome` s `1280` a `720` přepne store na `1280×720`; pouze `width` ani pouze
  `height` volbu nezmění.
- ✅ Výběr platného presetu mění `captureSize`; neznámý rozměr reducer odmítne a ponechá
  stávající hodnotu.
- ✅ Select přední/zadní kamery zůstal v `CaptureSettings.vue`.
- ✅ Skutečná velikost bitmapy se zobrazí jen tehdy, když se liší od vybraného presetu.
- ✅ Nové testy prošly.
- ✅ Celá frontendová sada prošla bez regresí.
- ✅ Picker používá `CAPTURE_PRESETS` a typ `CaptureSize` z dřívějšího T020; v rámci T030
  nebyla posuzována implementace `captureSize.ts`.

## Nezávislý výsledek testů

| Příkaz | Skutečný výsledek | Exit code |
|---|---|---:|
| `docker compose run --rm web npx vue-tsc --noEmit` | bez chyb | 0 |
| `docker compose run --rm web npx eslint .` | bez chyb | 0 |
| `docker compose run --rm web npx vitest run` | 10 souborů, 65 testů prošlo | 0 |

Výsledky odpovídají tvrzením v `report.md`.

## Shrnutí

Revize byla path-scoped na `CaptureSettings.vue`, session store/reducer a jejich testy
dotčené size pickerem a na T030 `dod.md` a `report.md`; ostatní změny v nečistém pracovním
stromu nebyly revidovány. V tomto rozsahu implementace splňuje specifikaci, zachovává
přepínač kamery a správně zobrazuje odlišnou skutečnou velikost bitmapy.
