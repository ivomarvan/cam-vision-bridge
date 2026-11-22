import { describe, expect, it, vi } from 'vitest';

import {
  CAPTURE_FRAME_HEIGHT,
  CAPTURE_FRAME_WIDTH,
  CaptureFrameError,
  JPEG_MIME_TYPE,
  captureFrame,
  openCamera,
  previewIsMirrored,
  type GetUserMedia,
} from './captureFrame';

const QUALITY = 0.82;

function fakeVideo(videoWidth: number, videoHeight: number): HTMLVideoElement {
  return { videoWidth, videoHeight } as unknown as HTMLVideoElement;
}

interface RecordedDraw {
  readonly drawImage: ReturnType<typeof vi.fn>;
  readonly toBlob: ReturnType<typeof vi.fn>;
  readonly canvas: HTMLCanvasElement;
}

function recordingCanvas(jpeg: Blob | null): RecordedDraw {
  const drawImage = vi.fn();
  const toBlob = vi.fn((callback: (blob: Blob | null) => void) => {
    callback(jpeg);
  });
  const canvas = {
    width: 0,
    height: 0,
    getContext: (contextId: string) => {
      if (contextId !== '2d') {
        return null;
      }
      return { drawImage };
    },
    toBlob,
  } as unknown as HTMLCanvasElement;
  return { drawImage, toBlob, canvas };
}

describe('captureFrame', () => {
  it('draws a 100×100 video at its real size instead of stretching to 640×480', async () => {
    const video = fakeVideo(100, 100);
    const jpeg = new Blob([Uint8Array.from([0xff, 0xd8])], { type: JPEG_MIME_TYPE });
    const recorded = recordingCanvas(jpeg);

    const blob = await captureFrame(video, QUALITY, recorded.canvas);

    expect(blob).toBe(jpeg);
    expect(recorded.canvas.width).toBe(100);
    expect(recorded.canvas.height).toBe(100);
    expect(recorded.drawImage).toHaveBeenCalledTimes(1);
    expect(recorded.drawImage).toHaveBeenCalledWith(video, 0, 0, 100, 100, 0, 0, 100, 100);
    expect(recorded.toBlob).toHaveBeenCalledWith(expect.any(Function), JPEG_MIME_TYPE, QUALITY);
  });

  it('draws a 1280×720 video onto a 1280×720 canvas', async () => {
    const video = fakeVideo(1280, 720);
    const recorded = recordingCanvas(new Blob([Uint8Array.from([1])], { type: JPEG_MIME_TYPE }));

    await captureFrame(video, QUALITY, recorded.canvas);

    expect(recorded.canvas.width).toBe(1280);
    expect(recorded.canvas.height).toBe(720);
    expect(recorded.drawImage).toHaveBeenCalledWith(video, 0, 0, 1280, 720, 0, 0, 1280, 720);
  });

  it('scales a 3840×2160 video so the longer side is 1920', async () => {
    const video = fakeVideo(3840, 2160);
    const recorded = recordingCanvas(new Blob([Uint8Array.from([1])], { type: JPEG_MIME_TYPE }));

    await captureFrame(video, QUALITY, recorded.canvas);

    expect(recorded.canvas.width).toBe(1920);
    expect(recorded.canvas.height).toBe(1080);
    expect(recorded.drawImage).toHaveBeenCalledWith(video, 0, 0, 3840, 2160, 0, 0, 1920, 1080);
  });

  it('asks getUserMedia for the front or rear camera and no microphone', async () => {
    const stream = { id: 'camera' } as unknown as MediaStream;
    const getUserMedia: GetUserMedia = vi.fn(() => Promise.resolve(stream));

    await expect(openCamera(getUserMedia, 'user')).resolves.toBe(stream);
    await expect(openCamera(getUserMedia, 'environment')).resolves.toBe(stream);

    expect(getUserMedia).toHaveBeenNthCalledWith(1, {
      audio: false,
      video: {
        facingMode: { exact: 'user' },
        width: { ideal: CAPTURE_FRAME_WIDTH },
        height: { ideal: CAPTURE_FRAME_HEIGHT },
      },
    });
    expect(getUserMedia).toHaveBeenNthCalledWith(2, {
      audio: false,
      video: {
        facingMode: { exact: 'environment' },
        width: { ideal: CAPTURE_FRAME_WIDTH },
        height: { ideal: CAPTURE_FRAME_HEIGHT },
      },
    });
    expect(previewIsMirrored('user')).toBe(true);
    expect(previewIsMirrored('environment')).toBe(false);
  });

  it('requests a larger preset with the same exact facingMode switch', async () => {
    const stream = { id: 'camera' } as unknown as MediaStream;
    const getUserMedia: GetUserMedia = vi.fn(() => Promise.resolve(stream));

    await openCamera(getUserMedia, 'environment', { width: 1920, height: 1080 });

    expect(getUserMedia).toHaveBeenCalledWith({
      audio: false,
      video: {
        facingMode: { exact: 'environment' },
        width: { ideal: 1920 },
        height: { ideal: 1080 },
      },
    });
  });

  it('rejects a quality outside 0..1 and a video that has no frame yet', async () => {
    const video = fakeVideo(100, 100);
    const recorded = recordingCanvas(null);

    await expect(captureFrame(video, 1.1, recorded.canvas)).rejects.toBeInstanceOf(RangeError);
    await expect(captureFrame(video, Number.NaN, recorded.canvas)).rejects.toBeInstanceOf(
      RangeError,
    );
    expect(recorded.drawImage).not.toHaveBeenCalled();
    expect(recorded.toBlob).not.toHaveBeenCalled();

    await expect(captureFrame(video, QUALITY, recorded.canvas)).rejects.toBeInstanceOf(
      CaptureFrameError,
    );
  });

  it('throws RangeError when the video width is 0 and does not encode a JPEG', async () => {
    const recorded = recordingCanvas(new Blob([Uint8Array.from([1])], { type: JPEG_MIME_TYPE }));

    await expect(captureFrame(fakeVideo(0, 720), QUALITY, recorded.canvas)).rejects.toBeInstanceOf(
      RangeError,
    );
    expect(recorded.drawImage).not.toHaveBeenCalled();
    expect(recorded.toBlob).not.toHaveBeenCalled();
    expect(recorded.canvas.width).toBe(0);
    expect(recorded.canvas.height).toBe(0);
  });
});
