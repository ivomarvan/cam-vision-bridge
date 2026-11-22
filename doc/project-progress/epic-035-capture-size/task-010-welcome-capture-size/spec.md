---
apm_category: task-spec
apm_ref: E035.T010
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E035.T010 — Požadavek velikosti ve welcome

## 1. Goal

`PhoneCamera` přijme volitelnou velikost snímku a po `hello` ji pošle ve `welcome`.
Bez argumentu zůstane dnešní `welcome` bez rozměrů.

## 2. Inputs

- `Welcome` už má volitelné `width`, `height` a `fps` (`messages.py`). Schema se nemění.
- DECISIONS #12 a `plan.md`.

## 3. Outputs

- Parametr `capture_size: tuple[int, int] | None = None` na `PhoneCamera`.
- `None` → `Welcome(v=1, t="welcome")` beze změny.
- `(1280, 720)` → stejná zpráva s `width=1280` a `height=720`. `fps` se neposílá.
- Neplatná dvojice (nula, záporné, necelé číslo) vyhodí `ValueError` v konstruktoru.

## 4. Context Bundle

- **Read:** `src/cam_vision_bridge/api/phone_camera.py`, `tests/api/test_phone_camera.py`,
  `tests/core/test_frame_hub.py`.
- **Do not modify:** schema, `web/`, `experiments/`, modely zpráv kromě toho, že se
  stávající `Welcome` použije.
- **Interfaces from prior tasks:** žádné.

## 5. Dependencies

Žádné. T020 na tomto kódu nečeká, tvar `welcome` už platí.

## 6. Test Specification

- Happy path: po `hello` odejde `welcome` s požadovanou velikostí.
- Edge: `capture_size=None` pošle `welcome` bez `width` a `height`.
- Error: `(0, 480)` a `(-1, 480)` vyhodí `ValueError` dřív, než se otevře transport.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high`. AGENT_MODELS: `grok-4.7-high`.
