<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';

import type { LivePreviewExpose } from '@/components/livePreviewExpose';

const videoRef = ref<HTMLVideoElement | null>(null);
const overlayRef = ref<HTMLCanvasElement | null>(null);
const containerRef = ref<HTMLDivElement | null>(null);

/**
 * Resize the overlay canvas to match the video element's layout box.
 */
function syncOverlaySize(): void {
  const video = videoRef.value;
  const overlay = overlayRef.value;
  if (video === null || overlay === null) {
    return;
  }
  const width = Math.round(video.clientWidth);
  const height = Math.round(video.clientHeight);
  if (width > 0 && height > 0) {
    overlay.width = width;
    overlay.height = height;
  }
}

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  const container = containerRef.value;
  if (container === null) {
    return;
  }
  resizeObserver = new ResizeObserver(() => {
    syncOverlaySize();
  });
  resizeObserver.observe(container);
  syncOverlaySize();
});

onUnmounted(() => {
  resizeObserver?.disconnect();
});

const exposeApi: LivePreviewExpose = {
  get videoElement(): HTMLVideoElement | null {
    return videoRef.value;
  },
  get overlayCanvas(): HTMLCanvasElement | null {
    return overlayRef.value;
  },
  syncOverlaySize,
};

defineExpose(exposeApi);
</script>

<template>
  <div ref="containerRef" class="relative w-full overflow-hidden rounded-lg bg-black">
    <video
      ref="videoRef"
      class="aspect-[4/3] w-full object-contain"
      playsinline
      muted
      autoplay
    />
    <canvas
      ref="overlayRef"
      class="pointer-events-none absolute inset-0 h-full w-full object-contain"
      aria-hidden="true"
    />
  </div>
</template>