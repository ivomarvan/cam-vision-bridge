export interface Point {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

/**
 * Maps normalized frame coordinates to pixel coordinates in a view that displays
 * the frame with object-fit contain (letterboxing unused bands).
 *
 * Points outside 0..1 are not clamped; callers receive them only from validated protocol data.
 *
 * @param point - Normalized x/y relative to the sent frame.
 * @param view - View element size in CSS pixels.
 * @param frame - Intrinsic frame width and height in pixels.
 * @param mirrorX - When true, flip x about the image center (front-facing camera).
 * @returns Pixel coordinates in the view element.
 * @throws {RangeError} When view width or height is negative.
 */
export function mapPoint(
  point: Point,
  view: Size,
  frame: Size,
  mirrorX: boolean,
): Point {
  if (view.width < 0 || view.height < 0) {
    throw new RangeError('view width and height must be non-negative');
  }

  let x = point.x;
  if (mirrorX) {
    x = 1 - x;
  }

  const scale = Math.min(view.width / frame.width, view.height / frame.height);
  const renderedWidth = frame.width * scale;
  const renderedHeight = frame.height * scale;
  const offsetX = (view.width - renderedWidth) / 2;
  const offsetY = (view.height - renderedHeight) / 2;

  return {
    x: offsetX + x * renderedWidth,
    y: offsetY + point.y * renderedHeight,
  };
}