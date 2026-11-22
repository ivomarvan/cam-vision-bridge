/**
 * Parse PeerJS peer id from a URL hash fragment (`#peer=<id>`).
 *
 * @param hash - Full hash including optional leading `#`, or empty when absent.
 * @returns Peer id string, or `null` when missing or empty.
 */
export function peerIdFromHash(hash: string): string | null {
  const body = hash.startsWith('#') ? hash.slice(1) : hash;
  if (body.length === 0) {
    return null;
  }
  const peer = new URLSearchParams(body).get('peer');
  if (peer === null || peer.length === 0) {
    return null;
  }
  return peer;
}