---
apm_category: task-spec
apm_ref: E010.T030
apm_level: task
created_by: Planner
model: claude-opus-5-5-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-21
updated_at: 2026-11-21
---

# Task Specification: E010.T030 — Analýza výsledků

## 1. Goal

Vytvořit `py/analyze.py`, který z `results/runs.csv` a `results/frames/*.csv` (schémata
v `plan.md`) vygeneruje `results/summary.md` s jednou řádkou tabulky na běh. Hotovo je,
když projdou testy z § 6 a skript vygeneruje souhrn z baseline CSV z T020 (pokud už
existují).

## 2. Inputs

- `plan.md` § CSV výstupy (schémata `runs.csv` a `frames/<run_id>.csv`).
- Metriky a definice:
  - `device` = zkrácený `device_ua`: OS (`Android` / `iOS` / `Linux` / `Windows` / `macOS`
    / `other`) + prohlížeč (`Chrome` / `Safari` / `Firefox` / `other`);
  - `fps` = `frames_echoed / duration_s`; `lost` = `frames_sent − frames_echoed`;
  - `mean_kb` = průměr `bytes` / 1024; `rtt_med`, `rtt_p95`, `decode_med` v ms;
  - p95 metodou **nearest-rank** (`ceil(0.95 · n)`-tý prvek seřazených hodnot);
  - čísla zaokrouhlit na 1 desetinné místo.

## 3. Outputs

- `experiments/2026-11-webrtc-peerjs-aiortc/py/analyze.py` — CLI `--results-dir`
  (výchozí `../results`); jen standardní knihovna (`csv`, `statistics`, `math`,
  `pathlib`, `argparse`, `logging`). Funkce `load_runs(...)`, `summarize_run(...)`,
  `render_markdown(...)` s typy a docstringy; zápis `summary.md` (přepíše existující).
  Sloupce tabulky: `run_id, device, mode, quality, in_flight, chunk_bytes, frames, lost,
  fps, mean_kb, rtt_med, rtt_p95, decode_med, ice_local, ice_remote, ice_proto,
  connect_ms`.
- `py/tests/test_analyze.py`.
- `README.md` experimentu — v sekci *Results* doplnit, jak spustit `analyze.py`.

## 4. Context Bundle

- **Read:** `plan.md`, `py/results_writer.py` (formát zápisu), `.cursor/rules/100-python.mdc`.
- **Do not modify:** ostatní soubory v `py/` a `web/`; `results/*.csv`; `doc/` kromě
  vlastního `report.md` / `dod.md`; `.cursor/`.
- **Interfaces from prior tasks:** T010 — CSV schémata (zapisuje `ResultsWriter`).

## 5. Dependencies

T010 (CSV formát). T020 není nutný — testy používají fixtures.

## 6. Test Specification

`pytest -m unit` s dočasným adresářem a ručně připravenými CSV:

- happy path: 2 běhy se známými hodnotami → správné `fps`, `lost`, `mean_kb`, `rtt_med`,
  `rtt_p95` (nearest-rank, ověřit na 20 hodnotách), `decode_med`, `device`
  (Android/Chrome UA a Linux/Chrome UA); `summary.md` obsahuje hlavičku a 2 řádky;
- edge: běh bez `frames/<run_id>.csv` nebo s 0 snímky → metriky `n/a`, bez pádu;
- error: nečíselná hodnota v řádku frames CSV → řádek přeskočen + `WARNING`, zbytek se
  započítá; chybějící `runs.csv` → exit code 2 a srozumitelná zpráva.
- `ruff check .` a `ruff format --check .` bez chyb.

## 7. Definition of Done

Viz [`dod.md`](dod.md).

## 8. Recommended Coder model

Coder role, band `low` — model podle `000-model-policy.mdc` (AGENT_MODELS: `composer-2.5`);
smí implementovat Planner přímo (`090-apm-orchestration.mdc` § D).
