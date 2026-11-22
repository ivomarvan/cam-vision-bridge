import { describe, expect, it } from 'vitest';

import { mapPoint } from './mapPoint';

const FRAME = { width: 640, height: 480 };

describe('mapPoint', () => {
  it('maps center to center when view matches frame size', () => {
    const view = { width: 640, height: 480 };
    expect(mapPoint({ x: 0.5, y: 0.5 }, view, FRAME, false)).toEqual({
      x: 320,
      y: 240,
    });
  });

  it('places horizontal letterbox points on the image edge, not the element edge', () => {
    const view = { width: 800, height: 480 };
    expect(mapPoint({ x: 0, y: 0.5 }, view, FRAME, false)).toEqual({
      x: 80,
      y: 240,
    });
    expect(mapPoint({ x: 1, y: 0.5 }, view, FRAME, false)).toEqual({
      x: 720,
      y: 240,
    });
  });

  it('mirrors x about the image center when mirrorX is true', () => {
    const view = { width: 640, height: 480 };
    expect(mapPoint({ x: 0.25, y: 0.5 }, view, FRAME, true)).toEqual({
      x: 480,
      y: 240,
    });
    expect(mapPoint({ x: 0.75, y: 0.5 }, view, FRAME, false)).toEqual({
      x: 480,
      y: 240,
    });
  });

  it('does not clamp normalized coordinates outside 0..1', () => {
    const view = { width: 640, height: 480 };
    expect(mapPoint({ x: -0.1, y: 1.2 }, view, FRAME, false)).toEqual({
      x: -64,
      y: 576,
    });
  });

  it('throws RangeError when view width or height is negative', () => {
    expect(() =>
      mapPoint({ x: 0.5, y: 0.5 }, { width: -1, height: 480 }, FRAME, false),
    ).toThrow(RangeError);
    expect(() =>
      mapPoint({ x: 0.5, y: 0.5 }, { width: 640, height: -1 }, FRAME, false),
    ).toThrow(RangeError);
  });
});