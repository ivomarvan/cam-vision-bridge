---
apm_category: project-brief
apm_ref: PROJECT
apm_level: project
created_by: Human
intended_for: Planner
created_at: 2026-11-21
---

# Brief: CAM-VISION-BRIDGE

Author: Ivo Marvan (role Human)
Date: 21. 11. 2026

## Cíl projektu
Pomocný projekt pro vývoj a testování různých Computer Vision projektů,
kdy se pro snímání obrazu (videa) použije kamera mobilního telefonu.

Tento projekt se pak využije v jiném Python projektu tak, že se kamera a výsledky ze zpracování napojí přes programový adaptér.

API adaptéru je definované zde, implementace je v jiném Python projektu, který tento projekt využívá.

Jako příkladovou studii napojíme tento projekt přes adaptér na projekt https://github.com/Eric-Canas/qrdet (a možná i další podobná).

Chceme dělat různé posy s rozpoznáváním obrazu (v jiných projektech) v pythonu a nezabývat se tam už snímáním obrazu a zobrazováním výsledků.

## Tok dat
- Kamera snímá obraz (video).
- Posílá ho přes síť WebSocket (nebo podobnou technologii podle doporučení AI agenta) na server.
- Přes definovaný adaptér se data dostávají do připojené aplikace (např. projekt https://github.com/Eric-Canas/qrdet či obdobné).
- Součástí adaptéru je i popis textových výstupů (v JSON formátu), které se odesílají do webového prohlížeče.
- Webový prohlížeč zobrazuje výsledky zpracování.
- Součástí definice adaptéru je i popis různých typů datových struktur, které se mohou do mobilu odesílat jako výsledky zpracování.
- Mobilní aplikace pak jednotlivé typy textových informací (z předchozího bodu) zobrazí standardním způsobem. Například obdélníky nalezených objektů s popisem a pod.
- Specifikaci adaptéru musíme navrhnout v konzultaci s AI.


## Dokumentace
Komunikace se mnou (Humanem) by měla probíhat česky, zatímco dokumentace (jako všechny README.md a pod.)
má být v angličtině.