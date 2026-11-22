# Vue 3 + TypeScript + Vite

Phone UI for CAM-VISION-BRIDGE. Tooling runs in the `web` Docker service; see `../README.docker.md`.

## Protocol types

`src/protocol/generated.ts` is generated from `schema/cam-vision-bridge-v1.schema.json`. Do not edit it by hand.

```bash
docker compose run --rm --user "$(id -u):$(id -g)" web npm run generate:protocol
```

`src/protocol/generated.test.ts` regenerates into a temp file and fails if the committed output differs.

## Frame codec

`src/protocol/frameCodec.ts` packs the same binary chunk as the Python frame codec: a big-endian uint32 header length, UTF-8 JSON `FrameHeader` (keys in model order), then that part's JPEG bytes. `splitFrame` defaults to 16384-byte parts. `chunkBytes: 0` sends one part. `parseServerMessage` accepts a protocol v1 JSON object whose `t` is known and whose `v` is 1.

## Camera and overlays

`src/camera/captureFrame.ts` opens `user` or `environment` through an injected `getUserMedia` and encodes the current video frame as a 640×480 `image/jpeg`. The JPEG is not mirrored.

`src/overlay/mapPoint.ts` maps normalized coordinates into the view (letterbox, optional x mirror). `src/overlay/drawItems.ts` strokes every v1 geometry item through that function. Text without a point and `metrics` are returned for the side panel and are not drawn.

## Peer session

`src/session/peerSession.ts` speaks protocol v1 over an injected PeerJS client. `peerjs` is pinned to **1.5.4** (the version measured in E010). That release's offer payload has no `browser` field. The session connects with `serialization: "raw"` and `reliable: true`, sets `binaryType` to `arraybuffer`, then sends `hello`. See `src/session/README.md`.

This template should help get you started developing with Vue 3 and TypeScript in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about the recommended Project Setup and IDE Support in the [Vue Docs TypeScript Guide](https://vuejs.org/guide/typescript/overview.html#project-setup).
