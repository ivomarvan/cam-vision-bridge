import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';

import { peerIdFromHash } from '@/utils/peer-id-from-hash';

import { reduceCaptureSize, reduceWelcome, statusAfterCameraFailure } from './sessionReducer';
import { useSessionStore } from './session';

const PRESET_640: { width: number; height: number } = { width: 640, height: 480 };
const PRESET_1280: { width: number; height: number } = { width: 1280, height: 720 };

describe('reduceCaptureSize', () => {
  it('accepts a known preset', () => {
    expect(reduceCaptureSize(PRESET_640, PRESET_1280)).toEqual(PRESET_1280);
  });

  it('rejects an unknown size', () => {
    expect(reduceCaptureSize(PRESET_640, { width: 800, height: 600 })).toEqual(PRESET_640);
  });
});

describe('statusAfterCameraFailure', () => {
  it('leaves the idle pairing hint in place when no peer id is set', () => {
    expect(statusAfterCameraFailure(null)).toBeNull();
  });

  it('reports a connection error once a peer id is being dialed', () => {
    expect(statusAfterCameraFailure('cvb-test')).toEqual({
      status: 'error',
      statusDetail: 'Camera permission or device failed',
    });
  });
});

describe('reduceWelcome', () => {
  it('maps welcome v1 to open', () => {
    expect(reduceWelcome(1)).toEqual({ status: 'open', statusDetail: null });
  });

  it('maps welcome v2 to version-mismatch', () => {
    const next = reduceWelcome(2);
    expect(next.status).toBe('version-mismatch');
    expect(next.statusDetail).toContain('v1');
  });
});

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
    store.configureFromHash('');
    store.beginConnecting();
    expect(store.status).toBe('idle');
    expect(store.peerId).toBeNull();
  });

  it('applyWelcome v1 sets open', () => {
    const store = useSessionStore();
    store.applyWelcome(1);
    expect(store.status).toBe('open');
  });

  it('applyWelcome v2 sets version-mismatch', () => {
    const store = useSessionStore();
    store.applyWelcome(2);
    expect(store.status).toBe('version-mismatch');
  });

  it('starts at 640×480', () => {
    const store = useSessionStore();
    expect(store.captureSize).toEqual(PRESET_640);
  });

  it('switches to 1280×720 when welcome names both dimensions', () => {
    const store = useSessionStore();
    store.applyWelcomeSize(1280, 720);
    expect(store.captureSize).toEqual(PRESET_1280);
  });

  it('leaves the preset when welcome has only one dimension', () => {
    const store = useSessionStore();
    store.applyWelcomeSize(1280, undefined);
    store.applyWelcomeSize(null, 720);
    store.applyWelcomeSize(1280, null);
    expect(store.captureSize).toEqual(PRESET_640);
  });

  it('rejects an unknown preset from the UI setter', () => {
    const store = useSessionStore();
    store.setCapturePreset({ width: 800, height: 600 });
    expect(store.captureSize).toEqual(PRESET_640);
    store.setCapturePreset(PRESET_1280);
    expect(store.captureSize).toEqual(PRESET_1280);
  });

  it('enters connecting only when peer id is present', () => {
    const store = useSessionStore();
    store.configureFromHash('#peer=test-peer');
    store.beginConnecting();
    expect(store.status).toBe('connecting');
    expect(store.peerId).toBe('test-peer');
  });
});