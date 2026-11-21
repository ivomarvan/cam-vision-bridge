---
apm_category: dod
apm_ref: E010.T020
apm_level: task
created_by: Planner
model: claude-opus-5-5-high
template_version: v1.2.0-1-gbb135f1
intended_for: Coder
created_at: 2026-11-21
updated_at: 2026-11-21
---

# Definition of Done: E010.T020

- ✅ `web/index.html`, `web/spike.js`, `web/frame_codec.js` existují; žádný build krok; PeerJS z CDN s přesnou verzí `1.5.4` (`esm.sh`); OFFER kontrakt dle DECISIONS #6 / `plan.md` § *PeerJS 1.5.4 — OFFER* (review #1)
- ✅ Binární formát a JSON zprávy odpovídají `plan.md` § Společné konvence spiku (beze změn)
- ✅ Parametry z hash URL (`peer`, `host`, `port`, `path`, `key`, `duration`) fungují s výchozími hodnotami PeerJS cloudu
- ✅ Řízení toku (`in_flight`, horní mez 30 FPS, timeout 2 s) a měření `rtt_ms` / `connect_ms` / ICE typů implementováno dle `spec.md` § 3
- ✅ Režim kamera je dostupný jen v secure context, jinak disabled s vysvětlením
- ✅ Node testy v Dockeru (`node:22.12.0-alpine`, digest `sha256:51eff88af6dff26f59316b6e356188ffa2c422bd3c3b76f2556a2e7e89d080bd`) — příkaz v `report.md` a README
- ✅ End-to-end v Chrome desktop: matice s `duration=5` proběhla (9 řádků v tabulce), CSV v `results/`, screenshot v `results/e2e-matrix-screenshot.png`
- ✅ Sonda bez dělení (`chunk_bytes=0`) proběhla jako poslední běh; stránka zůstala živá (status `ok`)
- ✅ `README.md` experimentu má vyplněnou sekci *Measurement page*
- ✅ Žádné soubory v `py/` ani mimo povolený rozsah nejsou změněny
- ✅ All new tests pass (7/7 Node)
- ✅ Full test suite passes (32/32 pytest T010)