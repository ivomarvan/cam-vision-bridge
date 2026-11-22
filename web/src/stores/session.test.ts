import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';

import { peerIdFromHash } from '@/utils/peer-id-from-hash';

import { useSessionStore } from './session';

describe('useSessionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('starts in idle state', () => {
    const store = useSessionStore();
    expect(store.status).toBe('idle');
  });

  it('stays idle when hash has no peer id', () => {
    const store = useSessionStore();
    expect(peerIdFromHash('')).toBeNull();
    expect(store.status).toBe('idle');
  });
});

describe('peerIdFromHash', () => {
  it('parses peer from hash fragment', () => {
    expect(peerIdFromHash('#peer=abc-123')).toBe('abc-123');
  });
});