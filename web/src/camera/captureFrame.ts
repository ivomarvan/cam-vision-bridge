/**
 * Open the phone camera and encode one preview frame as a JPEG.
 *
 * The bitmap follows the video size from {@link bitmapSize}, not a fixed
 * 640×480 canvas. `getUserMedia` is injected. The JPEG is the sensor image,
 * not a mirrored preview — front-camera mirroring belongs to overlay mapping.
 */

import { DEFAULT_CAPTURE_SIZE, bitmapSize, type CaptureSize } from './captureSize';

/** Default capture width. A frame header uses the bitmap size, which starts here. */
export const CAPTURE_FRAME_WIDTH = DEFAULT_CAPTURE_SIZE.width;

/** Default capture height. A frame header uses the bitmap size, which starts here. */
export const CAPTURE_FRAME_HEIGHT = DEFAULT_CAPTURE_SIZE.height;

/** MIME type passed to `canvas.toBlob`. */
export const JPEG_MIME_TYPE = 'image/jpeg';

export const FACING_MODE = {
  user: 'user',
  environment: 'environment',
} as const;

/** `user` is the front camera, `environment` the rear camera. */
export type FacingMode = (typeof FACING_MODE)[keyof typeof FACING_MODE];

/** Browser `navigator.mediaDevices.getUserMedia`, or a test double. */
export type GetUserMedia = (constraints: MediaStreamConstraints) => Promise<MediaStream>;

/**
 * The current video frame cannot be encoded.
 *
 * Raised when the canvas has no 2D context or `toBlob` returns null.
 * A quality outside 0..1, or a video dimension that is not positive, is a
 * `RangeError` instead.
 */
export class CaptureFrameError extends Error {
  override readonly name = 'CaptureFrameError';
}

/**
 * Whether overlay x must be mirrored for this camera.
 *
 * The encoded JPEG stays unmirrored. The preview and the overlay flip x only
 * for the front camera, inside `mapPoint`.
 *
 * @param facingMode - Camera passed to {@link openCamera}.
 * @returns `true` for the front camera (`user`).
 */
export function previewIsMirrored(facingMode: FacingMode): boolean {
  return facingMode === FACING_MODE.user;
}

/**
 * Constraints for one camera. Audio is off. `facingMode` is exact so a phone
 * switches cameras instead of keeping whichever sensor it opened last.
 * Ideal width and height follow the selected preset.
 *
 * @param facingMode - Front (`user`) or rear (`environment`) camera.
 * @param preset - Size to request. Defaults to 640×480.
 * @returns Constraints for {@link openCamera}.
 */
export function cameraConstraints(
  facingMode: FacingMode,
  preset: CaptureSize = DEFAULT_CAPTURE_SIZE,
): MediaStreamConstraints {
  return {
    audio: false,
    video: {
      facingMode: { exact: facingMode },
      width: { ideal: preset.width },
      height: { ideal: preset.height },
    },
  };
}

/**
 * Open the camera. The factory is injected so unit tests never call a device.
 *
 * @param getUserMedia - `navigator.mediaDevices.getUserMedia` or a fake.
 * @param facingMode - Front (`user`) or rear (`environment`) camera.
 * @param preset - Size to request. Defaults to 640×480.
 * @returns Camera stream. The caller assigns `video.srcObject` and stops the tracks.
 */
export function openCamera(
  getUserMedia: GetUserMedia,
  facingMode: FacingMode,
  preset: CaptureSize = DEFAULT_CAPTURE_SIZE,
): Promise<MediaStream> {
  return getUserMedia(cameraConstraints(facingMode, preset));
}

/**
 * Draw the current video frame at {@link bitmapSize} and encode JPEG.
 *
 * The canvas uses the sensor size. A longer side above 1920 is scaled down
 * with the aspect ratio kept. Assigning `canvas.width` / `height` also clears
 * pixels from the previous frame.
 *
 * @param video - Element with a decoded frame. Width and height must be positive.
 * @param quality - JPEG quality for `toBlob`, from 0 to 1 inclusive.
 * @param canvas - Destination bitmap. Tests pass a fake that records `drawImage`.
 * @param preset - Size requested from the camera. Defaults to 640×480.
 * @returns JPEG blob at the bitmap size.
 * @throws {RangeError} When `quality` is outside 0..1, or a video dimension is
 *   not positive. The rejection is asynchronous because the function is async.
 * @throws {CaptureFrameError} When the 2D context is missing or `toBlob` returns null.
 */
export async function captureFrame(
  video: HTMLVideoElement,
  quality: number,
  canvas: HTMLCanvasElement,
  preset: CaptureSize = DEFAULT_CAPTURE_SIZE,
): Promise<Blob> {
  assertJpegQuality(quality);
  const size = bitmapSize(video.videoWidth, video.videoHeight, preset);
  const context = prepareContext(canvas, size);
  drawVideoFrame(context, video, size);
  return encodeJpeg(canvas, quality);
}

function assertJpegQuality(quality: number): void {
  if (!Number.isFinite(quality) || quality < 0 || quality > 1) {
    throw new RangeError(`JPEG quality must be between 0 and 1: quality=${String(quality)}`);
  }
}

function prepareContext(canvas: HTMLCanvasElement, size: CaptureSize): CanvasRenderingContext2D {
  canvas.width = size.width;
  canvas.height = size.height;
  const context = canvas.getContext('2d');
  if (context === null) {
    throw new CaptureFrameError('Canvas 2D context is unavailable');
  }
  return context;
}

function drawVideoFrame(
  context: CanvasRenderingContext2D,
  video: HTMLVideoElement,
  size: CaptureSize,
): void {
  context.drawImage(
    video,
    0,
    0,
    video.videoWidth,
    video.videoHeight,
    0,
    0,
    size.width,
    size.height,
  );
}

function encodeJpeg(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob === null) {
          reject(new CaptureFrameError('Canvas toBlob returned null'));
          return;
        }
        resolve(blob);
      },
      JPEG_MIME_TYPE,
      quality,
    );
  });
}
