---
apm_category: task-review
apm_ref: E010.T010
apm_level: task
created_by: Reviewer
model: gpt-5.6-sol-medium
template_version: v1.2.0-1-gbb135f1
intended_for: Coder, Human
created_at: 2026-11-21
updated_at: 2026-11-21
---

# Task Review: E010.T010 — Python PeerJS echo peer

## Verdikt

REQUEST CHANGES (round 1)

## Nálezy

| # | Severity | Místo | Popis | Doporučená oprava |
|---|----------|-------|-------|-------------------|
| 1 | blocker | `experiments/2026-11-webrtc-peerjs-aiortc/py/frame_codec.py:195-203`, `experiments/2026-11-webrtc-peerjs-aiortc/py/tests/test_frame_codec.py:118-122` | `FrameAssembler` kontroluje součet payloadů až po přijetí všech částí a jejich spojení. Průběžný součet proto může překročit deklarované `total_bytes` a data zůstanou v paměti; nezávislá sonda přijala dvě části po 4 B pro `parts=3,total_bytes=4` bez `FrameProtocolError` (`None`, `None`). Útočník tak může pro jediný snímek držet až téměř `parts × total_bytes` a kontrola může nastat až po velké alokaci při `b"".join(...)`. Limit součtu payloadů proto není bezpečně vynucen na hranici nedůvěryhodného vstupu a příslušné ✅ v `dod.md` neplatí. | Před uložením nové, neduplicitní části spočítat průběžnou velikost; pokud by překročila `total_bytes`, odstranit rozpracovaný snímek a vyhodit `FrameProtocolError`. Doplnit unit test pro průběžný přesah a integrační test, že peer pošle `error` a DataChannel zůstane otevřený. |

## Ověření Definition of Done

- ✅ `py/requirements.txt` existuje; všech sedm přímých závislostí je připnuto přes `==` a má zdůvodňující komentář.
- ✅ Požadovaných pět modulů existuje, poskytuje rozhraní ze `spec.md` § 3 a obsahuje docstringy.
- ❌ Binární kontrakt a limity nejsou beze změn bezpečně vynuceny: průběžný součet payloadů může překročit `total_bytes` před dokončením snímku (nález #1). JSON zprávy a CSV schémata jinak odpovídají plánu.
- ❌ Unit testy procházejí, ale test nesouladu součtu pokrývá pouze výsledný nedostatek bajtů; neověřuje průběžný přesah, který odhaluje nález #1.
- ✅ Dva integrační testy aiortc ↔ `EchoPeer` v paměti prošly; pokrývají echo/CSV a krátkou neplatnou binární zprávu se zachováním otevřeného kanálu.
- ✅ `ruff check .` i `ruff format --check .` skončily s exit code 0.
- ✅ Reviewer nezávisle ověřil registraci: PeerJS cloud vrátil `OPEN`, CLI vypsalo URL a ASCII QR kód. Proces byl po pěti sekundách ukončen nástrojem `timeout`, proto obalový exit code 124; aplikace zalogovala čisté ukončení po `KeyboardInterrupt`.
- ✅ Experimentální `README.md` obsahuje *Goal*, *Setup (Python)*, *Run the peer* a připravené sekce *Measurement page*, *Results*, *Outcome*.
- ✅ V rámci povinně omezeného rozsahu jsou pouze povolené výstupy. Nesouvisející untracked `.cursor/` a ostatní `doc/` nebyly předmětem review.
- ✅ Všech 30 nových testů prošlo.
- ✅ Celá dostupná testovací sada prošla bez regresí.

## Nezávislý výsledek testů

- `.venv/bin/ruff check .` — exit code 0, `All checks passed!`.
- `.venv/bin/ruff format --check .` — exit code 0, 9 souborů již naformátováno.
- `.venv/bin/pytest -v --tb=short` — exit code 0, 30 testů nalezeno, 30 prošlo za 0,85 s.
- `.venv/bin/pytest -m unit -q --tb=short` — exit code 0, 28 prošlo, 2 vyřazeny markerem.
- `.venv/bin/pytest -m integration -q --tb=short` — exit code 0, 2 prošly, 28 vyřazeno markerem.
- Ruční registrace přes `run_peer.py` — `OPEN`, URL a QR ověřeny; obalový exit code 124 po plánovaném pětisekundovém ukončení.
- Bezpečnostní sonda `FrameAssembler` — exit code 0, výstup `None` / `None`; potvrdila přijetí průběžného součtu 8 B při deklarovaných 4 B.

Počty a exit kódy Ruff/pytest souhlasí s `report.md`. Tvrzení o registraci bylo ověřeno znovu nezávisle.

## Shrnutí

Review bylo path-scoped výhradně na cesty určené zadáním; nesouvisející `.cursor/` ani jiné dokumenty nebyly hodnoceny. Gate je zelený a registrace funguje, ale neomezený průběžný součet chunků představuje blocker v bezpečnostní hranici před JPEG dekódováním, takže Task zatím není připraven pro Human review.

# Review round 2

## Verdikt

APPROVE

## Nálezy

Žádné nové nálezy. Blocker #1 z prvního kola je uzavřen.

## Ověření Definition of Done

- ✅ Dříve neplatné kritérium binárního kontraktu a limitů je nyní ověřeno. `FrameAssembler.add()` před uložením nové neduplicitní části vypočte průběžný součet, při překročení `total_bytes` odstraní celý rozpracovaný snímek a vyhodí `FrameProtocolError("payload_size")`. Ke spojení payloadů dojde až po ověření přesné rovnosti součtu s `total_bytes`; `cv2.imdecode` zůstává až za touto hranicí.
- ✅ Dříve nedostatečné pokrytí unit testy je doplněno. `test_assembler_running_sum_above_total_bytes_drops_frame` ověřuje výjimku i odstranění rozpracovaného snímku. Na původním chování by test selhal, protože druhé `add()` vracelo `None` bez výjimky.
- ✅ Integrační test `test_echo_peer_running_overshoot_sends_error_and_stays_open` ověřuje `error` s důvodem `payload_size`, správné `frame_id` a otevřený DataChannel. Na původním chování by nedostal žádnou odpověď a vypršel při čekání.
- ✅ Validace `run_id` zůstává aktivní přes `ensure_run_id()` před uložením chunku i před zápisem CSV. Nezávislá sonda s `../x` skončila `FrameProtocolError("invalid_run_id")`.
- ✅ Ostatní položky DoD z prvního kola zůstávají ověřené; úplná sada i oba Ruff příkazy prošly.

## Nezávislý výsledek testů

- `.venv/bin/ruff check .` — exit code 0, `All checks passed!`.
- `.venv/bin/ruff format --check .` — exit code 0, 9 souborů již naformátováno.
- `.venv/bin/pytest -v --tb=short` — exit code 0, 32 testů nalezeno, 32 prošlo za 0,88 s.
- Nezávislá sonda průběžného součtu — exit code 0; přesah skončil `payload_size` a následná část stejného identifikátoru vrátila `None`, což potvrzuje, že předchozí rozpracovaný snímek byl odstraněn.
- Nezávislá sonda neplatného `run_id` — exit code 0, výsledek `invalid_run_id`.

Počty a exit kódy souhlasí s aktualizovaným `report.md`; rozdíl 0,01 s v době běhu není věcný rozpor.

## Shrnutí

Druhé kolo bylo opět path-scoped pouze na určené cesty. Oprava uzavírá původní bezpečnostní blocker, nové regresní testy jsou účinné a čerstvá gate je zelená; E010.T010 je připraven pro Human review.
