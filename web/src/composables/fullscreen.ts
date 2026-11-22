/**
 * Whether the standard Fullscreen API can be used on this document.
 *
 * @param doc - Usually `document`; tests pass a stub.
 * @returns `true` when `requestFullscreen` may be called.
 */
export function isFullscreenAvailable(doc: Document): boolean {
  return doc.fullscreenEnabled;
}

/**
 * Enter or leave fullscreen on the given element.
 *
 * @param element - Root layout element to expand.
 * @param doc - Document for fullscreen exit checks.
 */
export async function toggleFullscreen(element: HTMLElement, doc: Document): Promise<void> {
  if (!isFullscreenAvailable(doc)) {
    return;
  }
  if (doc.fullscreenElement !== null) {
    await doc.exitFullscreen();
    return;
  }
  await element.requestFullscreen();
}