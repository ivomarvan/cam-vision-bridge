import { describe, expect, it } from 'vitest';

import {
  CAPTURE_PRESETS,
  DEFAULT_CAPTURE_SIZE,
  bitmapSize,
  helloBitmap,
  nearestPreset,
  presetAfterWelcome,
  sizeFromWelcome,
} from './captureSize';

describe('captureSize', () => {
  it('lists only the three presets and defaults to the first', () => {
    expect(CAPTURE_PRESETS).toEqual([
      { width: 640, height: 480 },
      { width: 1280, height: 720 },
      { width: 1920, height: 1080 },
    ]);
    expect(DEFAULT_CAPTURE_SIZE).toEqual({ width: 640, height: 480 });
    expect(CAPTURE_PRESETS[0]).toEqual(DEFAULT_CAPTURE_SIZE);
  });

  it('maps 1280×720 onto that preset', () => {
    expect(nearestPreset(1280, 720)).toEqual({ width: 1280, height: 720 });
  });

  it('maps 1000×700 onto the closer pixel count', () => {
    expect(nearestPreset(1000, 700)).toEqual({ width: 1280, height: 720 });
  });

  it('keeps the smaller preset when pixel-count distances tie', () => {
    expect(nearestPreset(960, 640)).toEqual({ width: 640, height: 480 });
  });

  it('returns null from welcome when only one dimension is present', () => {
    expect(sizeFromWelcome(1280, undefined)).toBeNull();
    expect(sizeFromWelcome(undefined, 720)).toBeNull();
    expect(sizeFromWelcome(1280, null)).toBeNull();
    expect(sizeFromWelcome(null, 720)).toBeNull();
    expect(sizeFromWelcome(null, null)).toBeNull();
  });

  it('keeps the current preset when welcome is incomplete and changes it when both dimensions arrive', () => {
    const current = DEFAULT_CAPTURE_SIZE;
    expect(presetAfterWelcome(current, 1920, undefined)).toBe(current);
    expect(presetAfterWelcome(current, undefined, 1080)).toBe(current);
    expect(presetAfterWelcome(current, 1000, 700)).toEqual({ width: 1280, height: 720 });
  });

  it('keeps a 1280×720 video and scales 3840×2160 down to 1920×1080', () => {
    const preset = DEFAULT_CAPTURE_SIZE;
    expect(bitmapSize(1280, 720, preset)).toEqual({ width: 1280, height: 720 });
    expect(bitmapSize(3840, 2160, preset)).toEqual({ width: 1920, height: 1080 });
  });

  it('rounds scaled sides to integers of at least 1', () => {
    expect(bitmapSize(4000, 1, DEFAULT_CAPTURE_SIZE)).toEqual({ width: 1920, height: 1 });
  });

  it('throws RangeError when the video width is 0', () => {
    expect(() => bitmapSize(0, 720, DEFAULT_CAPTURE_SIZE)).toThrow(RangeError);
  });

  it('uses the preset for hello until the video has a positive size', () => {
    expect(helloBitmap(0, 0, DEFAULT_CAPTURE_SIZE)).toEqual(DEFAULT_CAPTURE_SIZE);
    expect(helloBitmap(3840, 2160, DEFAULT_CAPTURE_SIZE)).toEqual({ width: 1920, height: 1080 });
  });
});
