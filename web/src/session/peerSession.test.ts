import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DEFAULT_CHUNK_BYTES, splitFrame } from '@/protocol/frameCodec';

import {
  PEER_CONNECT_OPTIONS,
  PeerSession,
  type PeerConnectOptions,
  type SessionConnection,
  type SessionConnectionHandlers,
  type SessionDataChannel,
  type SessionPeer,
  type SessionPeerHandlers,
} from './peerSession';

const CAPTURED_AT = '2026-11-22T00:00:00.000Z';
const JPEG = new Uint8Array([0xff, 0xd8, 0xff, 0xd9]);

class FakeConnection implements SessionConnection {
  readonly dataChannel: SessionDataChannel = { binaryType: 'blob' };
  readonly sent: (string | ArrayBuffer)[] = [];
  #onData: ((data: unknown) => void) | null = null;

  send(data: string | ArrayBuffer): void {
    this.sent.push(data);
  }

  close(): void {
    // The session test does not observe close.
  }

  subscribe(handlers: SessionConnectionHandlers): void {
    this.#onData = handlers.onData;
    handlers.onOpen();
  }

  deliver(data: unknown): void {
    this.#onData?.(data);
  }
}

class FakePeer implements SessionPeer {
  connection: FakeConnection | null = null;
  connectOptions: PeerConnectOptions | null = null;
  connectedPeerId: string | null = null;

  connect(peerId: string, options: PeerConnectOptions): SessionConnection {
    this.connectedPeerId = peerId;
    this.connectOptions = options;
    const connection = new FakeConnection();
    this.connection = connection;
    return connection;
  }

  subscribe(handlers: SessionPeerHandlers): void {
    handlers.onOpen('local-peer');
  }

  destroy(): void {
    // The session test does not observe destroy.
  }
}

function texts(connection: FakeConnection): string[] {
  return connection.sent.filter((item): item is string => typeof item === 'string');
}

function binaries(connection: FakeConnection): ArrayBuffer[] {
  return connection.sent.filter((item): item is ArrayBuffer => item instanceof ArrayBuffer);
}

function payloadOf(message: ArrayBuffer): Uint8Array {
  const view = new DataView(message);
  const headerLength = view.getUint32(0, false);
  return new Uint8Array(message).subarray(4 + headerLength);
}

function openSession(): { session: PeerSession; peer: FakePeer; connection: FakeConnection } {
  const peer = new FakePeer();
  const session = new PeerSession({
    peerId: 'pc-peer',
    createPeer: () => peer,
    deviceUa: 'test-agent',
    width: 640,
    height: 480,
    now: () => CAPTURED_AT,
  });
  session.start();
  const connection = peer.connection;
  if (connection === null) {
    throw new Error('start() did not connect');
  }
  return { session, peer, connection };
}

function deliverJson(connection: FakeConnection, message: unknown): void {
  connection.deliver(JSON.stringify(message));
}

describe('PeerSession', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', (url: unknown) => {
      throw new Error(`blocked WebSocket ${String(url)}`);
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sends hello and one binary message for a small JPEG', () => {
    const { session, peer, connection } = openSession();

    expect(peer.connectedPeerId).toBe('pc-peer');
    expect(peer.connectOptions).toEqual(PEER_CONNECT_OPTIONS);
    expect(connection.dataChannel.binaryType).toBe('arraybuffer');
    expect(JSON.parse(texts(connection)[0] ?? '')).toEqual({
      v: 1,
      t: 'hello',
      device_ua: 'test-agent',
      width: 640,
      height: 480,
    });

    session.sendFrame(JPEG);
    expect(binaries(connection)).toHaveLength(0);

    deliverJson(connection, { v: 1, t: 'welcome' });
    expect(session.status).toBe('open');

    session.sendFrame(JPEG);
    const binary = binaries(connection);
    expect(binary).toHaveLength(1);
    const message = binary[0];
    if (message === undefined) {
      throw new Error('expected one binary message');
    }
    expect(Array.from(payloadOf(message))).toEqual(Array.from(JPEG));
  });

  it('drops a second frame until result arrives', () => {
    const { session, connection } = openSession();
    deliverJson(connection, { v: 1, t: 'welcome' });

    session.sendFrame(JPEG);
    session.sendFrame(new Uint8Array([1, 2, 3]));
    expect(binaries(connection)).toHaveLength(1);

    deliverJson(connection, {
      v: 1,
      t: 'result',
      frame_id: 0,
      items: [],
      processing_ms: 1,
    });
    session.sendFrame(new Uint8Array([1, 2, 3]));

    const binary = binaries(connection);
    expect(binary).toHaveLength(2);
    const second = binary[1];
    if (second === undefined) {
      throw new Error('expected a second binary message');
    }
    expect(Array.from(payloadOf(second))).toEqual([1, 2, 3]);
  });

  it('allows another frame after a protocol error', () => {
    const { session, connection } = openSession();
    deliverJson(connection, { v: 1, t: 'welcome' });
    session.sendFrame(JPEG);
    deliverJson(connection, { v: 1, t: 'error', reason: 'bad_frame', frame_id: 0 });
    expect(session.status).toBe('open');

    session.sendFrame(JPEG);
    expect(binaries(connection)).toHaveLength(2);
  });

  it('stops sending frames when welcome version is not 1', () => {
    const { session, connection } = openSession();
    expect(texts(connection)).toHaveLength(1);

    deliverJson(connection, { v: 2, t: 'welcome' });
    expect(session.status).toBe('version-mismatch');
    expect(session.statusDetail).toContain('v1');

    session.sendFrame(JPEG);
    expect(binaries(connection)).toHaveLength(0);
    expect(session.status).toBe('version-mismatch');
  });

  it('splits a JPEG larger than 16384 bytes into codec chunks', () => {
    const { session, connection } = openSession();
    deliverJson(connection, { v: 1, t: 'welcome' });
    const jpeg = new Uint8Array(DEFAULT_CHUNK_BYTES + 1);
    jpeg[0] = 9;
    jpeg[DEFAULT_CHUNK_BYTES] = 8;

    session.sendFrame(jpeg);
    session.sendFrame(JPEG);
    const binary = binaries(connection);
    const expected = splitFrame({
      frameId: 0,
      capturedAt: CAPTURED_AT,
      w: 640,
      h: 480,
      jpeg,
      chunkBytes: DEFAULT_CHUNK_BYTES,
    });

    expect(binary).toHaveLength(expected.length);
    expect(expected.length).toBeGreaterThan(1);
    binary.forEach((message, index) => {
      const chunk = expected[index];
      if (chunk === undefined) {
        throw new Error(`missing expected chunk ${String(index)}`);
      }
      expect(Array.from(new Uint8Array(message))).toEqual(Array.from(chunk));
    });
  });

  it('puts a new bitmap size on the next frame and does not send a second hello', () => {
    const { session, connection } = openSession();
    expect(texts(connection)).toHaveLength(1);
    expect(JSON.parse(texts(connection)[0] ?? '')).toMatchObject({ width: 640, height: 480 });

    session.setCaptureSize(1920, 1080);
    deliverJson(connection, { v: 1, t: 'welcome' });
    session.sendFrame(JPEG);

    expect(texts(connection)).toHaveLength(1);
    const expected = splitFrame({
      frameId: 0,
      capturedAt: CAPTURED_AT,
      w: 1920,
      h: 1080,
      jpeg: JPEG,
      chunkBytes: DEFAULT_CHUNK_BYTES,
    });
    const binary = binaries(connection);
    expect(binary).toHaveLength(expected.length);
    const message = binary[0];
    const chunk = expected[0];
    if (message === undefined || chunk === undefined) {
      throw new Error('expected one frame chunk');
    }
    expect(Array.from(new Uint8Array(message))).toEqual(Array.from(chunk));
  });
});
