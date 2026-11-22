<script setup lang="ts">
import { storeToRefs } from 'pinia';

import { useSessionStore } from '@/stores/session';

const store = useSessionStore();
const { panelTexts, panelMetrics } = storeToRefs(store);
</script>

<template>
  <section class="rounded-lg border border-gray-800 bg-gray-900/60 p-4">
    <h2 class="text-sm font-semibold text-gray-200">Panel</h2>
    <p v-if="panelTexts.length === 0 && panelMetrics.length === 0" class="mt-2 text-xs text-gray-500">
      Text without coordinates and metrics appear here.
    </p>
    <ul v-if="panelTexts.length > 0" class="mt-3 space-y-1 text-sm text-gray-100">
      <li v-for="(line, index) in panelTexts" :key="`text-${String(index)}`">
        {{ line.text }}
      </li>
    </ul>
    <ul v-if="panelMetrics.length > 0" class="mt-3 space-y-2 font-mono text-xs text-gray-100">
      <li v-for="(block, index) in panelMetrics" :key="`metrics-${String(index)}`">
        <ul class="space-y-0.5">
          <li v-for="(entry, metricIndex) in block.metrics" :key="`m-${String(index)}-${String(metricIndex)}`">
            {{ entry.name }}: {{ entry.value }}
          </li>
        </ul>
      </li>
    </ul>
  </section>
</template>