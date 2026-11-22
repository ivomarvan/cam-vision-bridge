/**
 * Methods exposed by {@link LivePreview.vue} for the parent capture loop.
 */
export interface LivePreviewExpose {
  readonly videoElement: HTMLVideoElement | null;
  readonly overlayCanvas: HTMLCanvasElement | null;
  syncOverlaySize(): void;
}