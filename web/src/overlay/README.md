# Overlay

`mapPoint.ts` maps a normalized frame coordinate into a view that uses object-fit contain, with an optional horizontal mirror for the front camera.

`drawItems.ts` strokes protocol v1 geometry (`box`, `quad`, `polygon`, `keypoints` and their edges, `polyline`, and `text` that has both coordinates) through `mapPoint`. Text without coordinates and `metrics` are not drawn; `drawItems` returns them for the side panel. The canvas is not cleared here — the caller clears it before each result. An empty item list does not touch the context.

Tests replace the canvas context with a call recorder.
