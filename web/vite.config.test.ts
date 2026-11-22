import path from 'node:path';

import { loadConfigFromFile } from 'vite';
import { describe, expect, it } from 'vitest';

import { APP_BASE } from './deploy-path';

describe('deploy path', () => {
  it('sets base URL for GitHub Pages deploy path', () => {
    expect(APP_BASE).toBe('/cam-vision-bridge/v1/');
  });
});

describe('import.meta.env', () => {
  it('BASE_URL starts with /cam-vision-bridge/', async () => {
    const loaded = await loadConfigFromFile(
      { command: 'build', mode: 'production' },
      path.resolve(process.cwd(), 'vite.config.ts'),
    );
    expect(loaded).not.toBeNull();
    const base = loaded?.config.base;
    expect(base).toMatch(/^\/cam-vision-bridge\//);
    expect(base).toBe(APP_BASE);
  });
});