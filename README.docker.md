# Docker — CAM Vision Bridge

## Images

| Service | Base image | Digest |
|---------|------------|--------|
| `web` | `node:22.12.0-alpine` | `sha256:51eff88af6dff26f59316b6e356188ffa2c422bd3c3b76f2556a2e7e89d080bd` |

## Quick start

```bash
# Build and start the Vite dev server (port 5173)
docker compose build web
docker compose up web
```

Open [http://localhost:5173/cam-vision-bridge/v1/](http://localhost:5173/cam-vision-bridge/v1/) (Vite serves with the configured `base`).

After changing `web/package.json`, rebuild:

```bash
docker compose build web
docker compose up -d web
```

## Frontend quality gate (run in Docker)

From the repository root:

```bash
docker compose build web
docker compose run --rm web npx vue-tsc --noEmit
docker compose run --rm web npx eslint .
docker compose run --rm web npx vitest run
```

`node_modules` live in the image; the compose file mounts `./web` for hot reload and uses a named volume for `/app/node_modules`.

## Maintenance

```bash
docker system prune -f
docker volume prune -f
```