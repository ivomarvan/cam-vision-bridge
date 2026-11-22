/** Result of trying to keep the screen awake during capture. */
export type WakeLockSupport = 'active' | 'released' | 'unsupported';

/**
 * Minimal `navigator.wakeLock` surface used by the app.
 */
export interface WakeLockNavigator {
  readonly wakeLock?: {
    request(type: 'screen'): Promise<{ release(): Promise<void> }>;
  };
}

/**
 * Request a screen wake lock when the API exists.
 *
 * Missing API or a rejected request maps to `unsupported` without throwing.
 *
 * @param navigatorLike - Usually `navigator`; tests pass a stub.
 * @returns Whether the lock is active or unsupported.
 */
export async function requestScreenWakeLock(
  navigatorLike: WakeLockNavigator,
): Promise<WakeLockSupport> {
  const api = navigatorLike.wakeLock;
  if (api === undefined) {
    return 'unsupported';
  }
  try {
    await api.request('screen');
    return 'active';
  } catch {
    return 'unsupported';
  }
}