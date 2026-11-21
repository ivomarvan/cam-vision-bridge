---
apm_category: task-report
apm_ref: E010.T020
apm_level: task
created_by: Coder
model: composer-2.5
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-21
updated_at: 2026-11-21
---

# Task Report: E010.T020 — Měřicí stránka (prohlížeč)

## Co bylo implementováno

Statická měřicí stránka (`index.html`, ES modul `spike.js`, čistý `frame_codec.js`) se připojuje přes **PeerJS 1.5.4** k `run_peer.py`, generuje syntetické JPEG 640×480, měří RTT/FPS/ICE a jedním tlačítkem projede matici 8 běhů + sonda `chunk_bytes=0`. Výsledky běhů jsou v tabulce na stránce a v `results/runs.csv` + `results/frames/*.csv`.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-010-spike-webrtc-peerjs/plan.md` (konvence spiku)
- `doc/project-progress/epic-010-spike-webrtc-peerjs/task-010-python-peerjs-echo-peer/spec.md` §2 (OFFER)
- `experiments/2026-11-webrtc-peerjs-aiortc/py/*.py` (read-only)

### Vytvořeno

- `experiments/2026-11-webrtc-peerjs-aiortc/web/index.html`
- `experiments/2026-11-webrtc-peerjs-aiortc/web/spike.js`
- `experiments/2026-11-webrtc-peerjs-aiortc/web/frame_codec.js`
- `experiments/2026-11-webrtc-peerjs-aiortc/web/tests/frame_codec.test.js`
- `experiments/2026-11-webrtc-peerjs-aiortc/results/runs.csv` (9 běhů z baseline)
- `experiments/2026-11-webrtc-peerjs-aiortc/results/frames/*.csv` (9 souborů)
- `experiments/2026-11-webrtc-peerjs-aiortc/results/e2e-matrix-screenshot.png`

### Změněno

- `experiments/2026-11-webrtc-peerjs-aiortc/README.md` (sekce *Measurement page*)

### Baseline desktop (stručná tabulka ze stránky)

| run_id | Q | in_flight | chunk | sent | echo | med RTT | status |
|--------|---|-----------|-------|------|------|---------|--------|
| r20261121T215121-01 | 0.6 | 1 | 16384 | 138 | 138 | 7.5 | ok |
| … | … | … | … | … | … | … | ok (8×) |
| r20261121T215201-09 | 0.8 | 1 | 0 | 138 | 138 | 8.8 | ok (sonda) |

ICE: `host/host udp`. Screenshot: `experiments/2026-11-webrtc-peerjs-aiortc/results/e2e-matrix-screenshot.png`.

**Výřez `runs.csv`:**

```csv
r20261121T215121-01,2026-11-21T20:51:21Z,...,synthetic,640,480,0.6,1,16384,5.0,5106.9,host,host,udp,138,138
r20261121T215201-09,2026-11-21T20:52:01Z,...,synthetic,640,480,0.8,1,0,5.0,5106.9,host,host,udp,138,138
```

**Poznámka k baseline:** Port `8080` na hostiteli obsadila jiná služba (bind na `127.0.0.1`), proto běh použil `python3 -m http.server 18080 --directory web` a `run_peer.py --page-url http://127.0.0.1:18080/`. Na jiném stroji držte výchozí `8080` dle README, pokud je volný.

**PeerJS OFFER (nález review #1):** Při implementaci Coder zjistil, že připnutá 1.5.4
nesplňuje starý text T010 spec § 2 o poli `browser` v `OFFER` — rozhodnutí vrátil
Plannerovi (ne `BLOCKED` v jednořádkovém signálu, ale dokumentovaná neshoda v reportu).
Planner kontrakt sjednotil v **DECISIONS #6** a `plan.md` § *PeerJS 1.5.4 — OFFER*;
Coder kontrakt neschvaloval. Implementace (`peerjs@1.5.4`) odpovídá schválenému seznamu
polí; baseline to potvrzuje funkčně.

## Výsledek regresního testu

| Příkaz / rozsah | Výsledek | Poznámka |
|-----------------|----------|----------|
| `docker run --rm -v "$PWD":/w -w /w node:22.12.0-alpine node --test tests/*.test.js` (z `web/`) | ✅ 7/7 | Image digest `sha256:51eff88af6dff26f59316b6e356188ffa2c422bd3c3b76f2556a2e7e89d080bd`; `node --test tests/` na tomto tagu selže (adresář není objeven) |
| `cd py && .venv/bin/pytest -q` | ✅ 32/32 | Regrese T010 |

## Definition of Done

Viz [dod.md](dod.md) — všechna kritéria ✅.