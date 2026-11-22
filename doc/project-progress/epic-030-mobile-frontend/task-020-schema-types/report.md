---
apm_category: task-report
apm_ref: E030.T020
apm_level: task
created_by: Coder
model: grok-4.7-high
template_version: v1.2.0-1-gbb135f1
intended_for: Human
created_at: 2026-11-22
updated_at: 2026-11-22
---

# Task Report: E030.T020 — Typy z JSON Schema

## Co bylo implementováno

- Generátor `web/scripts/generate-protocol-types.mjs` čte `schema/cam-vision-bridge-v1.schema.json` a zapisuje TypeScript. Nový npm balíček není potřeba.
- `web/src/protocol/generated.ts` vznikl jen tímto během. Hlavička říká, že se soubor needituje. Jsou v něm `hello`, `welcome`, `error`, `frame`, `result` a položky výsledku (`Box`, `Quad`, `Polygon`, `Keypoints`, `Polyline`, `Text`, `Metrics`).
- V `web/package.json` je script `generate:protocol`.
- Test vygeneruje soubor znovu do dočasného adresáře a porovná ho s uloženým. Kopie s přidaným řádkem shodou neprojde. `Text` má volitelné souřadnice `x` a `y`.

## Vstupy a výstupy

### Přečteno

- `doc/project-progress/epic-030-mobile-frontend/plan.md`
- `doc/project-progress/epic-030-mobile-frontend/task-020-schema-types/spec.md`
- `doc/project-progress/epic-030-mobile-frontend/task-020-schema-types/dod.md`
- `schema/cam-vision-bridge-v1.schema.json`
- `doc/architecture/decisions/ADR-002-protocol-v1-json-shapes.md`
- `doc/apm_config/DESIGN_RULES.user.md`
- `web/package.json`
- `web/tsconfig.json`
- `web/tsconfig.app.json`
- `web/tsconfig.node.json`
- `web/eslint.config.js`
- `docker-compose.yml`
- `web/Dockerfile`

### Vytvořeno

- `web/scripts/generate-protocol-types.mjs`
- `web/src/protocol/generated.ts`
- `web/src/protocol/generated.test.ts`

### Změněno

- `web/package.json`
- `web/eslint.config.js`
- `web/tsconfig.node.json`
- `docker-compose.yml`
- `README.docker.md`
- `web/README.md`
- `doc/project-progress/epic-030-mobile-frontend/task-020-schema-types/dod.md`

### Nedotčeno (Context Bundle)

- `schema/`
- `src/cam_vision_bridge/`
- `experiments/`

## Použité metody a rozhodnutí

### Generátor místo balíčku

Spec nabízí skript v `web/scripts`, nebo npm balíček s odůvodněním. Schéma je uzavřená podmnožina draftu 2020-12, kterou produkuje Pydantic: objekty, `const`, `enum`, `anyOf` / `oneOf`, `$ref`, pole a `prefixItems`. Skript tuto podmnožinu překládá a na neznámém klíčovém slově spadne, takže tichá změna schématu neprojde. Nová závislost by chtěla zámek v Dockeru a pořád by bylo potřeba srovnat diskriminované unie. ADR jsem nezakládal: zdroj pravdy už je ADR-002 a spec tento skript pojmenovává.

### Tvar vygenerovaných typů

Jméno rozhraní je klíč v `$defs`. Ten se shoduje s `title`; když se rozejdou, generátor skončí chybou, protože `$ref` ukazuje na klíč. Kořenový `oneOf` je union `CamVisionBridgeV1TextMessage`. Literály `t` a `v` dělají z zpráv i z položek výsledku diskriminované unie. Pole mimo `required` jsou volitelná. `anyOf` s `null` je v typu `| null`, takže `Text.x` a `Text.y` mohou chybět i být `null`. Pevný počet prvků (`quad` má čtyři body, hrana keypointů je dvojice indexů) je tuple. `minimum` a `maximum` v typu nejsou: TypeScript nemá rozsah čísla a spec branded typy nechce. Vlastnosti jsou `readonly`, protože ADR-002 drží naparsovaný model neměnný.

### Schéma viditelné v kontejneru

Služba `web` mountuje jen `./web`. Cesta `web/scripts/../../schema` je na hostu repozitářové `schema/` a v kontejneru `/schema`. Compose proto přidává read-only mount `./schema:/schema`. Obsah `schema/` se nemění. Test i generátor čtou živé schéma, ne kopii zapečenou v image.

### Kdo smí soubor zapsat

Proces v image běží jako `appuser` (uid 100). Bind mount patří uid 1000, takže `npm run generate:protocol` bez změny uživatele skončí `EACCES`. Testy zapisují jen do `/tmp` a uložený soubor nechávají být. Regenerace po změně schématu je v `README.docker.md`: `docker compose run --rm --user "$(id -u):$(id -g)" web npm run generate:protocol`. Druhý běh tímto příkazem obsah `generated.ts` nezměnil.

### Co brána skutečně typově kontroluje

`web/tsconfig.json` je solution z T010 (`files: []` a reference). Příkaz brány `vue-tsc --noEmit` u něj nenačte zdrojáky a skončí 0. Nerozebíral jsem ho: aby solution zároveň obsahoval soubory, musel by `tsconfig.node.json` mít `composite` a emit (TS6306, TS6310) a ESLint by přestal vidět `vite.config.ts`. Typy tohoto tasku kontrolují `vue-tsc --noEmit -p tsconfig.app.json` (aplikace včetně `generated.ts` a testu) a `-p tsconfig.node.json` (`checkJs` na generátoru). Oba skončily 0. Vitest navíc čte text souboru: export `Result` a `Box`, volitelné `x` a `y` u `Text`, a bajtovou shodu s novým během.

## Odchylky od spec.md

—

## Reference do kódu

| Soubor | Řádky | Shrnutí |
| --- | --- | --- |
| `web/scripts/generate-protocol-types.mjs` | 19-25 | Hlavička vkládaná do výstupu, zákaz ruční editace |
| `web/scripts/generate-protocol-types.mjs` | 306-366 | Překlad `$ref`, `const`, `enum`, unionů, polí a primitiv |
| `web/scripts/generate-protocol-types.mjs` | 468-482 | `renderProtocolTypes` složí celý soubor z `$defs` a kořenového `oneOf` |
| `web/src/protocol/generated.ts` | 1-5 | Vygenerovaná hlavička „Do not edit this file by hand.“ |
| `web/src/protocol/generated.ts` | 10-18 | `Box` |
| `web/src/protocol/generated.ts` | 128-144 | `Result` a `Text` s volitelnými souřadnicemi |
| `web/src/protocol/generated.ts` | 160-165 | `CamVisionBridgeV1TextMessage` |
| `web/src/protocol/generated.test.ts` | 63-127 | Happy path pro `result`/`box`, volitelný `text`, ostatní zprávy |
| `web/src/protocol/generated.test.ts` | 129-152 | Shoda s novým během a selhání na kopii s přidaným řádkem |
| `web/package.json` | 16 | Script `generate:protocol` |
| `docker-compose.yml` | 8-12 | Read-only mount schématu na `/schema` |

## Výsledek regresního testu

| Příkaz / rozsah | Výsledek | Poznámka |
| --- | --- | --- |
| `docker compose run --rm web npx vue-tsc --noEmit` | ✅ exit 0 | Příkaz brány. Solution `files: []` nenačte `src/` |
| `docker compose run --rm web npx vue-tsc --noEmit -p tsconfig.app.json` | ✅ exit 0 | Kontroluje `generated.ts` a test |
| `docker compose run --rm web npx vue-tsc --noEmit -p tsconfig.node.json` | ✅ exit 0 | `checkJs` na generátoru |
| `docker compose run --rm web npx eslint .` | ✅ exit 0 | |
| `docker compose run --rm web npx vitest run` | ✅ exit 0, 10/10 | 5 nových v `generated.test.ts`, 5 původních |
| `.venv/bin/python -m pytest tests/ -q` | ✅ exit 0, 91 passed | Python beze změn |

## Definition of Done

Všechna kritéria jsou splněná. Checklist je v [dod.md](dod.md).
