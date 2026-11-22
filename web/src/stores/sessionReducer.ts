import { CAPTURE_PRESETS, type CaptureSize } from '@/camera/captureSize';
import type { SessionStatus } from '@/session/peerSession';
import { peerIdFromHash } from '@/utils/peer-id-from-hash';

/** Shown when the URL hash has no `peer` parameter. */
export const IDLE_MESSAGE_NO_PEER =
  'Add a peer id to the URL hash, for example #peer=your-pc-peer-id.';

/**
 * Next connection status after a `welcome` message with the given protocol version.
 *
 * @param protocolVersion - `welcome.v` from the PC peer.
 * @returns Status and optional detail string for the UI.
 */
export function reduceWelcome(protocolVersion: number): {
  readonly status: SessionStatus;
  readonly statusDetail: string | null;
} {
  if (protocolVersion === 1) {
    return { status: 'open', statusDetail: null };
  }
  if (!Number.isFinite(protocolVersion)) {
    return {
      status: 'version-mismatch',
      statusDetail: 'Protocol version is not supported; this phone speaks v1',
    };
  }
  return {
    status: 'version-mismatch',
    statusDetail: `Protocol version ${String(protocolVersion)} is not supported; this phone speaks v1`,
  };
}

/**
 * Whether a hash fragment contains a peer id to dial.
 *
 * @param hash - `window.location.hash` or equivalent.
 * @returns Parsed peer id, or `null` when missing.
 */
export function peerIdFromHashFragment(hash: string): string | null {
  return peerIdFromHash(hash);
}

function isKnownPreset(size: CaptureSize): boolean {
  return CAPTURE_PRESETS.some(
    (preset) => preset.width === size.width && preset.height === size.height,
  );
}

/**
 * Apply a UI or programmatic preset change.
 *
 * Unknown widths and heights are rejected and `current` is returned unchanged.
 *
 * @param current - Preset already selected in the store.
 * @param next - Candidate preset from the size select or a test.
 * @returns `next` when it matches a preset, otherwise `current`.
 */
/** Detail shown when the camera cannot be opened during an active pairing. */
export const CAMERA_OPEN_FAILED = 'Camera permission or device failed';

/**
 * Decide whether a camera-open failure replaces the connection status.
 *
 * A missing peer id must stay `idle` with the pairing hint. The failure is a
 * connection error only after the page is already dialing a peer.
 *
 * @param peerId - Peer id from the URL hash, or `null` when it is absent.
 * @returns The error status to apply, or `null` to leave the store unchanged.
 */
export function statusAfterCameraFailure(peerId: string | null): {
  readonly status: SessionStatus;
  readonly statusDetail: string;
} | null {
  if (peerId === null) {
    return null;
  }
  return { status: 'error', statusDetail: CAMERA_OPEN_FAILED };
}

export function reduceCaptureSize(current: CaptureSize, next: CaptureSize): CaptureSize {
  if (!isKnownPreset(next)) {
    return current;
  }
  return { width: next.width, height: next.height };
}