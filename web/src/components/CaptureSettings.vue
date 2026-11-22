<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';

import { FACING_MODE } from '@/camera/captureFrame';
import { CAPTURE_PRESETS, type CaptureSize } from '@/camera/captureSize';
import { useSessionStore } from '@/stores/session';

const store = useSessionStore();
const { facingMode, jpegQuality, captureSize, encodedBitmapSize } = storeToRefs(store);

/** Stable option value for one preset row in the size select. */
function presetOptionValue(size: CaptureSize): string {
  return `${String(size.width)}×${String(size.height)}`;
}

const capturePresetKey = computed({
  get(): string {
    return presetOptionValue(captureSize.value);
  },
  set(key: string): void {
    const match = CAPTURE_PRESETS.find((preset) => presetOptionValue(preset) === key);
    if (match !== undefined) {
      store.setCapturePreset(match);
    }
  },
});

const actualBitmapLabel = computed((): string | null => {
  const actual = encodedBitmapSize.value;
  if (actual === null) {
    return null;
  }
  if (actual.width === captureSize.value.width && actual.height === captureSize.value.height) {
    return null;
  }
  return `${String(actual.width)}×${String(actual.height)}`;
});
</script>

<template>
  <section class="grid gap-4 rounded-lg border border-gray-800 bg-gray-900/60 p-4 sm:grid-cols-3">
    <div>
      <label for="facing-mode" class="mb-1 block text-xs font-medium text-gray-300"> Camera </label>
      <select
        id="facing-mode"
        v-model="facingMode"
        class="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100"
      >
        <option :value="FACING_MODE.user">Front (user)</option>
        <option :value="FACING_MODE.environment">Rear (environment)</option>
      </select>
    </div>
    <div>
      <label for="capture-size" class="mb-1 block text-xs font-medium text-gray-300">
        Capture size
      </label>
      <select
        id="capture-size"
        v-model="capturePresetKey"
        class="w-full rounded-md border border-gray-700 bg-gray-950 px-3 py-2 text-sm text-gray-100"
      >
        <option v-for="preset in CAPTURE_PRESETS" :key="presetOptionValue(preset)" :value="presetOptionValue(preset)">
          {{ presetOptionValue(preset) }}
        </option>
      </select>
      <p v-if="actualBitmapLabel !== null" class="mt-1 text-xs text-gray-400">
        Actual bitmap {{ actualBitmapLabel }}
      </p>
    </div>
    <div>
      <label for="jpeg-quality" class="mb-1 block text-xs font-medium text-gray-300">
        JPEG quality {{ Math.round(jpegQuality * 100) }}%
      </label>
      <input
        id="jpeg-quality"
        v-model.number="jpegQuality"
        type="range"
        min="0.35"
        max="0.95"
        step="0.05"
        class="w-full accent-sky-400"
      />
    </div>
  </section>
</template>