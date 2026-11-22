<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { computed } from 'vue';

import { useSessionStore } from '@/stores/session';

const store = useSessionStore();
const { fps, latencyMs } = storeToRefs(store);

const latencyLabel = computed((): string => {
  if (latencyMs.value === null) {
    return '—';
  }
  return `${String(Math.round(latencyMs.value))} ms`;
});
</script>

<template>
  <section
    class="flex flex-wrap gap-4 rounded-lg border border-gray-800 bg-gray-900/60 px-4 py-3 font-mono text-xs text-gray-200"
    aria-label="Performance"
  >
    <span>FPS {{ fps.toFixed(1) }}</span>
    <span>Latency {{ latencyLabel }}</span>
  </section>
</template>