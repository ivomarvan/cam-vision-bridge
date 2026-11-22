import { describe, expect, it } from 'vitest';

import type { Box, Keypoints, Metrics, Point, Polygon, Polyline, Quad, Text } from '@/protocol/generated';

import { drawItems, type OverlayContext, type ResultItem } from './drawItems';
import { mapPoint, type Size } from './mapPoint';

const VIEW: Size = { width: 800, height: 480 };
const FRAME: Size = { width: 640, height: 480 };

interface RecordedCall {
  readonly method: string;
  readonly args: readonly unknown[];
}

class CallRecorder {
  readonly calls: RecordedCall[] = [];
  strokeStyle = '';
  fillStyle = '';
  lineWidth = 0;
  font = '';
  textBaseline: CanvasTextBaseline = 'alphabetic';

  beginPath(): void {
    this.#call('beginPath');
  }

  moveTo(x: number, y: number): void {
    this.#call('moveTo', x, y);
  }

  lineTo(x: number, y: number): void {
    this.#call('lineTo', x, y);
  }

  closePath(): void {
    this.#call('closePath');
  }

  stroke(): void {
    this.#call('stroke');
  }

  fillText(text: string, x: number, y: number): void {
    this.#call('fillText', text, x, y);
  }

  arc(x: number, y: number, radius: number, startAngle: number, endAngle: number): void {
    this.#call('arc', x, y, radius, startAngle, endAngle);
  }

  methods(): string[] {
    return this.calls.map((call) => call.method);
  }

  #call(method: string, ...args: unknown[]): void {
    this.calls.push({ method, args });
  }
}

function contextOf(recorder: CallRecorder): OverlayContext {
  return recorder;
}

function throwingContext(): OverlayContext {
  return new Proxy({} as OverlayContext, {
    get() {
      throw new Error('context was read');
    },
    set() {
      throw new Error('context was written');
    },
  });
}

function numberArg(call: RecordedCall, index: number): number {
  const value = call.args[index];
  if (typeof value !== 'number') {
    throw new Error(`expected a number argument at ${String(index)}`);
  }
  return value;
}

function callsNamed(recorder: CallRecorder, method: string): RecordedCall[] {
  return recorder.calls.filter((call) => call.method === method);
}

describe('drawItems', () => {
  it('mirrors a box on the front camera and leaves the rear camera unmirrored', () => {
    const box: Box = { t: 'box', x: 0.25, y: 0.5, w: 0.2, h: 0.1 };
    const rear = new CallRecorder();
    const front = new CallRecorder();

    drawItems(contextOf(rear), [box], VIEW, FRAME, false);
    drawItems(contextOf(front), [box], VIEW, FRAME, true);

    const rearMove = callsNamed(rear, 'moveTo')[0];
    const frontMove = callsNamed(front, 'moveTo')[0];
    if (rearMove === undefined || frontMove === undefined) {
      throw new Error('box did not move to its first corner');
    }
    const expectedRear = mapPoint({ x: box.x, y: box.y }, VIEW, FRAME, false);
    const expectedFront = mapPoint({ x: box.x, y: box.y }, VIEW, FRAME, true);

    expect({ x: numberArg(rearMove, 0), y: numberArg(rearMove, 1) }).toEqual(expectedRear);
    expect({ x: numberArg(frontMove, 0), y: numberArg(frontMove, 1) }).toEqual(expectedFront);
    expect(numberArg(frontMove, 0)).not.toBe(numberArg(rearMove, 0));
    expect(numberArg(frontMove, 1)).toBe(numberArg(rearMove, 1));
    expect(callsNamed(rear, 'stroke')).toHaveLength(1);
    expect(callsNamed(front, 'stroke')).toHaveLength(1);
  });

  it('does not throw or stroke when items is empty', () => {
    const recorder = new CallRecorder();

    expect(drawItems(throwingContext(), [], VIEW, FRAME, true)).toEqual({
      texts: [],
      metrics: [],
    });
    expect(drawItems(contextOf(recorder), [], VIEW, FRAME, false)).toEqual({
      texts: [],
      metrics: [],
    });
    expect(recorder.calls).toEqual([]);
    expect(callsNamed(recorder, 'stroke')).toEqual([]);
  });

  it('returns panel text and metrics without drawing them', () => {
    const panelText: Text = { t: 'text', text: 'scan the code' };
    const nullPoint: Text = { t: 'text', text: 'waiting', x: null, y: null };
    const halfPoint: Text = { t: 'text', text: 'orphan', x: 0.2, y: null };
    const metrics: Metrics = { t: 'metrics', metrics: [{ name: 'fps', value: 12 }] };

    const panel = drawItems(
      throwingContext(),
      [panelText, nullPoint, halfPoint, metrics],
      VIEW,
      FRAME,
      false,
    );

    expect(panel.texts).toEqual([panelText, nullPoint, halfPoint]);
    expect(panel.metrics).toEqual([metrics]);
  });

  it('projects quad, polygon, polyline, keypoints, and positioned text through mapPoint', () => {
    const origin: Point = { x: 0.1, y: 0.2 };
    const next: Point = { x: 0.4, y: 0.6 };
    const third: Point = { x: 0.5, y: 0.15 };
    const quad: Quad = { t: 'quad', points: [origin, next, third, { x: 0.2, y: 0.7 }] };
    const polygon: Polygon = { t: 'polygon', points: [origin, next, third] };
    const polyline: Polyline = { t: 'polyline', points: [origin, next] };
    const keypoints: Keypoints = { t: 'keypoints', points: [origin, next], edges: [[0, 1]] };
    const label: Text = { t: 'text', text: 'qr', x: origin.x, y: origin.y };
    const items: readonly ResultItem[] = [quad, polygon, polyline, keypoints, label];
    const recorder = new CallRecorder();
    const expected = mapPoint(origin, VIEW, FRAME, true);

    const panel = drawItems(contextOf(recorder), items, VIEW, FRAME, true);

    expect(panel).toEqual({ texts: [], metrics: [] });
    const moveTos = callsNamed(recorder, 'moveTo');
    expect(moveTos.some((call) => numberArg(call, 0) === expected.x && numberArg(call, 1) === expected.y)).toBe(
      true,
    );
    const lineTos = callsNamed(recorder, 'lineTo');
    const mappedNext = mapPoint(next, VIEW, FRAME, true);
    expect(
      lineTos.some((call) => numberArg(call, 0) === mappedNext.x && numberArg(call, 1) === mappedNext.y),
    ).toBe(true);
    expect(recorder.methods()).toContain('closePath');
    expect(recorder.methods().filter((method) => method === 'closePath').length).toBe(2);
    const textCall = callsNamed(recorder, 'fillText')[0];
    if (textCall === undefined) {
      throw new Error('positioned text was not drawn');
    }
    expect(textCall.args[0]).toBe('qr');
    expect(numberArg(textCall, 1)).toBe(expected.x);
    expect(numberArg(textCall, 2)).toBe(expected.y);
    expect(callsNamed(recorder, 'arc').length).toBeGreaterThan(0);
    expect(callsNamed(recorder, 'stroke').length).toBeGreaterThan(0);
  });

  it('skips a keypoint edge whose index is outside the point list', () => {
    const keypoints: Keypoints = {
      t: 'keypoints',
      points: [{ x: 0.2, y: 0.3 }],
      edges: [[0, 4]],
    };
    const recorder = new CallRecorder();

    expect(() => drawItems(contextOf(recorder), [keypoints], VIEW, FRAME, false)).not.toThrow();
    expect(callsNamed(recorder, 'lineTo')).toEqual([]);
    expect(callsNamed(recorder, 'arc')).toHaveLength(1);
    expect(callsNamed(recorder, 'stroke')).toHaveLength(1);
  });
});
