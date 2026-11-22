<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { isFullscreenAvailable, toggleFullscreen } from '@/composables/fullscreen';
import { requestScreenWakeLock, type WakeLockSupport } from '@/composables/screenWakeLock';

const props = defineProps<{
  readonly rootElement: HTMLElement | null;
}>();

const fullscreenSupported = ref(false);
const wakeLockState = ref<WakeLockSupport>('unsupported');

onMounted(async () => {
  fullscreenSupported.value = isFullscreenAvailable(globalThis.document);
  wakeLockState.value = await requestScreenWakeLock(globalThis.navigator);
});

async function onFullscreenClick(): Promise<void> {
  const root = props.rootElement;
  if (root === null) {
    return;
  }
  await toggleFullscreen(root, globalThis.document);
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-3">
    <p class="text-xs text-gray-400">
      Wake lock:
      <span class="font-mono text-gray-200">{{ wakeLockState }}</span>
    </p>
    <button
      v-if="fullscreenSupported"
      type="button"
      class="rounded-md border border-gray-700 bg-gray-900 px-3 py-1.5 text-xs font-medium text-gray-100 hover:bg-gray-800"
      @click="onFullscreenClick"
    >
      Toggle fullscreen
    </button>
  </div>
</template>