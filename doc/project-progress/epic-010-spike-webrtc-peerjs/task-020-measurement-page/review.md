---
apm_category: task-review
apm_ref: E010.T020
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-21
updated_at: 2026-11-21
---

# Task Review: E010.T020 — Měřicí stránka (prohlížeč)

## Verdikt

REQUEST CHANGES (round 1)

## Nálezy

| # | Severity | Místo | Popis | Doporučená oprava |
|---|----------|-------|-------|-------------------|
| 1 | blocker | `experiments/2026-11-webrtc-peerjs-aiortc/README.md:42-47`, `doc/project-progress/epic-010-spike-webrtc-peerjs/task-020-measurement-page/report.md:60` | Zvolený PeerJS 1.5.4 podle vlastního ověření Coderu neposílá v `OFFER.payload` pole `browser`, které závazný kontrakt T010 `spec.md` § 2 vyžaduje. T020 `spec.md` výslovně říká, že při neshodě má Coder vrátit `BLOCKED` Plannerovi; místo toho README a report jednostranně přijímají změněný kontrakt s odůvodněním, že Python pole nevyžaduje. Funkční baseline proto nedokládá shodu OFFER payloadu a jde o zakázanou tichou změnu rozhraní mezi Tasky. | Vrátit rozhodnutí Plannerovi jako `BLOCKED`: buď použít přesně připnutou verzi/build PeerJS 1.5.x, která posílá celé sjednané payload pole, nebo nechat Plannerem výslovně změnit společný kontrakt a návazné specifikace. Teprve poté aktualizovat implementaci, README, report a DoD podle schváleného rozhodnutí. |

## Ověření Definition of Done

- ❌ `web/index.html`, `web/spike.js` a `web/frame_codec.js` existují bez build kroku a CDN URL je připnutá na `peerjs@1.5.4`, ale tato verze podle doloženého ověření nesplňuje závazný OFFER kontrakt T010 (nález #1).
- ✅ Binární hlavička používá pořadí klíčů `t, run_id, frame_id, part, parts, total_bytes`; textové zprávy odpovídají společným konvencím spiku.
- ✅ Hash parametry `peer`, `host`, `port`, `path`, `key` a `duration` jsou implementovány; nepředané PeerJS volby jsou odstraněny a použijí se cloudové výchozí hodnoty.
- ✅ Řízení toku omezuje počet čekajících snímků přes `in_flight`, odesílání na nejvýše 30 FPS a zahazuje čekání na echo po 2 s. RTT, `connect_ms` a vybraný ICE pár jsou implementovány.
- ✅ Kamera je povolena jen pro secure context s dostupným `getUserMedia`; jinak je volba disabled s vysvětlením.
- ✅ Node gate v přesně připnutém Docker image prošla: 7/7 testů.
- ✅ Desktopový E2E artefakt existuje: screenshot ukazuje 9 řádků se statusem `ok`; `runs.csv` má hlavičku a 9 běhů, ke každému existuje CSV v `results/frames/`.
- ✅ Matice obsahuje kartézský součin quality `{0.6, 0.8}` × in-flight `{1, 2}` × chunk bytes `{16384, 61440}`; devátý a poslední běh je sonda `quality=0.8`, `in_flight=1`, `chunk_bytes=0`. Její výsledek je `ok`.
- ✅ Chyby odesílání a zavření spojení jsou zachyceny do logu/stavu a ovládací prvky se ve `finally` znovu povolí; stránka při selhání sondy nemá spadnout.
- ✅ Experimentální README obsahuje sekci *Measurement page*, připnutý Docker příkaz i upozornění, že stejný PC není důkaz LAN, mDNS ani NAT.
- ✅ Zdrojové a testovací soubory v `py/` mají časy změn nejpozději 21:43:45, schválení T010 bylo zapsáno v 21:46:04 a soubory T020 vznikaly od 21:48:16. `py/` tedy T020 neupravoval; pozdější změny v něm nebyly zjištěny.
- ✅ V path scope nebyl nalezen tajný údaj ani produkční Vue/FastAPI/`src` balíček.
- ✅ Všech 7 nových Node testů prošlo.
- ✅ Python sada měla podle T010 32/32; protože `py/` zůstal nedotčený, Reviewer ji podle zadání znovu nespouštěl.

## Nezávislý výsledek testů

- `docker run --rm -v "$PWD/experiments/2026-11-webrtc-peerjs-aiortc/web":/w -w /w node:22.12.0-alpine@sha256:51eff88af6dff26f59316b6e356188ffa2c422bd3c3b76f2556a2e7e89d080bd node --test tests/*.test.js` — exit code 0; 3 suites, 7 testů, 7 prošlo, 0 selhalo, doba 115 ms.
- `results/runs.csv` — 9 datových řádků v předepsané matici; sonda je poslední.
- `results/frames/` — 9 CSV souborů; namátkově ověřený soubor sondy obsahuje hlavičku `frame_id,bytes,parts,rtt_ms,decode_ms` a data.
- `results/e2e-matrix-screenshot.png` — čitelných 9 řádků, sonda poslední se statusem `ok`, DataChannel `open`, ICE `host/host udp`.
- Počet Node testů a exit code souhlasí s `report.md`. Python tvrzení nebylo znovu testováno, protože kontrola scope a časů potvrdila, že T020 `py/` nezměnil.

## Shrnutí

Review bylo path-scoped pouze na výslovně určené cesty, protože celý epic je necommitnutý a změny jsou untracked; nesouvisející soubory nebyly hodnoceny. Reviewer medium měl podle AGENT_MODELS použít `gemini-4-hydrogen-high`, který není pro subagenty dostupný, proto byl povinně použit fallback Reviewer high `gpt-5.6-sol-medium`. Implementace, Docker gate i baseline artefakty jsou jinak reprodukovatelné, ale vědomá neshoda PeerJS OFFER payloadu se závazným T010 kontraktem vyžaduje rozhodnutí Plannera, takže Task zatím nelze schválit.

# Review round 2

## Verdikt

APPROVE

## Nálezy

Žádné nové nálezy. Blocker #1 z prvního kola je uzavřen.

## Ověření Definition of Done

- ✅ Planner zapsal rozhodnutí do `DECISIONS.md` #6 a sjednotil `plan.md` § *PeerJS 1.5.4 — OFFER*, T010 `spec.md` § 2 a T020 `spec.md` § 2. Schválený data OFFER obsahuje `sdp`, `type`, `connectionId`, `metadata`, `label`, `reliable`, `serialization` a neobsahuje `browser`.
- ✅ README už kontrakt nerozhoduje samo: odkazuje na `DECISIONS.md` #6 a příslušnou sekci `plan.md` a pouze reprodukuje schválený seznam polí.
- ✅ `web/spike.js` zůstává připnutý na `https://esm.sh/peerjs@1.5.4`; ve webovém kódu není kontrola ani požadavek na pole `browser`.
- ✅ Mezi společným kontraktem, oběma Task specifikacemi, README a implementací nebyla nalezena další tichá změna. `ANSWER` z Pythonu smí nadále obsahovat `browser: "aiortc"` přesně podle rozhodnutí #6.
- ✅ Webové JavaScript soubory a Node test se od prvního kola nezměnily: jejich časy zůstaly 21:48:16 až 21:53:35. Docker Node gate proto v tomto kole nebyla znovu spuštěna; platí nezávislý výsledek prvního kola 7/7, exit code 0.
- ✅ Zdrojové a testovací soubory v `py/` se v tomto kole nezměnily; jejich nejpozdější čas změny zůstává 21:43:45, tedy před prvním review. Python testy nebyly znovu spuštěny.
- ✅ V tomto kole se změnily smluvní dokumenty Plannera a pouze README, `report.md` a `dod.md` na straně Tasku; implementace a testy zůstaly beze změny.
- ✅ Ostatní položky DoD ověřené v prvním kole zůstávají platné.

## Nezávislý výsledek testů

- Docker Node gate nebyla opakována, protože `web/*.js` ani `web/tests/` nebyly po prvním kole změněny.
- Poslední nezávislý běh z prvního kola: připnutý image `node:22.12.0-alpine@sha256:51eff88af6dff26f59316b6e356188ffa2c422bd3c3b76f2556a2e7e89d080bd`, exit code 0, 7/7 testů.
- Python suite nebyla opakována, protože `py/` zůstal nedotčený.

## Shrnutí

Druhé kolo bylo opět path-scoped, protože epic zůstává necommitnutý a soubory jsou untracked. Reviewer medium měl podle AGENT_MODELS použít `gemini-4-hydrogen-high`, který není pro subagenty dostupný, proto byl znovu použit fallback Reviewer high `gpt-5.6-sol-medium`. Planner formálně schválil a sjednotil skutečný OFFER kontrakt PeerJS 1.5.4, README na rozhodnutí správně odkazuje a implementace se nezměnila; E010.T020 je připraven pro navazující postup.
