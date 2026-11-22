/**
 * Phone-side PeerJS session for protocol v1.
 *
 * The PeerJS client is injected. Tests pass a fake and never open a socket to
 * the public broker. {@link importPeerJsFactory} is the browser constructor.
 * PeerJS 1.5.4 builds the OFFER itself. This module does not add a `browser`
 * field (DECISIONS #6). The echo measurement protocol is not used here.
 */

import type { DataConnection, Peer } from 'peerjs';

import type { CamVisionBridgeV1TextMessage, ErrorMessage, Hello, Result, Welcome } from '@/protocol/generated';
import { DEFAULT_CHUNK_BYTES, FrameProtocolError, parseServerMessage, splitFrame } from '@/protocol/frameCodec';

/** At most one JPEG waits for `result` or `error`. */
export const DEFAULT_IN_FLIGHT = 1;

/**
 * Options passed to PeerJS 1.5.4 `peer.connect`.
 * `serialization: "raw"` is {@link https://github.com/peers/peerjs/blob/v1.5.4/lib/enums.ts | SerializationType.None}.
 * The library then sends bytes unchanged. `reliable: true` requests an ordered data channel.
 */
export const PEER_CONNECT_OPTIONS = {
  reliable: true,
  serialization: 'raw',
} as const;

export type PeerConnectOptions = typeof PEER_CONNECT_OPTIONS;

/** Lifecycle the screen can show. Frames are sent only while `open`. */
export type SessionStatus = 'idle' | 'connecting' | 'open' | 'version-mismatch' | 'error';

/** Live data channel. `binaryType` is set to `arraybuffer` when the channel opens. */
export interface SessionDataChannel {
  binaryType: BinaryType;
}

/** Handlers for one data connection. Installed together so `open` cannot race `data`. */
export interface SessionConnectionHandlers {
  readonly onOpen: () => void;
  readonly onData: (data: unknown) => void;
  readonly onError: (error: unknown) => void;
  readonly onClose: () => void;
}

/**
 * Data connection the session can drive without importing PeerJS.
 * Pattern: Dependency Injection — production wraps PeerJS; tests pass a fake.
 */
export interface SessionConnection {
  readonly dataChannel: SessionDataChannel;
  send(data: string | ArrayBuffer): void;
  close(): void;
  subscribe(handlers: SessionConnectionHandlers): void;
}

/** Handlers for the local peer's broker socket. */
export interface SessionPeerHandlers {
  readonly onOpen: (localId: string) => void;
  readonly onError: (error: unknown) => void;
}

/** Local peer that can open one raw data connection to the Python peer id. */
export interface SessionPeer {
  connect(peerId: string, options: PeerConnectOptions): SessionConnection;
  subscribe(handlers: SessionPeerHandlers): void;
  destroy(): void;
}

/** Builds the local peer. Called from {@link PeerSession.start}, not at import time. */
export type PeerClientFactory = () => SessionPeer;

/** Capture identity carried in `hello` and in every frame header. */
export interface PeerSessionOptions {
  /** Remote peer id from the URL hash (`#peer=`). */
  readonly peerId: string;
  /** Injected PeerJS (or a fake). Must not be the real client in unit tests. */
  readonly createPeer: PeerClientFactory;
  /** `hello.device_ua`. */
  readonly deviceUa: string;
  /** Capture width in pixels. Also `hello.width` and frame header `w`. */
  readonly width: number;
  /** Capture height in pixels. Also `hello.height` and frame header `h`. */
  readonly height: number;
  /** `hello.camera` when the facing mode is already known. */
  readonly camera?: 'user' | 'environment' | null;
  /** `captured_at` clock. Defaults to `Date.toISOString`. */
  readonly now?: () => string;
}

type WelcomeGate =
  | { readonly kind: 'not-welcome' }
  | { readonly kind: 'supported' }
  | { readonly kind: 'mismatch'; readonly version: number | null };

/**
 * Connects to the PC peer, sends `hello`, and posts at most one JPEG at a time.
 */
export class PeerSession {
  readonly #options: PeerSessionOptions;
  readonly #now: () => string;
  #status: SessionStatus = 'idle';
  #statusDetail: string | null = null;
  #welcome: Welcome | null = null;
  #lastResult: Result | null = null;
  #peer: SessionPeer | null = null;
  #connection: SessionConnection | null = null;
  #framesInFlight = 0;
  #nextFrameId = 0;
  #helloSent = false;
  #frameWidth: number;
  #frameHeight: number;

  /**
   * @param options - Remote peer id, injected client, and capture identity for `hello`.
   * @throws {RangeError} When width or height is not a positive integer.
   */
  constructor(options: PeerSessionOptions) {
    assertCaptureSize(options.width, options.height);
    this.#options = options;
    this.#frameWidth = options.width;
    this.#frameHeight = options.height;
    this.#now = options.now ?? defaultNow;
  }

  /** Current lifecycle state. */
  get status(): SessionStatus {
    return this.#status;
  }

  /**
   * Human-readable failure for `version-mismatch` or `error`.
   * A protocol `error` message while the session stays `open` is stored here too.
   */
  get statusDetail(): string | null {
    return this.#statusDetail;
  }

  /** Last `welcome` whose `v` was 1, or null. */
  get welcome(): Welcome | null {
    return this.#welcome;
  }

  /** Last `result`, or null before the first one. */
  get lastResult(): Result | null {
    return this.#lastResult;
  }

  /**
   * Open the broker peer and, once it is open, the data channel to `peerId`.
   * A second call does nothing. An empty peer id fails without creating a client.
   */
  start(): void {
    if (this.#status !== 'idle') {
      return;
    }
    if (this.#options.peerId.length === 0) {
      this.#fail('Missing peer id');
      return;
    }
    this.#status = 'connecting';
    const peer = this.#options.createPeer();
    this.#peer = peer;
    peer.subscribe({
      onOpen: () => {
        this.#connect(peer);
      },
      onError: (error: unknown) => {
        this.#fail(errorText(error));
      },
    });
  }

  /**
   * Send one JPEG, split with the frame codec when it is larger than
   * {@link DEFAULT_CHUNK_BYTES}.
   *
   * Does nothing unless `welcome` with `v` 1 was accepted, and does nothing
   * when a frame is already waiting for `result` or `error`.
   *
   * @param jpeg - Encoded frame bytes. Not decoded here.
   * @throws {FrameProtocolError} When the JPEG or its header breaks a codec limit.
   */
  sendFrame(jpeg: Uint8Array): void {
    const connection = this.#connection;
    if (!this.#canSend(connection)) {
      return;
    }
    const chunks = splitFrame({
      frameId: this.#nextFrameId,
      capturedAt: this.#now(),
      w: this.#frameWidth,
      h: this.#frameHeight,
      jpeg,
      chunkBytes: DEFAULT_CHUNK_BYTES,
    });
    this.#framesInFlight += 1;
    this.#nextFrameId += 1;
    this.#sendChunks(connection, chunks);
  }

  /**
   * Set the pixel size used for a later frame header.
   *
   * `hello` is sent once, from the size stored when the channel opens. Calling
   * this after that does not send a second `hello`. The PC sees the new size
   * on the next frame. Calling it before `hello` updates that single `hello`.
   *
   * @param width - Bitmap width in pixels.
   * @param height - Bitmap height in pixels.
   * @throws {RangeError} When width or height is not a positive integer.
   */
  setCaptureSize(width: number, height: number): void {
    assertCaptureSize(width, height);
    this.#frameWidth = width;
    this.#frameHeight = height;
  }

  /** Close the data channel and destroy the local peer. */
  close(): void {
    this.#connection?.close();
    this.#peer?.destroy();
    this.#connection = null;
    this.#peer = null;
  }

  #connect(peer: SessionPeer): void {
    if (this.#status !== 'connecting') {
      return;
    }
    const connection = peer.connect(this.#options.peerId, PEER_CONNECT_OPTIONS);
    this.#connection = connection;
    connection.subscribe({
      onOpen: () => {
        this.#onChannelOpen(connection);
      },
      onData: (data: unknown) => {
        this.#onData(data);
      },
      onError: (error: unknown) => {
        this.#fail(errorText(error));
      },
      onClose: () => {
        this.#onChannelClose();
      },
    });
  }

  #onChannelOpen(connection: SessionConnection): void {
    if (this.#helloSent) {
      return;
    }
    this.#helloSent = true;
    connection.dataChannel.binaryType = 'arraybuffer';
    connection.send(JSON.stringify(buildHello(this.#options, this.#frameWidth, this.#frameHeight)));
  }

  #onData(data: unknown): void {
    if (this.#status === 'version-mismatch' || this.#status === 'error') {
      return;
    }
    const text = textFromPeerData(data);
    if (text === null) {
      return;
    }
    const gate = classifyWelcome(text);
    if (gate.kind === 'mismatch') {
      this.#markVersionMismatch(gate.version);
      return;
    }
    const message = parseOrIgnore(text);
    if (message === null) {
      return;
    }
    this.#apply(message);
  }

  #apply(message: CamVisionBridgeV1TextMessage): void {
    switch (message.t) {
      case 'welcome':
        this.#acceptWelcome(message);
        return;
      case 'result':
        this.#acceptResult(message);
        return;
      case 'error':
        this.#acceptProtocolError(message);
        return;
      case 'hello':
      case 'frame':
        return;
      default:
        throw new Error(unknownMessage(message));
    }
  }

  #acceptWelcome(message: Welcome): void {
    this.#welcome = message;
    this.#status = 'open';
    this.#statusDetail = null;
  }

  #acceptResult(message: Result): void {
    this.#lastResult = message;
    this.#framesInFlight = 0;
  }

  #acceptProtocolError(message: ErrorMessage): void {
    this.#statusDetail = message.reason;
    this.#framesInFlight = 0;
  }

  #markVersionMismatch(version: number | null): void {
    this.#status = 'version-mismatch';
    this.#statusDetail = versionMismatchDetail(version);
    this.#framesInFlight = 0;
  }

  #onChannelClose(): void {
    if (this.#status === 'connecting' || this.#status === 'open') {
      this.#fail('Data channel closed');
    }
  }

  #fail(detail: string): void {
    this.#status = 'error';
    this.#statusDetail = detail;
  }

  #canSend(connection: SessionConnection | null): connection is SessionConnection {
    return this.#status === 'open' && connection !== null && this.#framesInFlight < DEFAULT_IN_FLIGHT;
  }

  #sendChunks(connection: SessionConnection, chunks: readonly Uint8Array[]): void {
    for (const chunk of chunks) {
      connection.send(arrayBufferOf(chunk));
    }
  }
}

/**
 * Load PeerJS 1.5.4 and return a factory.
 *
 * Calling the factory runs `new Peer()`, which opens a socket to the configured
 * broker (by default `0.peerjs.com`). Unit tests must not call this.
 *
 * @returns A factory that builds one browser peer per call.
 */
export async function importPeerJsFactory(): Promise<PeerClientFactory> {
  const { Peer: PeerCtor } = await import('peerjs');
  return () => adaptPeer(new PeerCtor());
}

function adaptPeer(peer: Peer): SessionPeer {
  return {
    connect(peerId: string, options: PeerConnectOptions): SessionConnection {
      return adaptConnection(peer.connect(peerId, options));
    },
    subscribe(handlers: SessionPeerHandlers): void {
      peer.on('open', (localId: string) => {
        handlers.onOpen(localId);
      });
      peer.on('error', (error: unknown) => {
        handlers.onError(error);
      });
    },
    destroy(): void {
      peer.destroy();
    },
  };
}

function adaptConnection(connection: DataConnection): SessionConnection {
  let reportSendError: (error: unknown) => void = ignoreLateSendError;
  return {
    get dataChannel(): SessionDataChannel {
      return connection.dataChannel;
    },
    send(data: string | ArrayBuffer): void {
      forwardSend(connection.send(data), (error: unknown) => {
        reportSendError(error);
      });
    },
    close(): void {
      connection.close();
    },
    subscribe(handlers: SessionConnectionHandlers): void {
      reportSendError = handlers.onError;
      bindConnection(connection, handlers);
    },
  };
}

function forwardSend(pending: unknown, reportSendError: (error: unknown) => void): void {
  if (!isPromise(pending)) {
    return;
  }
  // Rejection is reported to the session. The chained promise is not awaited.
  void pending.catch((error: unknown) => {
    reportSendError(error);
  });
}

function bindConnection(connection: DataConnection, handlers: SessionConnectionHandlers): void {
  connection.on('open', () => {
    handlers.onOpen();
  });
  connection.on('data', (data: unknown) => {
    handlers.onData(data);
  });
  connection.on('error', (error: unknown) => {
    handlers.onError(error);
  });
  connection.on('close', () => {
    handlers.onClose();
  });
}

function assertCaptureSize(width: number, height: number): void {
  if (!Number.isInteger(width) || width < 1 || !Number.isInteger(height) || height < 1) {
    throw new RangeError('capture width and height must be positive integers');
  }
}

function defaultNow(): string {
  return new Date().toISOString();
}

function buildHello(options: PeerSessionOptions, width: number, height: number): Hello {
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
    device_ua: options.deviceUa,
    width,
    height,
  };
  if (options.camera !== undefined) {
    message.camera = options.camera;
  }
  return message;
}

function textFromPeerData(data: unknown): string | null {
  if (typeof data === 'string') {
    return data;
  }
  if (data instanceof ArrayBuffer) {
    return jsonObjectText(new Uint8Array(data));
  }
  if (data instanceof Uint8Array) {
    return jsonObjectText(data);
  }
  return null;
}

/**
 * Binary welcome/result/error payloads are UTF-8 objects. JPEG chunks are not.
 */
function jsonObjectText(bytes: Uint8Array): string | null {
  if (bytes.at(0) !== 0x7b) {
    return null;
  }
  return new TextDecoder().decode(bytes);
}

function classifyWelcome(text: string): WelcomeGate {
  const record = parseRecord(text);
  if (record?.t !== 'welcome') {
    return { kind: 'not-welcome' };
  }
  if (record.v === 1) {
    return { kind: 'supported' };
  }
  return { kind: 'mismatch', version: finiteVersion(record.v) };
}

function parseRecord(text: string): Record<string, unknown> | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return null;
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    return null;
  }
  return parsed;
}

function finiteVersion(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  return null;
}

function parseOrIgnore(text: string): CamVisionBridgeV1TextMessage | null {
  try {
    return parseServerMessage(text);
  } catch (error: unknown) {
    if (error instanceof FrameProtocolError) {
      return null;
    }
    throw error;
  }
}

function versionMismatchDetail(version: number | null): string {
  if (version === null) {
    return 'Protocol version is not supported; this phone speaks v1';
  }
  return `Protocol version ${String(version)} is not supported; this phone speaks v1`;
}

function errorText(error: unknown): string {
  if (error instanceof Error && error.message.length > 0) {
    return error.message;
  }
  return 'Peer connection failed';
}

function unknownMessage(message: never): string {
  return `Unhandled protocol message: ${JSON.stringify(message)}`;
}

function arrayBufferOf(bytes: Uint8Array): ArrayBuffer {
  const copy = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(copy).set(bytes);
  return copy;
}

function isPromise(value: unknown): value is Promise<unknown> {
  return value instanceof Promise;
}

function ignoreLateSendError(): void {
  // subscribe() replaces this before the channel can send.
}
