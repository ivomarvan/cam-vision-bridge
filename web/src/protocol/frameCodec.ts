/**
 * Binary frame codec for protocol v1, matching `cam_vision_bridge.protocol.frame_codec`.
 *
 * One data-channel message is uint32 big-endian header length, UTF-8 JSON
 * `FrameHeader`, then the JPEG bytes of that part. JSON object key order is part
 * of the wire image: Python `json.dumps` follows the model field order.
 */

import type {
  Box,
  CamVisionBridgeV1TextMessage,
  ErrorMessage,
  FrameHeader,
  Hello,
  Keypoints,
  Metric,
  Metrics,
  Point,
  Polygon,
  Polyline,
  Quad,
  Result,
  Text,
  Welcome,
} from './generated';

/** Default JPEG part size. Frames larger than this are split. */
export const DEFAULT_CHUNK_BYTES = 16_384;

/** Maximum UTF-8 header size accepted by the Python codec. */
const HEADER_LEN_MAX = 4096;

const PARTS_MIN = 1;
const PARTS_MAX = 256;

/** 8 MiB, the same ceiling as the Python codec. */
const TOTAL_BYTES_MAX = 8 * 1024 * 1024;

const LENGTH_PREFIX_BYTES = 4;

const TEXT_TAGS = ['hello', 'welcome', 'error', 'frame', 'result'] as const;
type TextTag = (typeof TEXT_TAGS)[number];

const ITEM_TAGS = ['box', 'quad', 'polygon', 'keypoints', 'polyline', 'text', 'metrics'] as const;
type ItemTag = (typeof ITEM_TAGS)[number];

const QUAD_POINT_COUNT = 4;
const POLYGON_MIN_POINTS = 3;
const POLYLINE_MIN_POINTS = 2;

const HELLO_KEYS = new Set(['v', 't', 'device_ua', 'camera', 'width', 'height']);
const WELCOME_KEYS = new Set(['v', 't', 'width', 'height', 'fps']);
const ERROR_KEYS = new Set(['v', 't', 'reason', 'frame_id']);
const FRAME_KEYS = new Set([
  'v',
  't',
  'frame_id',
  'captured_at',
  'w',
  'h',
  'part',
  'parts',
  'total_bytes',
]);
const RESULT_KEYS = new Set(['v', 't', 'frame_id', 'items', 'processing_ms']);
const POINT_KEYS = new Set(['x', 'y']);
const BOX_KEYS = new Set(['t', 'x', 'y', 'w', 'h', 'label', 'score']);
const QUAD_KEYS = new Set(['t', 'points', 'label', 'score']);
const POLYGON_KEYS = new Set(['t', 'points', 'label', 'score']);
const KEYPOINTS_KEYS = new Set(['t', 'points', 'edges', 'label', 'score']);
const POLYLINE_KEYS = new Set(['t', 'points', 'label', 'score']);
const TEXT_KEYS = new Set(['t', 'text', 'x', 'y']);
const METRICS_KEYS = new Set(['t', 'metrics']);
const METRIC_KEYS = new Set(['name', 'value']);

/**
 * A binary chunk or a text message broke a protocol v1 rule.
 *
 * `reason` is a stable code. `frameId` is set when the header already named a frame.
 */
export class FrameProtocolError extends Error {
  override readonly name = 'FrameProtocolError';
  readonly reason: string;
  readonly frameId: number | undefined;

  /**
   * @param reason - Stable cause code. Also the `Error` message.
   * @param frameId - Frame the failure belongs to, when one is known.
   */
  constructor(reason: string, frameId?: number) {
    // The app tsconfig Error constructor accepts only a message (no `cause` options).
    super(reason);
    this.reason = reason;
    this.frameId = frameId;
  }
}

/**
 * Fields needed to split one JPEG into packed chunks.
 */
export interface SplitFrameInput {
  /** Frame counter carried in every chunk header. */
  readonly frameId: number;
  /** Capture timestamp carried in every chunk header. */
  readonly capturedAt: string;
  /** Frame width in pixels. */
  readonly w: number;
  /** Frame height in pixels. */
  readonly h: number;
  /** Complete JPEG bytes. Not decoded. */
  readonly jpeg: Uint8Array;
  /**
   * Maximum payload size of one part.
   * `0` sends the JPEG as a single part. Defaults to {@link DEFAULT_CHUNK_BYTES}.
   */
  readonly chunkBytes?: number;
}

/**
 * Serialize one frame chunk into the length-prefixed wire layout.
 *
 * @param header - Chunk metadata. Numeric codec limits are applied here.
 * @param payload - JPEG bytes of this part only.
 * @returns The length-prefixed message, ready to send. Its buffer is exactly the message.
 * @throws FrameProtocolError - If the header or this payload breaks a codec limit.
 */
export function packChunk(header: FrameHeader, payload: Uint8Array): Uint8Array {
  assertPackableHeader(header);
  if (payload.byteLength > header.total_bytes) {
    throw new FrameProtocolError('payload_sum', header.frame_id);
  }
  const body = encodeHeader(header);
  if (body.byteLength > HEADER_LEN_MAX) {
    throw new FrameProtocolError('header_too_long', header.frame_id);
  }
  return concatChunk(body, payload);
}

/**
 * Split one JPEG into packed chunks.
 *
 * A length that is an exact multiple of `chunkBytes` does not add an empty trailing
 * part. `chunkBytes` of 0 keeps a single part, including when the JPEG is empty.
 *
 * @param input - Frame identity, pixel size, JPEG bytes, and optional part size.
 * @returns Packed wire messages, part 0 first.
 * @throws RangeError - If `chunkBytes` is not an integer greater than or equal to 0.
 * @throws FrameProtocolError - If the resulting header or part count breaks a limit.
 */
export function splitFrame(input: SplitFrameInput): Uint8Array[] {
  const chunkBytes = input.chunkBytes ?? DEFAULT_CHUNK_BYTES;
  if (!Number.isInteger(chunkBytes) || chunkBytes < 0) {
    throw new RangeError('chunkBytes must be an integer >= 0');
  }
  const slices = jpegSlices(input.jpeg, chunkBytes);
  const parts = slices.length;
  const totalBytes = input.jpeg.byteLength;
  return slices.map((payload, part) =>
    packChunk(frameHeaderForPart(input, part, parts, totalBytes), payload),
  );
}

/**
 * Parse one JSON text message from the PC or the phone.
 *
 * `t` must be a known protocol tag and `v` must be 1. Result items are checked
 * against the same shapes as the generated types. Unknown object keys are rejected.
 *
 * @param text - UTF-8 JSON object already decoded to a string. Treated as untrusted.
 * @returns The message selected by `t`.
 * @throws FrameProtocolError - If the JSON is invalid, `t` is missing or unknown, or `v` is not 1.
 */
export function parseServerMessage(text: string): CamVisionBridgeV1TextMessage {
  const record = parseJsonObject(text);
  const tag = readTextTag(record);
  if (record.v !== 1) {
    throw new FrameProtocolError('unsupported_version');
  }
  return parseKnownMessage(tag, record);
}

function assertPackableHeader(header: FrameHeader): void {
  if (!Number.isInteger(header.frame_id) || header.frame_id < 0) {
    throw new FrameProtocolError('invalid_header');
  }
  if (!Number.isInteger(header.w) || header.w < 1 || !Number.isInteger(header.h) || header.h < 1) {
    throw new FrameProtocolError('invalid_header', header.frame_id);
  }
  enforceChunkLimits(header);
}

function enforceChunkLimits(header: FrameHeader): void {
  if (!Number.isInteger(header.parts) || header.parts < PARTS_MIN || header.parts > PARTS_MAX) {
    throw new FrameProtocolError('parts_out_of_range', header.frame_id);
  }
  if (!Number.isInteger(header.part) || header.part < 0 || header.part >= header.parts) {
    throw new FrameProtocolError('part_out_of_range', header.frame_id);
  }
  if (
    !Number.isInteger(header.total_bytes) ||
    header.total_bytes < 0 ||
    header.total_bytes > TOTAL_BYTES_MAX
  ) {
    throw new FrameProtocolError('total_bytes_out_of_range', header.frame_id);
  }
}

/**
 * Emit header keys in model order. Callers may build `FrameHeader` in any order.
 */
function encodeHeader(header: FrameHeader): Uint8Array {
  const document = {
    v: header.v,
    t: header.t,
    frame_id: header.frame_id,
    captured_at: header.captured_at,
    w: header.w,
    h: header.h,
    part: header.part,
    parts: header.parts,
    total_bytes: header.total_bytes,
  };
  return new TextEncoder().encode(JSON.stringify(document));
}

function concatChunk(body: Uint8Array, payload: Uint8Array): Uint8Array {
  const message = new Uint8Array(LENGTH_PREFIX_BYTES + body.byteLength + payload.byteLength);
  const view = new DataView(message.buffer);
  view.setUint32(0, body.byteLength, false);
  message.set(body, LENGTH_PREFIX_BYTES);
  message.set(payload, LENGTH_PREFIX_BYTES + body.byteLength);
  return message;
}

function frameHeaderForPart(
  input: SplitFrameInput,
  part: number,
  parts: number,
  totalBytes: number,
): FrameHeader {
  return {
    v: 1,
    t: 'frame',
    frame_id: input.frameId,
    captured_at: input.capturedAt,
    w: input.w,
    h: input.h,
    part,
    parts,
    total_bytes: totalBytes,
  };
}

/**
 * `chunkBytes === 0` or an empty JPEG stays one part, so the wire always has a header.
 */
function jpegSlices(jpeg: Uint8Array, chunkBytes: number): Uint8Array[] {
  if (chunkBytes === 0 || jpeg.byteLength === 0) {
    return [jpeg];
  }
  const slices: Uint8Array[] = [];
  for (let start = 0; start < jpeg.byteLength; start += chunkBytes) {
    slices.push(jpeg.subarray(start, start + chunkBytes));
  }
  return slices;
}

function parseJsonObject(text: string): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new FrameProtocolError('invalid_json');
  }
  if (!isRecord(parsed)) {
    throw new FrameProtocolError('invalid_json');
  }
  return parsed;
}

function parseKnownMessage(
  tag: TextTag,
  record: Record<string, unknown>,
): CamVisionBridgeV1TextMessage {
  switch (tag) {
    case 'hello':
      return parseHello(record);
    case 'welcome':
      return parseWelcome(record);
    case 'error':
      return parseError(record);
    case 'frame':
      return parseFrameHeader(record);
    case 'result':
      return parseResult(record);
    default:
      return unexpectedTag(tag);
  }
}

function unexpectedTag(tag: never): never {
  throw new FrameProtocolError(`unknown_type:${JSON.stringify(tag)}`);
}

function parseHello(record: Record<string, unknown>): Hello {
  assertKeys(record, HELLO_KEYS);
  const message: {
    v: 1;
    t: 'hello';
    device_ua: string;
    camera?: 'user' | 'environment' | null;
    width: number;
    height: number;
  } = {
    v: 1,
    t: 'hello',
    device_ua: readString(record, 'device_ua'),
    width: readPositiveInt(record, 'width'),
    height: readPositiveInt(record, 'height'),
  };
  const camera = readCamera(record);
  if (camera !== undefined) {
    message.camera = camera;
  }
  return message;
}

function parseWelcome(record: Record<string, unknown>): Welcome {
  assertKeys(record, WELCOME_KEYS);
  const message: {
    v: 1;
    t: 'welcome';
    width?: number | null;
    height?: number | null;
    fps?: number | null;
  } = { v: 1, t: 'welcome' };
  assignOptionalInt(message, 'width', readOptionalNullableInt(record, 'width'));
  assignOptionalInt(message, 'height', readOptionalNullableInt(record, 'height'));
  assignOptionalInt(message, 'fps', readOptionalNullableInt(record, 'fps', 1));
  return message;
}

function parseError(record: Record<string, unknown>): ErrorMessage {
  assertKeys(record, ERROR_KEYS);
  const message: {
    v: 1;
    t: 'error';
    reason: string;
    frame_id?: number | null;
  } = {
    v: 1,
    t: 'error',
    reason: readString(record, 'reason'),
  };
  const frameId = readOptionalNullableInt(record, 'frame_id', 0);
  if (frameId !== undefined) {
    message.frame_id = frameId;
  }
  return message;
}

function parseFrameHeader(record: Record<string, unknown>): FrameHeader {
  assertKeys(record, FRAME_KEYS);
  return {
    v: 1,
    t: 'frame',
    frame_id: readNonNegativeInt(record, 'frame_id'),
    captured_at: readString(record, 'captured_at'),
    w: readPositiveInt(record, 'w'),
    h: readPositiveInt(record, 'h'),
    part: readInteger(record, 'part'),
    parts: readInteger(record, 'parts'),
    total_bytes: readInteger(record, 'total_bytes'),
  };
}

function parseResult(record: Record<string, unknown>): Result {
  assertKeys(record, RESULT_KEYS);
  return {
    v: 1,
    t: 'result',
    frame_id: readNonNegativeInt(record, 'frame_id'),
    items: readUnknownArray(record.items).map((item) => parseResultItem(item)),
    processing_ms: readNonNegativeNumber(record, 'processing_ms'),
  };
}

function parseResultItem(
  value: unknown,
): Box | Quad | Polygon | Keypoints | Polyline | Text | Metrics {
  if (!isRecord(value)) {
    throw new FrameProtocolError('invalid_message');
  }
  const tag = readItemTag(value);
  switch (tag) {
    case 'box':
      return parseBox(value);
    case 'quad':
      return parseQuad(value);
    case 'polygon':
      return parsePolygon(value);
    case 'keypoints':
      return parseKeypoints(value);
    case 'polyline':
      return parsePolyline(value);
    case 'text':
      return parseText(value);
    case 'metrics':
      return parseMetrics(value);
    default:
      return unexpectedTag(tag);
  }
}

function parseBox(record: Record<string, unknown>): Box {
  assertKeys(record, BOX_KEYS);
  return {
    t: 'box',
    x: readUnit(record, 'x'),
    y: readUnit(record, 'y'),
    w: readUnit(record, 'w'),
    h: readUnit(record, 'h'),
    ...annotationFields(record),
  };
}

function parseQuad(record: Record<string, unknown>): Quad {
  assertKeys(record, QUAD_KEYS);
  return {
    t: 'quad',
    points: asQuadPoints(readPointList(record.points, QUAD_POINT_COUNT, QUAD_POINT_COUNT)),
    ...annotationFields(record),
  };
}

function parsePolygon(record: Record<string, unknown>): Polygon {
  assertKeys(record, POLYGON_KEYS);
  return {
    t: 'polygon',
    points: asPolygonPoints(readPointList(record.points, POLYGON_MIN_POINTS)),
    ...annotationFields(record),
  };
}

function parseKeypoints(record: Record<string, unknown>): Keypoints {
  assertKeys(record, KEYPOINTS_KEYS);
  const message: {
    t: 'keypoints';
    points: readonly Point[];
    edges?: readonly (readonly [number, number])[] | null;
    label?: string | null;
    score?: number | null;
  } = {
    t: 'keypoints',
    points: readPointList(record.points, 0),
    ...annotationFields(record),
  };
  const edges = readEdges(record);
  if (edges !== undefined) {
    message.edges = edges;
  }
  return message;
}

function parsePolyline(record: Record<string, unknown>): Polyline {
  assertKeys(record, POLYLINE_KEYS);
  return {
    t: 'polyline',
    points: asPolylinePoints(readPointList(record.points, POLYLINE_MIN_POINTS)),
    ...annotationFields(record),
  };
}

function parseText(record: Record<string, unknown>): Text {
  assertKeys(record, TEXT_KEYS);
  return {
    t: 'text',
    text: readString(record, 'text'),
    ...textCoordinates(record),
  };
}

function parseMetrics(record: Record<string, unknown>): Metrics {
  assertKeys(record, METRICS_KEYS);
  return {
    t: 'metrics',
    metrics: readUnknownArray(record.metrics).map((item) => readMetric(item)),
  };
}

function annotationFields(record: Record<string, unknown>): {
  label?: string | null;
  score?: number | null;
} {
  const fields: { label?: string | null; score?: number | null } = {};
  if (hasOwn(record, 'label')) {
    fields.label = readNullableString(record, 'label');
  }
  if (hasOwn(record, 'score')) {
    fields.score = readNullableFinite(record, 'score');
  }
  return fields;
}

function textCoordinates(record: Record<string, unknown>): { x?: number | null; y?: number | null } {
  const hasX = hasOwn(record, 'x');
  const hasY = hasOwn(record, 'y');
  if (hasX !== hasY) {
    throw new FrameProtocolError('invalid_message');
  }
  if (!hasX) {
    return {};
  }
  const x = readNullableUnit(record, 'x');
  const y = readNullableUnit(record, 'y');
  if ((x === null) !== (y === null)) {
    throw new FrameProtocolError('invalid_message');
  }
  return { x, y };
}

function readEdges(
  record: Record<string, unknown>,
): readonly (readonly [number, number])[] | null | undefined {
  if (!hasOwn(record, 'edges')) {
    return undefined;
  }
  const value = record.edges;
  if (value === null) {
    return null;
  }
  return readUnknownArray(value).map((edge) => readEdge(edge));
}

function readEdge(value: unknown): readonly [number, number] {
  const pair = readUnknownArray(value);
  if (pair.length !== 2) {
    throw new FrameProtocolError('invalid_message');
  }
  const first = pair[0];
  const second = pair[1];
  if (!isNonNegativeInteger(first) || !isNonNegativeInteger(second)) {
    throw new FrameProtocolError('invalid_message');
  }
  return [first, second];
}

function readPointList(value: unknown, min: number, max?: number): Point[] {
  const points = readUnknownArray(value);
  if (points.length < min || (max !== undefined && points.length > max)) {
    throw new FrameProtocolError('invalid_message');
  }
  return points.map((item) => readPoint(item));
}

function readPoint(value: unknown): Point {
  if (!isRecord(value)) {
    throw new FrameProtocolError('invalid_message');
  }
  assertKeys(value, POINT_KEYS);
  return { x: readUnit(value, 'x'), y: readUnit(value, 'y') };
}

function readMetric(value: unknown): Metric {
  if (!isRecord(value)) {
    throw new FrameProtocolError('invalid_message');
  }
  assertKeys(value, METRIC_KEYS);
  return { name: readString(value, 'name'), value: readFinite(value, 'value') };
}

function asQuadPoints(points: readonly Point[]): [Point, Point, Point, Point] {
  return [
    definedPoint(points[0]),
    definedPoint(points[1]),
    definedPoint(points[2]),
    definedPoint(points[3]),
  ];
}

function asPolygonPoints(points: readonly Point[]): [Point, Point, Point, ...Point[]] {
  return [definedPoint(points[0]), definedPoint(points[1]), definedPoint(points[2]), ...points.slice(3)];
}

function asPolylinePoints(points: readonly Point[]): [Point, Point, ...Point[]] {
  return [definedPoint(points[0]), definedPoint(points[1]), ...points.slice(2)];
}

function definedPoint(point: Point | undefined): Point {
  if (point === undefined) {
    throw new FrameProtocolError('invalid_message');
  }
  return point;
}

function readCamera(record: Record<string, unknown>): 'user' | 'environment' | null | undefined {
  if (!hasOwn(record, 'camera')) {
    return undefined;
  }
  const value = record.camera;
  if (value === null || value === 'user' || value === 'environment') {
    return value;
  }
  throw new FrameProtocolError('invalid_message');
}

function assignOptionalInt(
  message: { width?: number | null; height?: number | null; fps?: number | null },
  key: 'width' | 'height' | 'fps',
  value: number | null | undefined,
): void {
  if (value !== undefined) {
    message[key] = value;
  }
}

function readTextTag(record: Record<string, unknown>): TextTag {
  const tag = record.t;
  if (typeof tag !== 'string' || !isTextTag(tag)) {
    throw new FrameProtocolError('unknown_type');
  }
  return tag;
}

function readItemTag(record: Record<string, unknown>): ItemTag {
  const tag = record.t;
  if (typeof tag !== 'string' || !isItemTag(tag)) {
    throw new FrameProtocolError('invalid_message');
  }
  return tag;
}

function isTextTag(value: string): value is TextTag {
  return TEXT_TAGS.some((tag) => tag === value);
}

function isItemTag(value: string): value is ItemTag {
  return ITEM_TAGS.some((tag) => tag === value);
}

function assertKeys(record: Record<string, unknown>, allowed: ReadonlySet<string>): void {
  for (const key of Object.keys(record)) {
    if (!allowed.has(key)) {
      throw new FrameProtocolError('invalid_message');
    }
  }
}

function readRequired(record: Record<string, unknown>, key: string): unknown {
  if (!hasOwn(record, key)) {
    throw new FrameProtocolError('invalid_message');
  }
  return record[key];
}

function readString(record: Record<string, unknown>, key: string): string {
  const value = readRequired(record, key);
  if (typeof value !== 'string') {
    throw new FrameProtocolError('invalid_message');
  }
  return value;
}

function readNullableString(record: Record<string, unknown>, key: string): string | null {
  const value = readRequired(record, key);
  if (typeof value === 'string' || value === null) {
    return value;
  }
  throw new FrameProtocolError('invalid_message');
}

function readInteger(record: Record<string, unknown>, key: string): number {
  const value = readRequired(record, key);
  if (!isInteger(value)) {
    throw new FrameProtocolError('invalid_message');
  }
  return value;
}

function readNonNegativeInt(record: Record<string, unknown>, key: string): number {
  const value = readInteger(record, key);
  if (value < 0) {
    throw new FrameProtocolError('invalid_message');
  }
  return value;
}

function readPositiveInt(record: Record<string, unknown>, key: string): number {
  const value = readInteger(record, key);
  if (value < 1) {
    throw new FrameProtocolError('invalid_message');
  }
  return value;
}

function readOptionalNullableInt(
  record: Record<string, unknown>,
  key: string,
  minimum?: number,
): number | null | undefined {
  if (!hasOwn(record, key)) {
    return undefined;
  }
  const value = record[key];
  if (value === null) {
    return null;
  }
  if (!isInteger(value) || (minimum !== undefined && value < minimum)) {
    throw new FrameProtocolError('invalid_message');
  }
  return value;
}

function readUnit(record: Record<string, unknown>, key: string): number {
  const value = readRequired(record, key);
  if (!isUnit(value)) {
    throw new FrameProtocolError('invalid_message');
  }
  return value;
}

function readNullableUnit(record: Record<string, unknown>, key: string): number | null {
  const value = readRequired(record, key);
  if (value === null) {
    return null;
  }
  if (!isUnit(value)) {
    throw new FrameProtocolError('invalid_message');
  }
  return value;
}

function readFinite(record: Record<string, unknown>, key: string): number {
  const value = readRequired(record, key);
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new FrameProtocolError('invalid_message');
  }
  return value;
}

function readNullableFinite(record: Record<string, unknown>, key: string): number | null {
  const value = readRequired(record, key);
  if (value === null) {
    return null;
  }
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new FrameProtocolError('invalid_message');
  }
  return value;
}

function readNonNegativeNumber(record: Record<string, unknown>, key: string): number {
  const value = readFinite(record, key);
  if (value < 0) {
    throw new FrameProtocolError('invalid_message');
  }
  return value;
}

function hasOwn(record: object, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(record, key);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * `Array.isArray` narrows to `any[]`. The predicate keeps each element `unknown`.
 */
function readUnknownArray(value: unknown): readonly unknown[] {
  if (!isUnknownArray(value)) {
    throw new FrameProtocolError('invalid_message');
  }
  return value;
}

function isUnknownArray(value: unknown): value is readonly unknown[] {
  return Array.isArray(value);
}

function isInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value);
}

function isNonNegativeInteger(value: unknown): value is number {
  return isInteger(value) && value >= 0;
}

function isUnit(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;
}
