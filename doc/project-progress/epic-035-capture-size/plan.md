---
apm_category: epic-plan
apm_ref: E035
apm_level: epic
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Epic Plan: E035 — Volba velikosti snímku

## Epic Goal

Telefon umí snímat jinak než natvrdo 640×480 a PC si smí velikost vyžádat. Výchozí
zůstává 640×480. Skutečná velikost odchází v `hello` a v hlavičce každého snímku.
Poměr stran se nenatahuje. Přepínač přední/zadní kamery se nemění.

Human zvolil tuto epiku před E040 (DECISIONS #12).

## Task List

| Task | Name | Depends on | Coder model | Band |
|------|------|-----------|-------------|------|
| T010 | Požadavek velikosti ve `welcome` | — | Coder role | high |
| T020 | Velikost snímku na telefonu | — | Coder role | high |
| T030 | Výběr velikosti na obrazovce | T020 | Coder role | medium |

T010 a T020 sahají do jiných stromů a smějí běžet vedle sebe. Tvar `welcome` už je
v protokolu v1, schema se nemění.

**Modely:** Coder `medium` = `composer-2.5`, Coder `high` = `grok-4.7-high`.
Reviewer `high` = `gpt-5.6-sol-medium`. Reviewer `medium` fallback `gpt-5.6-sol-medium`.

## Společné konvence E035

- Povolené položky, v tomto pořadí: 640×480, 1280×720, 1920×1080. Jiná velikost z
  `welcome` se mapuje na nejbližší podle počtu pixelů. Stejná vzdálenost vezme menší.
- `welcome` bez `width` i `height` nechá telefon na aktuální volbě. Jen jedno z polí
  se ignoruje, telefon velikost nemění.
- Po `applyConstraints` (nebo znovuotevření kamery) se čte skutečná velikost videa.
  Canvas JPEG má právě ty pixely. Když je delší strana nad 1920, zmenší se se
  zachováním poměru tak, aby delší strana byla 1920.
- Hlavička snímku `w`/`h` a `hello.width`/`hello.height` říkají tuto skutečnou
  velikost. Druhé `hello` se neposílá. PC pozná změnu z dalšího snímku.
- Výchozí volba telefonu i chybějící `capture_size` na PC je 640×480.
- Přední/zadní přepínač, FPS, schema a `experiments/` se nemění.

## Task Specifications

- [T010](task-010-welcome-capture-size/spec.md)
- [T020](task-020-phone-capture-size/spec.md)
- [T030](task-030-size-picker/spec.md)
