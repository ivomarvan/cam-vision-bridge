<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';

import CaptureSettings from '@/components/CaptureSettings.vue';
import ConnectionStatus from '@/components/ConnectionStatus.vue';
import LivePreview from '@/components/LivePreview.vue';
import type { LivePreviewExpose } from '@/components/livePreviewExpose';
import PerformanceHud from '@/components/PerformanceHud.vue';
import ResultsPanel from '@/components/ResultsPanel.vue';
import ScreenTools from '@/components/ScreenTools.vue';
import { CaptureFrameError, captureFrame, openCamera, previewIsMirrored } from '@/camera/captureFrame';
import { helloBitmap, type CaptureSize } from '@/camera/captureSize';
import { drawItems } from '@/overlay/drawItems';
import { importPeerJsFactory, PeerSession } from '@/session/peerSession';
import { useSessionStore } from '@/stores/session';
import { statusAfterCameraFailure } from '@/stores/sessionReducer';

const store = useSessionStore();
const rootRef = ref<HTMLElement | null>(null);
const previewRef = ref<LivePreviewExpose | null>(null);

const captureCanvas = globalThis.document.createElement('canvas');
let encodedSize: CaptureSize = { width: store.captureSize.width, height: store.captureSize.height };
let peerSession: PeerSession | null = null;
let mediaStream: MediaStream | null = null;
let rafHandle = 0;
let sendInFlight = false;
let lastPaintedFrameId = -1;
let framesSentInWindow = 0;
let fpsWindowStart = globalThis.performance.now();

/**
 * Skip a frame that is not decoded yet. A bad JPEG quality still propagates.
 *
 * @param error - Failure from {@link captureFrame}.
 * @param video - Element that was encoded.
 * @returns True when the loop should wait for the next frame.
 */
function isSkippableCaptureError(error: unknown, video: HTMLVideoElement): boolean {
  if (error instanceof CaptureFrameError) {
    return true;
  }
  return error instanceof RangeError && (video.videoWidth <= 0 || video.videoHeight <= 0);
}

/**
 * Apply a complete welcome to the preset used for later frames.
 *
 * An incomplete welcome leaves the preset unchanged. The session does not
 * send a second hello; the next frame header carries the new bitmap.
 *
 * @param session - Open phone session, after `welcome` may have arrived.
 */
function syncWelcomeSize(session: PeerSession): void {
  const welcome = session.welcome;
  if (welcome === null) {
    return;
  }
  store.applyWelcomeSize(welcome.width, welcome.height);
}

/**
 * Stop camera tracks and release the peer session.
 */
function teardownRuntime(): void {
  globalThis.cancelAnimationFrame(rafHandle);
  peerSession?.close();
  peerSession = null;
  if (mediaStream !== null) {
    for (const track of mediaStream.getTracks()) {
      track.stop();
    }
    mediaStream = null;
  }
}

/**
 * Attach the selected camera to the preview video element.
 */
async function bindCamera(): Promise<void> {
  const video = previewRef.value?.videoElement ?? null;
  if (video === null) {
    return;
  }
  if (mediaStream !== null) {
    for (const track of mediaStream.getTracks()) {
      track.stop();
    }
  }
  try {
    mediaStream = await openCamera(
      (constraints) => globalThis.navigator.mediaDevices.getUserMedia(constraints),
      store.facingMode,
      store.captureSize,
    );
    video.srcObject = mediaStream;
    await video.play();
    previewRef.value?.syncOverlaySize();
  } catch {
    const failure = statusAfterCameraFailure(store.peerId);
    if (failure !== null) {
      store.syncFromPeer(failure.status, failure.statusDetail);
    }
  }
}

/**
 * Paint overlay geometry and push panel-only items into the store.
 */
function paintResult(): void {
  const session = peerSession;
  const result = session?.lastResult ?? null;
  if (result === null || result.frame_id === lastPaintedFrameId) {
    return;
  }
  const overlay = previewRef.value?.overlayCanvas ?? null;
  if (overlay === null) {
    return;
  }
  const context = overlay.getContext('2d');
  if (context === null) {
    return;
  }
  lastPaintedFrameId = result.frame_id;
  context.clearRect(0, 0, overlay.width, overlay.height);
  const panel = drawItems(
    context,
    result.items,
    { width: overlay.width, height: overlay.height },
    { width: encodedSize.width, height: encodedSize.height },
    previewIsMirrored(store.facingMode),
  );
  store.setPanelContent(panel.texts, panel.metrics);
  store.setPerformanceIndicators(store.fps, result.processing_ms);
}

/**
 * Encode one preview frame and send it when the session is ready.
 */
async function maybeSendFrame(video: HTMLVideoElement): Promise<void> {
  const session = peerSession;
  if (session?.status !== 'open' || sendInFlight) {
    return;
  }
  sendInFlight = true;
  try {
    const blob = await captureFrame(video, store.jpegQuality, captureCanvas, store.captureSize);
    encodedSize = { width: captureCanvas.width, height: captureCanvas.height };
    store.setEncodedBitmapSize(encodedSize);
    session.setCaptureSize(encodedSize.width, encodedSize.height);
    const bytes = new Uint8Array(await blob.arrayBuffer());
    session.sendFrame(bytes);
    framesSentInWindow += 1;
    const now = globalThis.performance.now();
    const elapsed = now - fpsWindowStart;
    if (elapsed >= 1000) {
      const measuredFps = (framesSentInWindow * 1000) / elapsed;
      store.setPerformanceIndicators(measuredFps, store.latencyMs);
      framesSentInWindow = 0;
      fpsWindowStart = now;
    }
  } catch (error: unknown) {
    if (!isSkippableCaptureError(error, video)) {
      throw error;
    }
  } finally {
    sendInFlight = false;
  }
}

/**
 * Drive session sync, overlay refresh, and frame upload.
 */
function tick(): void {
  const session = peerSession;
  if (session !== null) {
    store.syncFromPeer(session.status, session.statusDetail);
    syncWelcomeSize(session);
    paintResult();
  }
  const video = previewRef.value?.videoElement ?? null;
  if (video !== null) {
    void maybeSendFrame(video);
  }
  rafHandle = globalThis.requestAnimationFrame(tick);
}

async function startPeerSession(): Promise<void> {
  if (store.peerId === null) {
    return;
  }
  const createPeer = await importPeerJsFactory();
  const video = previewRef.value?.videoElement ?? null;
  encodedSize = helloBitmap(video?.videoWidth ?? 0, video?.videoHeight ?? 0, store.captureSize);
  peerSession = new PeerSession({
    peerId: store.peerId,
    createPeer,
    deviceUa: globalThis.navigator.userAgent,
    width: encodedSize.width,
    height: encodedSize.height,
    camera: store.facingMode,
  });
  store.beginConnecting();
  peerSession.start();
}

onMounted(() => {
  store.configureFromHash(globalThis.location.hash);
  void (async () => {
    await bindCamera();
    await startPeerSession();
    rafHandle = globalThis.requestAnimationFrame(tick);
  })();
});

watch(
  () => store.facingMode,
  () => {
    void bindCamera();
  },
);

watch(
  () => [store.captureSize.width, store.captureSize.height],
  () => {
    void bindCamera();
  },
);

onUnmounted(() => {
  teardownRuntime();
});
</script>

<template>
  <div ref="rootRef" class="min-h-screen bg-gray-950 px-3 py-4 text-gray-100 sm:px-4">
    <main class="mx-auto flex w-full max-w-lg flex-col gap-4">
      <header class="space-y-1">
        <h1 class="text-xl font-semibold tracking-tight">CAM Vision Bridge</h1>
        <p class="text-xs text-gray-400">
          Pair with the QR code from the Python host
          <code class="rounded bg-gray-900 px-1 py-0.5 font-mono">#peer=&lt;id&gt;</code>
        </p>
      </header>
      <ConnectionStatus />
      <CaptureSettings />
      <LivePreview ref="previewRef" />
      <PerformanceHud />
      <ResultsPanel />
      <ScreenTools :root-element="rootRef" />
    </main>
  </div>
</template>