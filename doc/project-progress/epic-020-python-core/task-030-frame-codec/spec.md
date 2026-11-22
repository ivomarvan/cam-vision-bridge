---
apm_category: task-spec
apm_ref: E020.T030
apm_level: task
created_by: Planner
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Specification: E020.T030 — Binární kodek snímku

## 1. Goal

Kódovat a skládat binární snímky podle konvencí v `plan.md`. Limity platí předtím, než
volající dostane JPEG bajty. Dekódování OpenCV v tomhle tasku není.

## 2. Inputs

- `plan.md` § Společné konvence E020
- `FrameHeader` z T020

## 3. Outputs

`src/cam_vision_bridge/protocol/frame_codec.py`:

- `pack_chunk(header: FrameHeader, payload: bytes) -> bytes`
- `unpack_chunk(data: bytes) -> tuple[FrameHeader, bytes]`
- `FrameAssembler` s injektovaným časem (`now: Callable[[], float]`). `add(header, payload)`
  vrátí kompletní JPEG `bytes`, nebo `None` když snímek ještě není celý.
- `FrameProtocolError` pro porušení limitů.
- `split_jpeg(jpeg: bytes, *, frame_id, captured_at, w, h, chunk_bytes: int) -> list[bytes]`
  pro testy a budoucí transport. `chunk_bytes == 0` znamená jedna část.

Průběžný součet nesmí `total_bytes` překročit ještě před uložením části. Duplicitní `part`
se ignoruje. Po chybě se rozpracovaný snímek tohoto `frame_id` zahodí.

## 4. Context Bundle

- **Read:** `plan.md`, T020 `messages.py`. Spike `experiments/.../py/frame_codec.py` jen jako
  popis chování limitů, ne jako kód ke zkopírování (jiná hlavička, má `run_id`).
- **Do not modify:** `experiments/`, schéma jinak než importem modelu, jiné tasky.
- **Interfaces from prior tasks:** `FrameHeader`.

## 5. Dependencies

T020.

## 6. Test Specification

- Happy path: pack → unpack; 3 části v pořadí i mimo něj; `parts = 1`.
- Edge: nekompletní snímek starší než 2 s se zahodí (injektovaný čas); duplicitní část
  nezmění JPEG; `split_jpeg` pro délku přesně násobek `chunk_bytes` nepřidá prázdnou část.
- Error: `header_len > 4096`, `parts` 0 a 257, `part` mimo rozsah, `total_bytes` nad 8 MiB,
  nesoulad metadat mezi částmi, součet ≠ `total_bytes`, průběžný přesah před uložením,
  neplatný JSON, zpráva kratší než 4 B.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `high` (nedůvěryhodný vstup). AGENT_MODELS: `grok-4.7-high`.
