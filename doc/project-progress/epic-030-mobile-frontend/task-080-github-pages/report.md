---
apm_category: task-report
apm_ref: E030.T080
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E030.T080 — GitHub Actions Pages

## Co bylo implementováno

- Workflow `.github/workflows/pages.yml` se spouští jen při `push` na `master`, sestaví `web/` na Node.js 22.12.0 a nasadí artifact `web/dist` na GitHub Pages.
- Akce `actions/checkout` v7.0.1, `actions/setup-node` v7.1.0, `actions/upload-pages-artifact` v5.0.0 a `actions/deploy-pages` v5.0.1 jsou připnuté na ověřený commit SHA. V repozitáři není žádné tajemství; oprávnění jsou `contents: read`, `pages: write`, `id-token: write`.
- Před uploadem se výstup Vite přesune do `web/dist/v1/`, aby URL `https://ivomarvan.github.io/cam-vision-bridge/v1/` seděla na `base` `/cam-vision-bridge/v1/`. Lokální `npm run build` pořád píše `web/dist/index.html`.
- `README.md` má anglický odstavec, jak stránku otevřít a že peer id je v hashi `#peer=<id>`, který GitHub Pages nepřepisuje.
- Workflow se z agenta nespouštěl (`gh workflow run` ani `act`).

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-030-mobile-frontend/task-080-github-pages/spec.md`
- `doc/project-progress/epic-030-mobile-frontend/task-080-github-pages/dod.md`
- `doc/project-progress/spec.md`
- `doc/apm_config/DESIGN_RULES.user.md`
- `web/vite.config.ts`
- `web/deploy-path.ts`
- `web/package.json`
- `web/Dockerfile`
- `docker-compose.yml`
- `README.md`
- `README.docker.md`
- `.gitignore`
- `web/.gitignore`

### Vytvořeno

- `.github/workflows/pages.yml`
- `doc/project-progress/epic-030-mobile-frontend/task-080-github-pages/report.md`

### Změněno

- `README.md`
- `doc/project-progress/epic-030-mobile-frontend/task-080-github-pages/dod.md`

### Nedotčeno (Context Bundle)

- `web/vite.config.ts` (`base` zůstává `APP_BASE`, tedy `/cam-vision-bridge/v1/`)
- `web/src/` včetně kamery, protokolu a `App.vue`
- Python knihovna, testy a `experiments/`
- `web/dist/` zůstává v `web/.gitignore` a v kořenovém `.gitignore`; do gitu nepatří

## Použité metody a rozhodnutí

### Spouštění a oprávnění

Trigger je pouze `push` na větev `master`. Klíč `pull_request` v souboru není, takže fork PR tento workflow nespustí a nedostane `pages:write`. `workflow_dispatch` také není. Autentizace nasazení je OIDC token jobu (`id-token: write`), žádný `secrets.*`.

### Připnutí akcí

Verze jsou poslední stabilní release k 22. 11. 2026, ověřené přes GitHub API (tag ukazuje na commit, commit je signed). SHA pin je v `uses`, v komentáři je číslo verze. `actions/setup-node` je navíc vůči třem akcím jmenovaným ve spec, protože runner musí nainstalovat Node 22.12.0, stejnou verzi jako image `node:22.12.0-alpine` a `engines.node`.

### Concurrency

Skupina `pages` a `cancel-in-progress: false`. Druhý push počká, rozběhnuté nasazení Pages se neruší, dvě publikace se nepřekrývají.

### Rozložení artifactu

GitHub Pages projektu servíruje kořen artifactu na `https://ivomarvan.github.io/cam-vision-bridge/`. Vite s `base` `/cam-vision-bridge/v1/` odkazuje assety na `/cam-vision-bridge/v1/...` a soubory nechá v kořeni `dist/`. Workflow proto po kontrole prefixu v `web/dist/index.html` přesune strom do `web/dist/v1/` a uploaduje pořád `path: web/dist`. Cesta `.../v1/` pak najde `v1/index.html` i `v1/assets/`.

Nasazení Pages nahrazuje celý web. Až přijde protokol `/v2/`, artifact musí obsahovat i předchozí adresáře `vN/`, jinak starší cesta zmizí. Tohle je poznámka ve workflow, samostatné ADR nevzniklo: cesta `/v1/` je už v `spec.md` a v `web/deploy-path.ts`.

### Lokální důkaz

Příkaz ze spec je `docker compose run --rm web npm run build`. Image běží jako `appuser` (uid 100), bind mount `web/` patří uid 1000 a má mód 775, takže první `mkdir /app/dist` skončí EACCES. To je stejné omezení zápisu na bind mount, které `README.docker.md` už popisuje u `generate:protocol`. Adresář `web/dist` se pro důkaz jednou založil tak, aby ho uid 100 mohl zapisovat; mód `web/` je zpět 775. Opakovaný přesný příkaz pak skončil 0. Na GitHub Actions checkout patří uživateli jobu, ten rozdíl uid tam není.

## Odchylky od spec.md

- Před `actions/upload-pages-artifact` se obsah `web/dist` přesune do `web/dist/v1/`. Spec říká artifact `web/dist` a lokální `dist/index.html` s prefixem; obojí platí (cesta uploadu je `web/dist`, lokální build se nemění). Posun do `v1/` je nutný, aby projektové Pages opravdu servírovaly `https://ivomarvan.github.io/cam-vision-bridge/v1/`. Bez něj by `index.html` ležel v kořeni webu `/cam-vision-bridge/` a prohlížeč by assety z `base` nenašel.
- Ve workflow je i `actions/setup-node` (SHA v7.1.0). Spec jmenuje checkout, upload-pages-artifact a deploy-pages. Bez setup-node by job neměl Node 22.12.0.

## Reference do kódu

| Soubor | Řádky | Shrnutí |
| --- | --- | --- |
| `.github/workflows/pages.yml` | 10–18 | Trigger jen `push` na `master`, permissions bez secrets |
| `.github/workflows/pages.yml` | 22–24 | Concurrency skupina `pages`, běžící deploy se neruší |
| `.github/workflows/pages.yml` | 30–49 | Checkout, Node 22.12.0, `npm ci`, `npm run build`, kontrola prefixu |
| `.github/workflows/pages.yml` | 55–67 | Přesun buildu do `web/dist/v1/` a upload `web/dist` |
| `.github/workflows/pages.yml` | 69–78 | Job `deploy`, environment `github-pages`, `actions/deploy-pages` |
| `README.md` | 90–93 | Odstavec s URL a hashem `#peer=<id>` |
| `web/deploy-path.ts` | 2 | `APP_BASE` `/cam-vision-bridge/v1/` beze změny |
| `web/vite.config.ts` | 7–11 | `base: APP_BASE` beze změny |
| `web/dist/index.html` | 5–9 | Vygenerovaný prefix `/cam-vision-bridge/v1/` (gitignored) |

## Výsledek regresního testu

Nové testovací soubory nevznikly. Kontroly ze spec (build, prefix, tvar workflow) jsou v tabulce. Python ani frontendové zdroje se neměnily.

| Příkaz / rozsah | Výsledek | Poznámka |
| --- | --- | --- |
| `docker compose run --rm web npm run build` | exit 0 | vue-tsc + Vite. `web/dist/index.html` existuje a obsahuje `/cam-vision-bridge/v1/` (ikona, JS, CSS). První mkdir na prázdném bind mountu: EACCES uid 100, viz metody. |
| `docker compose run --rm web npx eslint .` | exit 0 | bez výstupu, tedy bez varování |
| `docker compose run --rm web npx vitest run` | exit 0 | 44/44, 9 souborů |
| `.venv/bin/pytest -q` | exit 0 | 91/91 |
| actionlint v1.7.12 na `pages.yml` | exit 0 | platný workflow |
| Ruby YAML: triggery, permissions, concurrency, `path: web/dist`, žádný `pull_request` / `secrets.` | exit 0 | error case ze spec |
| `gh workflow run` / `act` | nespouštěno | nasazení z agenta neproběhlo |

## Definition of Done

Všechna kritéria v [dod.md](dod.md) jsou ✅. Workflow soubor nasazuje `web/dist`, lokální Docker build prošel s prefixem `/cam-vision-bridge/v1/`, v repozitáři není tajemství, README popisuje URL a hash, a workflow se z agenta nespouštěl.
