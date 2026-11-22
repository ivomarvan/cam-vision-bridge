/**
 * Allowed phone capture sizes and the bitmap that a JPEG may actually use.
 *
 * The phone offers three presets. A `welcome` from the PC picks the nearest
 * one. The encoded frame follows the sensor, not a stretched preset.
 */

/** One width and height in pixels. */
export interface CaptureSize {
  readonly width: number;
  readonly height: number;
}

/**
 * Presets the phone may request, smallest first.
 * The default is the first entry.
 */
export const CAPTURE_PRESETS: readonly CaptureSize[] = [
  { width: 640, height: 480 },
  { width: 1280, height: 720 },
  { width: 1920, height: 1080 },
];

/** Longest side of an encoded bitmap. Larger sensor frames scale down to this. */
export const MAX_BITMAP_LONG_SIDE = 1920;

function presetAt(index: number): CaptureSize {
  const preset = CAPTURE_PRESETS[index];
  if (preset === undefined) {
    throw new Error(`Capture preset missing: index=${String(index)}`);
  }
  return preset;
}

/** Size used before any `welcome` and when `welcome` omits a dimension. */
export const DEFAULT_CAPTURE_SIZE: CaptureSize = presetAt(0);

function pixelCount(size: CaptureSize): number {
  return size.width * size.height;
}

/**
 * Preset whose pixel count is closest to `width * height`.
 *
 * A tie keeps the smaller count. Presets are stored smallest-first, so the
 * first minimum distance wins.
 *
 * @param width - Requested width in pixels.
 * @param height - Requested height in pixels.
 * @returns One of {@link CAPTURE_PRESETS}.
 */
export function nearestPreset(width: number, height: number): CaptureSize {
  const pixels = width * height;
  let best: CaptureSize = DEFAULT_CAPTURE_SIZE;
  let bestDistance = Math.abs(pixels - pixelCount(best));
  for (const preset of CAPTURE_PRESETS) {
    const distance = Math.abs(pixels - pixelCount(preset));
    if (distance < bestDistance) {
      best = preset;
      bestDistance = distance;
    }
  }
  return { width: best.width, height: best.height };
}

/**
 * Preset requested by one `welcome`, or null when a dimension is absent.
 *
 * Null and undefined are both absent. Zero is present and is mapped like any
 * other number.
 *
 * @param width - `welcome.width`.
 * @param height - `welcome.height`.
 * @returns Nearest preset, or null when either dimension is missing.
 */
export function sizeFromWelcome(
  width: number | null | undefined,
  height: number | null | undefined,
): CaptureSize | null {
  if (width === null || width === undefined || height === null || height === undefined) {
    return null;
  }
  return nearestPreset(width, height);
}

/**
 * Preset to keep after a `welcome`.
 *
 * An incomplete welcome (one dimension or both missing) returns `current`
 * unchanged. A complete welcome returns the nearest preset.
 *
 * @param current - Preset already in use.
 * @param width - `welcome.width`.
 * @param height - `welcome.height`.
 * @returns Next preset for camera constraints and later frames.
 */
export function presetAfterWelcome(
  current: CaptureSize,
  width: number | null | undefined,
  height: number | null | undefined,
): CaptureSize {
  const requested = sizeFromWelcome(width, height);
  if (requested === null) {
    return current;
  }
  return requested;
}

function assertPositiveDimension(value: number, label: string): void {
  if (!Number.isFinite(value) || value <= 0) {
    throw new RangeError(`${label} must be a positive number: value=${String(value)}`);
  }
}

function positiveRounded(value: number): number {
  return Math.max(1, Math.round(value));
}

/**
 * Canvas size for one JPEG.
 *
 * Uses the real video size. The preset is the size requested from the camera;
 * it is checked, and it is not stretched over the sensor. When the longer
 * video side exceeds {@link MAX_BITMAP_LONG_SIDE}, both sides scale by the
 * same factor so that longer side becomes 1920.
 *
 * @param videoWidth - `HTMLVideoElement.videoWidth`.
 * @param videoHeight - `HTMLVideoElement.videoHeight`.
 * @param preset - Preset currently requested from the camera.
 * @returns Integer canvas width and height, each at least 1.
 * @throws {RangeError} When a video or preset dimension is not positive and finite.
 */
export function bitmapSize(
  videoWidth: number,
  videoHeight: number,
  preset: CaptureSize,
): CaptureSize {
  assertPositiveDimension(videoWidth, 'videoWidth');
  assertPositiveDimension(videoHeight, 'videoHeight');
  assertPositiveDimension(preset.width, 'preset.width');
  assertPositiveDimension(preset.height, 'preset.height');
  const longSide = Math.max(videoWidth, videoHeight);
  const scale = longSide > MAX_BITMAP_LONG_SIDE ? MAX_BITMAP_LONG_SIDE / longSide : 1;
  return {
    width: positiveRounded(videoWidth * scale),
    height: positiveRounded(videoHeight * scale),
  };
}

/**
 * Bitmap advertised in `hello` before the first encoded frame.
 *
 * A video that has no positive size yet keeps the preset. Otherwise the
 * result is {@link bitmapSize}, so `hello` matches the JPEG that will follow.
 *
 * @param videoWidth - `HTMLVideoElement.videoWidth`, or 0 when no frame exists.
 * @param videoHeight - `HTMLVideoElement.videoHeight`, or 0 when no frame exists.
 * @param preset - Preset currently requested from the camera.
 * @returns Size for the single `hello`.
 */
export function helloBitmap(
  videoWidth: number,
  videoHeight: number,
  preset: CaptureSize,
): CaptureSize {
  if (
    !Number.isFinite(videoWidth) ||
    !Number.isFinite(videoHeight) ||
    videoWidth <= 0 ||
    videoHeight <= 0
  ) {
    return { width: preset.width, height: preset.height };
  }
  return bitmapSize(videoWidth, videoHeight, preset);
}
