---
apm_category: epic-report
apm_ref: E010
apm_level: epic
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human, Planner
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Epic Report: E010 — Spike: WebRTC aiortc ↔ mobil přes PeerJS

## Shrnutí epiky

Spike ověřil transport z DECISIONS #2. V `experiments/2026-11-webrtc-peerjs-aiortc/`
je Python echo peer (`aiortc`, PeerJS cloud), statická měřicí stránka (PeerJS 1.5.4)
a `analyze.py`. Chrome na Androidu ve stejné Wi-Fi navázal DataChannel a při kvalitě
JPEG 0,6 s jedním snímkem na cestě dosáhl asi 24 FPS a mediánu RTT 18 ms. Human zvolil
ponechat tento transport. Rozhodnutí je v ADR-001.

## Dokončené tasky

| Task | Název | Pásmo | Human brána po tasku | Kola revize | BLOCKED | Výsledek |
|------|-------|-------|----------------------|-------------|---------|---------|
| T010 | Python PeerJS echo peer | high | přeskočena (DECISIONS #5) | 1 | 0 | ✅ |
| T020 | Měřicí stránka | medium | ne | 1 | 0 | ✅ |
| T030 | Analýza výsledků | low | ne | 0 | 0 | ✅ |

T030 nemá `report.md`: pásmo `low`, implementoval Planner v hlavním okně
(`090-apm-orchestration.mdc` § D). Záznam je v `plan.md` a verdikt gate v
[review.md](task-030-results-analysis/review.md).

## Klíčová rozhodnutí a poznatky

- Transport MVP zůstává WebRTC DataChannel přes veřejný PeerJS cloud (DECISIONS #7,
  ADR-001). Fallback na WebSocket se nedělá.
- PeerJS 1.5.4 v `OFFER` neposílá `browser` (DECISIONS #6). Python ho nesmí vyžadovat.
- Na Androidu byl vybraný ICE pár nejdřív `host/prflx`, potom `host/host`, UDP.
  TURN se nepoužil. Navázání trvalo 5,3 s.
- Rozpočet ≥ 10 FPS a medián ≤ 200 ms plní běhy s kvalitou 0,6 a `in_flight` 1.
  Dekódování JPEGu v Pythonu je kolem 4 ms. Ztráty na doběhnutých bězích byly 0.
- Druhá polovina matice skoro přestala posílat snímky, RTT přitom zůstalo nízké.
  Mezi během 7 a 8 jsou asi 3 minuty. Telefon přestal snímky nabízet.
- Snímky měly 15–22 KB. Sonda bez dělení spojení neshodila a `run_end` se nezapsal.
  Chování zprávy nad 64 KB se neměřilo.
- Desktopový baseline na stejném PC není důkaz LAN. Ten dává až Android.

## Odchylky od Epic Planu

- Human gate FT.7 u T010 se nečekala (DECISIONS #5). Reviewer APPROVE proběhl.
- T020 jednou jednostranně popsal chybějící pole `browser`. Review kolo 1 to vrátilo,
  Planner smlouvu upravil (DECISIONS #6), kolo 2 je APPROVE.
- Metrika vytížení CPU na PC se nesbírala. Safari na iOS se neměřilo (bylo volitelné).
- Statický server nešel na port 8080 (Docker na localhostu). Měření jelo na 8088
  s `--page-url`.

## Doporučení pro Planner

- E020 přebírá spike, výchozí `in_flight` je 1 a `OFFER` bez pole `browser`. Dělení
  nad 64 KB v kódu zůstává, i když ho telefon neprověřil.
- E030 už má Wake Lock. Měření ukazuje, že bez něj stránka na telefonu přestane
  posílat, aniž by spadl kanál.
- Reziduální riziko: mDNS v `aioice` a Safari na iOS. Na tomto Chrome se neprojevilo.
- Závislost na veřejném cloudu a internetu platí dál (spec § 5).

## Využití tokenů (vyplní Human)

Planner: ~— · Coder: ~— · Reviewer: ~—

## Reference

- Epic Plan: [plan.md](plan.md)
- ADR: [ADR-001](../../architecture/decisions/ADR-001-transport-webrtc-peerjs.md)
- Task Reports: [T010](task-010-python-peerjs-echo-peer/report.md),
  [T020](task-020-measurement-page/report.md); T030 viz
  [review.md](task-030-results-analysis/review.md)
