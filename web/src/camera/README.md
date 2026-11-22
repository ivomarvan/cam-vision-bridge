# Camera capture

`captureSize.ts` lists the three presets, smallest first: 640×480, 1280×720, 1920×1080. The default is the first. `nearestPreset` picks the closest pixel count and keeps the smaller preset on a tie. `sizeFromWelcome` returns that preset, or `null` when width or height is missing. `bitmapSize` uses the video's real size and, when the longer side is above 1920, scales both sides so that side is 1920.

`captureFrame.ts` opens a camera through an injected `getUserMedia` and encodes the current video frame as `image/jpeg` at that bitmap size. Ideal width and height follow the selected preset. `facingMode` stays exact: `user` (front) or `environment` (rear). The JPEG is not mirrored. `previewIsMirrored` reports whether overlay code should pass `mirrorX: true` to `mapPoint` — only the front camera.

Unit tests pass a fake video element and a canvas that records `drawImage`. They do not call a real camera.
