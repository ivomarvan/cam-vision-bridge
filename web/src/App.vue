<script setup lang="ts">
// Single-screen shell; peer id is read from the URL hash in later tasks.
</script>

<template>
  <main
    class="flex min-h-screen flex-col items-center justify-center bg-gray-950 px-4 text-gray-100"
  >
    <h1 class="text-2xl font-semibold tracking-tight">CAM Vision Bridge</h1>
    <p class="mt-4 max-w-md text-center text-sm text-gray-400">
      Peer ID is read from the URL hash
      <code class="rounded bg-gray-800 px-1.5 py-0.5 font-mono text-gray-200"
        >#peer=&lt;id&gt;</code
      >.
    </p>
  </main>
</template>