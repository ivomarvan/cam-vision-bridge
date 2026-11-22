/**
 * Draw protocol v1 result geometry into a Canvas 2D context.
 *
 * Every vertex goes through `mapPoint`, so letterbox and front-camera mirroring
 * stay in one place. Text without a point, and every metrics item, are not
 * painted; they are returned for the side panel.
 */

import type {
  Box,
  Keypoints,
  Metrics,
  Point,
  Polygon,
  Polyline,
  Quad,
  Result,
  Text,
} from '@/protocol/generated';

import { mapPoint, type Size } from './mapPoint';

/** Cyan reads on both bright and dark camera frames. */
export const OVERLAY_STROKE_STYLE = '#00e5ff';

/** Device pixels. One stroke weight for every geometry kind. */
export const OVERLAY_LINE_WIDTH_PX = 2;

/** Device pixels. Positioned text sits on the mapped point. */
export const OVERLAY_FONT = '16px sans-serif';

/** Device pixels. Keypoint mark radius in view space, not frame space. */
export const KEYPOINT_RADIUS_PX = 4;

const CLOSED_MIN_POINTS = 3;
const OPEN_MIN_POINTS = 2;

/** One entry of `result.items`. */
export type ResultItem = Result['items'][number];

/**
 * Methods this module calls. A real `CanvasRenderingContext2D` satisfies it.
 * Tests pass a recorder with the same methods.
 */
export interface OverlayContext {
  strokeStyle: string | CanvasGradient | CanvasPattern;
  fillStyle: string | CanvasGradient | CanvasPattern;
  lineWidth: number;
  font: string;
  textBaseline: CanvasTextBaseline;
  beginPath(): void;
  moveTo(x: number, y: number): void;
  lineTo(x: number, y: number): void;
  closePath(): void;
  stroke(): void;
  fillText(text: string, x: number, y: number, maxWidth?: number): void;
  arc(
    x: number,
    y: number,
    radius: number,
    startAngle: number,
    endAngle: number,
    counterclockwise?: boolean,
  ): void;
}

/**
 * Items that belong in the T070 panel rather than on the video.
 */
export interface PanelItems {
  /** Text items that have no point. Positioned text is drawn and omitted here. */
  readonly texts: readonly Text[];
  /** Metrics items, in input order, including their `metrics` arrays. */
  readonly metrics: readonly Metrics[];
}

interface FrameMapping {
  readonly view: Size;
  readonly frame: Size;
  readonly mirrorX: boolean;
}

interface MappedPoint {
  readonly x: number;
  readonly y: number;
}

type Assert<T extends true> = T;

/**
 * Compile-time check that a live canvas context can be passed to {@link drawItems}.
 * The type is `true` only when `CanvasRenderingContext2D` implements {@link OverlayContext}.
 */
export type OverlayContextIsDomContext = Assert<
  CanvasRenderingContext2D extends OverlayContext ? true : false
>;

/**
 * Paint geometry for one result and split out panel-only items.
 *
 * Does not clear the canvas — the caller clears before each result. An empty
 * list does not touch the context. Labels and scores are not painted; they
 * stay on the item for a later panel.
 *
 * @param context - Overlay canvas context, or a test recorder with the same methods.
 * @param items - `result.items`. Each `t` selects the shape.
 * @param view - Overlay element size in CSS pixels.
 * @param frame - Sent frame size in pixels (the JPEG that was published).
 * @param mirrorX - `true` for the front camera. Flips x inside `mapPoint`.
 * @returns Text without coordinates, and metrics items, in input order.
 * @throws {Error} When `t` is outside the v1 union (a programming error).
 * @throws {RangeError} When `view` width or height is negative (`mapPoint`).
 */
export function drawItems(
  context: OverlayContext,
  items: readonly ResultItem[],
  view: Size,
  frame: Size,
  mirrorX: boolean,
): PanelItems {
  const texts: Text[] = [];
  const metrics: Metrics[] = [];
  const mapping: FrameMapping = { view, frame, mirrorX };
  for (const item of items) {
    routeItem(context, item, mapping, texts, metrics);
  }
  return { texts, metrics };
}

function routeItem(
  context: OverlayContext,
  item: ResultItem,
  mapping: FrameMapping,
  texts: Text[],
  metrics: Metrics[],
): void {
  switch (item.t) {
    case 'box':
      drawBox(context, item, mapping);
      return;
    case 'quad':
      drawClosed(context, item, mapping);
      return;
    case 'polygon':
      drawClosed(context, item, mapping);
      return;
    case 'polyline':
      drawOpen(context, item, mapping);
      return;
    case 'keypoints':
      drawKeypoints(context, item, mapping);
      return;
    case 'text':
      if (!drawText(context, item, mapping)) {
        texts.push(item);
      }
      return;
    case 'metrics':
      metrics.push(item);
      return;
    default: {
      const unreachable: never = item;
      throw new Error(`Unhandled result item: ${JSON.stringify(unreachable)}`);
    }
  }
}

function drawBox(context: OverlayContext, item: Box, mapping: FrameMapping): void {
  // Both corners go through mapPoint so mirror and letterbox stay consistent.
  const corners: readonly Point[] = [
    { x: item.x, y: item.y },
    { x: item.x + item.w, y: item.y },
    { x: item.x + item.w, y: item.y + item.h },
    { x: item.x, y: item.y + item.h },
  ];
  strokeShape(context, projectAll(corners, mapping), true);
}

function drawClosed(
  context: OverlayContext,
  item: Quad | Polygon,
  mapping: FrameMapping,
): void {
  strokeShape(context, projectAll(item.points, mapping), true);
}

function drawOpen(context: OverlayContext, item: Polyline, mapping: FrameMapping): void {
  strokeShape(context, projectAll(item.points, mapping), false);
}

function drawKeypoints(context: OverlayContext, item: Keypoints, mapping: FrameMapping): void {
  const mapped = projectAll(item.points, mapping);
  strokeSegments(context, segmentsFor(mapped, item.edges));
  strokeMarks(context, mapped);
}

function drawText(context: OverlayContext, item: Text, mapping: FrameMapping): boolean {
  const x = item.x;
  const y = item.y;
  // One coordinate is neither a panel line nor a point. Treat it as panel text.
  if (typeof x !== 'number' || typeof y !== 'number') {
    return false;
  }
  const point = project({ x, y }, mapping);
  applyStyle(context);
  context.fillText(item.text, point.x, point.y);
  return true;
}

function projectAll(points: readonly Point[], mapping: FrameMapping): readonly MappedPoint[] {
  return points.map((point) => project(point, mapping));
}

function project(point: Point, mapping: FrameMapping): MappedPoint {
  return mapPoint(point, mapping.view, mapping.frame, mapping.mirrorX);
}

function strokeShape(
  context: OverlayContext,
  points: readonly MappedPoint[],
  close: boolean,
): void {
  const minimum = close ? CLOSED_MIN_POINTS : OPEN_MIN_POINTS;
  const origin = points[0];
  if (origin === undefined || points.length < minimum) {
    return;
  }
  applyStyle(context);
  context.beginPath();
  context.moveTo(origin.x, origin.y);
  for (let index = 1; index < points.length; index += 1) {
    const point = points[index];
    if (point === undefined) {
      return;
    }
    context.lineTo(point.x, point.y);
  }
  if (close) {
    context.closePath();
  }
  context.stroke();
}

function segmentsFor(
  points: readonly MappedPoint[],
  edges: Keypoints['edges'],
): readonly (readonly [MappedPoint, MappedPoint])[] {
  const segments: (readonly [MappedPoint, MappedPoint])[] = [];
  for (const edge of edges ?? []) {
    const start = pointAt(points, edge[0]);
    const end = pointAt(points, edge[1]);
    if (start === undefined || end === undefined) {
      continue;
    }
    segments.push([start, end]);
  }
  return segments;
}

function pointAt(points: readonly MappedPoint[], index: number): MappedPoint | undefined {
  // A bad index must not throw: one edge should not drop the rest of the frame.
  if (!Number.isInteger(index) || index < 0 || index >= points.length) {
    return undefined;
  }
  return points[index];
}

function strokeSegments(
  context: OverlayContext,
  segments: readonly (readonly [MappedPoint, MappedPoint])[],
): void {
  const first = segments[0];
  if (first === undefined) {
    return;
  }
  applyStyle(context);
  context.beginPath();
  for (const [start, end] of segments) {
    context.moveTo(start.x, start.y);
    context.lineTo(end.x, end.y);
  }
  context.stroke();
}

function strokeMarks(context: OverlayContext, points: readonly MappedPoint[]): void {
  const first = points[0];
  if (first === undefined) {
    return;
  }
  applyStyle(context);
  context.beginPath();
  for (const point of points) {
    // moveTo starts a new subpath so circles are not joined by a straight line.
    context.moveTo(point.x + KEYPOINT_RADIUS_PX, point.y);
    context.arc(point.x, point.y, KEYPOINT_RADIUS_PX, 0, Math.PI * 2);
  }
  context.stroke();
}

function applyStyle(context: OverlayContext): void {
  context.strokeStyle = OVERLAY_STROKE_STYLE;
  context.fillStyle = OVERLAY_STROKE_STYLE;
  context.lineWidth = OVERLAY_LINE_WIDTH_PX;
  context.font = OVERLAY_FONT;
  context.textBaseline = 'bottom';
}
