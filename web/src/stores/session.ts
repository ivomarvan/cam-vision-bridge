import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import { FACING_MODE, type FacingMode } from '@/camera/captureFrame';
import { DEFAULT_CAPTURE_SIZE, presetAfterWelcome, type CaptureSize } from '@/camera/captureSize';
import type { Metrics, Text } from '@/protocol/generated';
import type { SessionStatus } from '@/session/peerSession';

import {
  IDLE_MESSAGE_NO_PEER,
  peerIdFromHashFragment,
  reduceCaptureSize,
  reduceWelcome,
} from './sessionReducer';

export type { SessionStatus };

/** Default JPEG quality for capture (0..1). */
export const DEFAULT_JPEG_QUALITY = 0.85;

/**
 * Global UI and session mirror state for the single-screen app.
 */
export const useSessionStore = defineStore('session', () => {
  const status = ref<SessionStatus>('idle');
  const statusDetail = ref<string | null>(null);
  const idleMessage = ref<string | null>(IDLE_MESSAGE_NO_PEER);
  const peerId = ref<string | null>(null);
  const facingMode = ref<FacingMode>(FACING_MODE.environment);
  const jpegQuality = ref(DEFAULT_JPEG_QUALITY);
  const panelTexts = ref<readonly Text[]>([]);
  const panelMetrics = ref<readonly Metrics[]>([]);
  const fps = ref(0);
  const latencyMs = ref<number | null>(null);
  const captureSize = ref<CaptureSize>({
    width: DEFAULT_CAPTURE_SIZE.width,
    height: DEFAULT_CAPTURE_SIZE.height,
  });
  const encodedBitmapSize = ref<CaptureSize | null>(null);

  const headline = computed((): string => {
    switch (status.value) {
      case 'idle':
        return idleMessage.value ?? 'Waiting for peer id';
      case 'connecting':
        return 'Connecting to PC peer…';
      case 'open':
        return 'Connected';
      case 'version-mismatch':
        return 'Protocol version mismatch';
      case 'error':
        return 'Connection error';
      default: {
        const unreachable: never = status.value;
        return unreachable;
      }
    }
  });

  /**
   * Read `#peer=` from the hash. Missing peer keeps `idle` and never enters `connecting`.
   *
   * @param hash - Current URL hash fragment.
   */
  function configureFromHash(hash: string): void {
    const parsed = peerIdFromHashFragment(hash);
    peerId.value = parsed;
    if (parsed === null) {
      status.value = 'idle';
      idleMessage.value = IDLE_MESSAGE_NO_PEER;
      statusDetail.value = null;
      return;
    }
    idleMessage.value = null;
  }

  /** Start dialling only when a peer id is present and status is still `idle`. */
  function beginConnecting(): void {
    if (peerId.value === null || status.value !== 'idle') {
      return;
    }
    status.value = 'connecting';
  }

  /**
   * Apply handshake outcome from a `welcome` message (store tests and manual sync).
   *
   * @param protocolVersion - `welcome.v`.
   */
  function applyWelcome(protocolVersion: number): void {
    const next = reduceWelcome(protocolVersion);
    status.value = next.status;
    statusDetail.value = next.statusDetail;
  }

  /**
   * Select the preset used for the next frames from a `welcome`.
   *
   * Both dimensions map to the nearest preset. One missing dimension, or both,
   * leaves the current preset in place.
   *
   * @param width - `welcome.width`.
   * @param height - `welcome.height`.
   * @returns The preset now in effect.
   */
  function applyWelcomeSize(
    width: number | null | undefined,
    height: number | null | undefined,
  ): CaptureSize {
    const next = presetAfterWelcome(captureSize.value, width, height);
    if (next.width !== captureSize.value.width || next.height !== captureSize.value.height) {
      captureSize.value = next;
    }
    return captureSize.value;
  }

  /**
   * Select one of the three capture presets from the UI.
   *
   * @param next - Preset chosen in the size select.
   * @returns The preset now in effect.
   */
  function setCapturePreset(next: CaptureSize): CaptureSize {
    const resolved = reduceCaptureSize(captureSize.value, next);
    if (resolved.width !== captureSize.value.width || resolved.height !== captureSize.value.height) {
      captureSize.value = resolved;
    }
    return captureSize.value;
  }

  /**
   * Mirror the last encoded JPEG dimensions for UI hints.
   *
   * @param size - Canvas size used for the latest frame header.
   */
  function setEncodedBitmapSize(size: CaptureSize): void {
    encodedBitmapSize.value = { width: size.width, height: size.height };
  }

  /**
   * Mirror lifecycle state from {@link PeerSession}.
   *
   * @param nextStatus - Current session status.
   * @param detail - Human-readable failure when applicable.
   */
  function syncFromPeer(nextStatus: SessionStatus, detail: string | null): void {
    status.value = nextStatus;
    statusDetail.value = detail;
    if (nextStatus !== 'idle') {
      idleMessage.value = null;
    }
  }

  /**
   * Replace side-panel content after overlay drawing.
   */
  function setPanelContent(texts: readonly Text[], metrics: readonly Metrics[]): void {
    panelTexts.value = texts;
    panelMetrics.value = metrics;
  }

  /**
   * Update live performance indicators shown under the video.
   */
  function setPerformanceIndicators(nextFps: number, nextLatencyMs: number | null): void {
    fps.value = Math.max(0, nextFps);
    latencyMs.value = nextLatencyMs;
  }

  return {
    status,
    statusDetail,
    idleMessage,
    peerId,
    facingMode,
    jpegQuality,
    panelTexts,
    panelMetrics,
    fps,
    latencyMs,
    captureSize,
    encodedBitmapSize,
    headline,
    configureFromHash,
    beginConnecting,
    applyWelcome,
    applyWelcomeSize,
    setCapturePreset,
    setEncodedBitmapSize,
    syncFromPeer,
    setPanelContent,
    setPerformanceIndicators,
  };
});