import { describe, expect, it } from 'vitest';

import { requestScreenWakeLock } from './screenWakeLock';

describe('requestScreenWakeLock', () => {
  it('returns unsupported when wake lock api is missing', async () => {
    await expect(requestScreenWakeLock({})).resolves.toBe('unsupported');
  });
});