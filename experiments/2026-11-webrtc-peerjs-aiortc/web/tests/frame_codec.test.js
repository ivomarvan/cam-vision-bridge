import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { packChunk, parseServerMessage, splitFrame } from "../frame_codec.js";

const HEADER_KEY_ORDER = ["t", "run_id", "frame_id", "part", "parts", "total_bytes"];

describe("packChunk", () => {
  it("prefixes big-endian header length and ordered JSON keys", () => {
    const payload = new Uint8Array([0xff, 0xd8, 0xff]);
    const packed = packChunk(
      {
        run_id: "r20261121T120000-01",
        frame_id: 0,
        part: 0,
        parts: 1,
        total_bytes: 3,
      },
      payload,
    );
    const view = new DataView(packed.buffer, packed.byteOffset, packed.byteLength);
    const headerLen = view.getUint32(0, false);
    const headerBytes = packed.subarray(4, 4 + headerLen);
  const headerText = new TextDecoder().decode(headerBytes);
    const header = JSON.parse(headerText);
    assert.deepEqual(Object.keys(header), HEADER_KEY_ORDER);
    assert.equal(header.t, "frame");
    assert.deepEqual(packed.subarray(4 + headerLen), payload);
  });
});

describe("splitFrame", () => {
  it("splits 100000 bytes into 7 parts at 16384", () => {
    const jpeg = new Uint8Array(100_000);
    jpeg.fill(0xab);
    const messages = splitFrame({
      runId: "r20261121T120000-02",
      frameId: 1,
      jpeg,
      chunkBytes: 16_384,
    });
    assert.equal(messages.length, 7);
    let sum = 0;
    for (let part = 0; part < 7; part += 1) {
      const view = new DataView(messages[part].buffer, messages[part].byteOffset);
      const headerLen = view.getUint32(0, false);
      const header = JSON.parse(
        new TextDecoder().decode(messages[part].subarray(4, 4 + headerLen)),
      );
      assert.equal(header.part, part);
      assert.equal(header.parts, 7);
      assert.equal(header.total_bytes, 100_000);
      const payload = messages[part].subarray(4 + headerLen);
      sum += payload.length;
    }
    assert.equal(sum, 100_000);
  });

  it("chunkBytes zero yields a single message with parts=1", () => {
    const jpeg = new Uint8Array([1, 2, 3, 4]);
    const messages = splitFrame({
      runId: "r20261121T120000-03",
      frameId: 0,
      jpeg,
      chunkBytes: 0,
    });
    assert.equal(messages.length, 1);
    const view = new DataView(messages[0].buffer, messages[0].byteOffset);
    const headerLen = view.getUint32(0, false);
    const header = JSON.parse(
      new TextDecoder().decode(messages[0].subarray(4, 4 + headerLen)),
    );
    assert.equal(header.parts, 1);
    assert.equal(header.part, 0);
  });

  it("does not emit an empty trailing chunk when size is an exact multiple", () => {
    const jpeg = new Uint8Array(32_768);
    jpeg.fill(0xcd);
    const messages = splitFrame({
      runId: "r20261121T120000-04",
      frameId: 2,
      jpeg,
      chunkBytes: 16_384,
    });
    assert.equal(messages.length, 2);
    for (const message of messages) {
      const view = new DataView(message.buffer, message.byteOffset);
      const headerLen = view.getUint32(0, false);
      const payloadLen = message.length - 4 - headerLen;
      assert.ok(payloadLen > 0);
    }
  });
});

describe("parseServerMessage", () => {
  it("accepts echo messages", () => {
    const msg = parseServerMessage(
      '{"t":"echo","run_id":"r1","frame_id":0,"bytes":100,"parts":1,"decode_ms":1.2}',
    );
    assert.equal(msg.t, "echo");
  });

  it("rejects invalid JSON", () => {
    assert.throws(() => parseServerMessage("{"), /invalid_json/);
  });

  it("rejects unknown message type", () => {
    assert.throws(() => parseServerMessage('{"t":"wat"}'), /unknown_type/);
  });
});