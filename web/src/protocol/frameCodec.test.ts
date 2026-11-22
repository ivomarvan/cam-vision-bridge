import { describe, expect, it } from 'vitest';

import {
  DEFAULT_CHUNK_BYTES,
  FrameProtocolError,
  packChunk,
  parseServerMessage,
  splitFrame,
} from './frameCodec';

const CAPTURED_AT = '2026-11-22T00:00:00+00:00';
const HEADER_KEYS = [
  'v',
  't',
  'frame_id',
  'captured_at',
  'w',
  'h',
  'part',
  'parts',
  'total_bytes',
] as const;

describe('packChunk', () => {
  it('round-trips big-endian header length and JSON key order', () => {
    const json =
      '{"v":1,"t":"frame","frame_id":7,"captured_at":"2026-11-22T00:00:00+00:00","w":640,"h":480,"part":1,"parts":3,"total_bytes":3}';
    const payload = new Uint8Array([9, 8, 7]);
    const message = packChunk(
      {
        v: 1,
        t: 'frame',
        frame_id: 7,
        captured_at: CAPTURED_AT,
        w: 640,
        h: 480,
        part: 1,
        parts: 3,
        total_bytes: payload.byteLength,
      },
      payload,
    );

    expect(Array.from(message.subarray(0, 4))).toEqual(uint32be(json.length));
    const decoded = new TextDecoder().decode(message.subarray(4, 4 + json.length));
    expect(decoded).toBe(json);
    expect(jsonKeys(decoded)).toEqual([...HEADER_KEYS]);
    expect(Array.from(message.subarray(4 + json.length))).toEqual([9, 8, 7]);
    expect(message.byteLength).toBe(4 + json.length + payload.byteLength);
  });

  it('counts header length in UTF-8 bytes', () => {
    const json =
      '{"v":1,"t":"frame","frame_id":0,"captured_at":"café","w":1,"h":1,"part":0,"parts":1,"total_bytes":1}';
    const encoded = new TextEncoder().encode(json);
    expect(encoded.byteLength).not.toBe(json.length);
    const message = packChunk(
      {
        v: 1,
        t: 'frame',
        frame_id: 0,
        captured_at: 'café',
        w: 1,
        h: 1,
        part: 0,
        parts: 1,
        total_bytes: 1,
      },
      new Uint8Array([4]),
    );
    const view = new DataView(message.buffer, message.byteOffset, message.byteLength);
    expect(view.getUint32(0, false)).toBe(encoded.byteLength);
    expect(new TextDecoder().decode(message.subarray(4, 4 + encoded.byteLength))).toBe(json);
  });
});

describe('splitFrame', () => {
  it('splits 100000 bytes by the default 16384 without an empty tail', () => {
    const jpeg = new Uint8Array(100_000);
    jpeg[0] = 1;
    jpeg[99_999] = 2;
    const messages = splitFrame({
      frameId: 4,
      capturedAt: CAPTURED_AT,
      w: 3,
      h: 2,
      jpeg,
    });
    const partCount = Math.ceil(jpeg.byteLength / DEFAULT_CHUNK_BYTES);
    expect(DEFAULT_CHUNK_BYTES).toBe(16_384);
    expect(messages).toHaveLength(partCount);
    expect(partCount).toBe(7);

    const payloads: Uint8Array[] = [];
    messages.forEach((message, index) => {
      const chunk = readChunk(message);
      expect(chunk.payload.byteLength).toBeGreaterThan(0);
      expect(jsonKeys(chunk.json)).toEqual([...HEADER_KEYS]);
      expect(chunk.fields.part).toBe(index);
      expect(chunk.fields.parts).toBe(partCount);
      expect(chunk.fields.total_bytes).toBe(jpeg.byteLength);
      payloads.push(chunk.payload);
    });

    const last = payloads.at(-1);
    expect(last?.byteLength).toBe(jpeg.byteLength - (partCount - 1) * DEFAULT_CHUNK_BYTES);
    expect(concatPayloads(payloads)).toEqual(jpeg);
  });

  it('does not add an empty part when the length is an exact multiple', () => {
    const chunkBytes = 16_384;
    const jpeg = new Uint8Array(chunkBytes * 2);
    jpeg[0] = 5;
    jpeg[chunkBytes] = 6;
    const messages = splitFrame({
      frameId: 1,
      capturedAt: CAPTURED_AT,
      w: 2,
      h: 2,
      jpeg,
      chunkBytes,
    });
    expect(messages).toHaveLength(2);
    const payloads = messages.map((message) => readChunk(message).payload);
    expect(payloads.map((payload) => payload.byteLength)).toEqual([chunkBytes, chunkBytes]);
    expect(concatPayloads(payloads)).toEqual(jpeg);
  });

  it('sends one message when chunkBytes is 0', () => {
    const jpeg = new Uint8Array(20_000);
    jpeg[19_999] = 9;
    const messages = splitFrame({
      frameId: 8,
      capturedAt: CAPTURED_AT,
      w: 8,
      h: 8,
      jpeg,
      chunkBytes: 0,
    });
    expect(messages).toHaveLength(1);
    const chunk = readChunk(messageAt(messages, 0));
    expect(chunk.fields.part).toBe(0);
    expect(chunk.fields.parts).toBe(1);
    expect(chunk.fields.total_bytes).toBe(jpeg.byteLength);
    expect(chunk.payload).toEqual(jpeg);
  });

  it('keeps an empty jpeg as one part', () => {
    const messages = splitFrame({
      frameId: 0,
      capturedAt: CAPTURED_AT,
      w: 1,
      h: 1,
      jpeg: new Uint8Array(),
      chunkBytes: DEFAULT_CHUNK_BYTES,
    });
    expect(messages).toHaveLength(1);
    const chunk = readChunk(messageAt(messages, 0));
    expect(chunk.payload.byteLength).toBe(0);
    expect(chunk.fields.parts).toBe(1);
    expect(chunk.fields.total_bytes).toBe(0);
  });

  it('rejects a negative chunkBytes', () => {
    expect(() =>
      splitFrame({
        frameId: 1,
        capturedAt: CAPTURED_AT,
        w: 1,
        h: 1,
        jpeg: new Uint8Array([1]),
        chunkBytes: -1,
      }),
    ).toThrow(RangeError);
  });
});

describe('parseServerMessage', () => {
  it('parses welcome, error, and result when v is 1', () => {
    expect(parseServerMessage('{"v":1,"t":"welcome"}')).toEqual({ v: 1, t: 'welcome' });
    expect(parseServerMessage('{"v":1,"t":"error","reason":"dropped"}')).toEqual({
      v: 1,
      t: 'error',
      reason: 'dropped',
    });
    expect(
      parseServerMessage(
        JSON.stringify({
          v: 1,
          t: 'result',
          frame_id: 3,
          processing_ms: 1.5,
          items: [
            { t: 'box', x: 0, y: 0, w: 1, h: 1 },
            { t: 'text', text: 'fps' },
          ],
        }),
      ),
    ).toEqual({
      v: 1,
      t: 'result',
      frame_id: 3,
      processing_ms: 1.5,
      items: [
        { t: 'box', x: 0, y: 0, w: 1, h: 1 },
        { t: 'text', text: 'fps' },
      ],
    });
  });

  it('throws when t is missing or unknown', () => {
    expect(reasonOf('{"v":1}')).toBe('unknown_type');
    expect(reasonOf('{"v":1,"t":"nope"}')).toBe('unknown_type');
  });

  it('throws when v is not 1', () => {
    expect(reasonOf('{"v":2,"t":"welcome"}')).toBe('unsupported_version');
    expect(reasonOf('{"t":"error","reason":"x"}')).toBe('unsupported_version');
  });

  it('rejects an unknown key', () => {
    expect(() => parseServerMessage('{"v":1,"t":"welcome","extra":true}')).toThrow(FrameProtocolError);
  });
});

function reasonOf(text: string): string {
  try {
    parseServerMessage(text);
  } catch (error: unknown) {
    if (error instanceof FrameProtocolError) {
      return error.reason;
    }
    throw error;
  }
  throw new Error('expected FrameProtocolError');
}

function messageAt(messages: readonly Uint8Array[], index: number): Uint8Array {
  const message = messages.at(index);
  if (message === undefined) {
    throw new Error(`missing message at index ${String(index)}`);
  }
  return message;
}

function uint32be(value: number): number[] {
  return [(value >>> 24) & 0xff, (value >>> 16) & 0xff, (value >>> 8) & 0xff, value & 0xff];
}

function jsonKeys(json: string): string[] {
  const parsed: unknown = JSON.parse(json);
  if (!isRecord(parsed)) {
    throw new Error('header is not an object');
  }
  return Object.keys(parsed);
}

function readChunk(message: Uint8Array): {
  json: string;
  payload: Uint8Array;
  fields: Record<string, unknown>;
} {
  const view = new DataView(message.buffer, message.byteOffset, message.byteLength);
  const headerLen = view.getUint32(0, false);
  const json = new TextDecoder().decode(message.subarray(4, 4 + headerLen));
  const parsed: unknown = JSON.parse(json);
  if (!isRecord(parsed)) {
    throw new Error('header is not an object');
  }
  return { json, payload: message.subarray(4 + headerLen), fields: parsed };
}

function concatPayloads(parts: readonly Uint8Array[]): Uint8Array {
  const size = parts.reduce((sum, part) => sum + part.byteLength, 0);
  const joined = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) {
    joined.set(part, offset);
    offset += part.byteLength;
  }
  return joined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
