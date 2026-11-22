import { defineStore } from 'pinia';
import { ref } from 'vue';

/** Connection lifecycle; extended in later tasks. */
export type SessionStatus = 'idle';

/**
 * Global WebRTC session state for the single-screen app.
 */
export const useSessionStore = defineStore('session', () => {
  const status = ref<SessionStatus>('idle');

  return { status };
});