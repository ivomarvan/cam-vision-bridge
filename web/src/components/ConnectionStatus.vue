<script setup lang="ts">
import { storeToRefs } from 'pinia';

import { useSessionStore } from '@/stores/session';

const store = useSessionStore();
const { status, headline, statusDetail } = storeToRefs(store);

const statusTone: Record<string, string> = {
  idle: 'border-amber-500/40 bg-amber-950/40 text-amber-100',
  connecting: 'border-sky-500/40 bg-sky-950/40 text-sky-100',
  open: 'border-emerald-500/40 bg-emerald-950/40 text-emerald-100',
  'version-mismatch': 'border-orange-500/40 bg-orange-950/40 text-orange-100',
  error: 'border-red-500/40 bg-red-950/40 text-red-100',
};
</script>

<template>
  <section
    class="rounded-lg border px-4 py-3"
    :class="statusTone[status] ?? statusTone.idle"
    role="status"
    aria-live="polite"
  >
    <p class="text-sm font-medium">{{ headline }}</p>
    <p v-if="statusDetail" class="mt-1 text-xs opacity-90">{{ statusDetail }}</p>
  </section>
</template>