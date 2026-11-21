/**
 * Pure helpers for JPEG chunk framing on a WebRTC DataChannel (spike contract).
 */

const HEADER_KEY_ORDER = ["t", "run_id", "frame_id", "part", "parts", "total_bytes"];

/**
 * Build a UTF-8 JSON header with keys in the prescribed order.
 *
 * @param {object} fields Header fields without `t` (always `"frame"`).
 * @returns {string} Compact JSON string.
 */
function encodeHeaderJson(fields) {
  const document = { t: "frame" };
  for (const key of HEADER_KEY_ORDER) {
    if (key === "t") continue;
    document[key] = fields[key];
  }
  return JSON.stringify(document);
}

/**
 * Pack one chunk into the wire format: BE uint32 header length + JSON + payload.
 *
 * @param {object} header Chunk metadata (`run_id`, `frame_id`, `part`, `parts`, `total_bytes`).
 * @param {Uint8Array} payload JPEG bytes for this part.
 * @returns {Uint8Array} Full message.
 */
export function packChunk(header, payload) {
  const body = new TextEncoder().encode(encodeHeaderJson(header));
  const out = new Uint8Array(4 + body.length + payload.length);
  const view = new DataView(out.buffer);
  view.setUint32(0, body.length, false);
  out.set(body, 4);
  out.set(payload, 4 + body.length);
  return out;
}

/**
 * Split a JPEG into DataChannel messages.
 *
 * @param {object} opts
 * @param {string} opts.runId
 * @param {number} opts.frameId
 * @param {Uint8Array} opts.jpeg Full JPEG.
 * @param {number} opts.chunkBytes Max payload per part; `0` means one message.
 * @returns {Uint8Array[]} Packed messages.
 */
export function splitFrame({ runId, frameId, jpeg, chunkBytes }) {
  const total = jpeg.length;
  if (chunkBytes === 0) {
    return [
      packChunk(
        {
          run_id: runId,
          frame_id: frameId,
          part: 0,
          parts: 1,
          total_bytes: total,
        },
        jpeg,
      ),
    ];
  }
  const parts = Math.ceil(total / chunkBytes);
  const messages = [];
  for (let part = 0; part < parts; part += 1) {
    const start = part * chunkBytes;
    const end = Math.min(start + chunkBytes, total);
    const slice = jpeg.subarray(start, end);
    if (slice.length === 0) {
      continue;
    }
    messages.push(
      packChunk(
        {
          run_id: runId,
          frame_id: frameId,
          part,
          parts,
          total_bytes: total,
        },
        slice,
      ),
    );
  }
  return messages;
}

const ALLOWED_SERVER_TYPES = new Set(["echo", "error"]);

/**
 * Parse a JSON text message from the Python peer.
 *
 * @param {string} text Raw UTF-8 JSON from the DataChannel.
 * @returns {object} Parsed message with known `t`.
 * @throws {Error} On invalid JSON or unknown `t`.
 */
export function parseServerMessage(text) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error("invalid_json");
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("invalid_json");
  }
  const kind = parsed.t;
  if (typeof kind !== "string" || !ALLOWED_SERVER_TYPES.has(kind)) {
    throw new Error("unknown_type");
  }
  return parsed;
}