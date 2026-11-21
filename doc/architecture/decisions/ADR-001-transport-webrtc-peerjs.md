# ADR-001: Keep WebRTC DataChannel via PeerJS for the MVP transport

**Status**: Accepted
**Date**: 2026-11-22

## Context

DECISIONS #2 chose WebRTC (`aiortc` on the PC, PeerJS in the browser, public PeerJS
cloud for signaling) before any code existed. Epic E010 measured that choice on a
real phone instead of treating it as an assumption.

The spike ran Chrome on Android 10 (Chrome 157) and the Python echo peer on the same
Wi-Fi. Signaling used `0.peerjs.com`. Frames were synthetic 640×480 JPEGs. The page
and the peer agreed on PeerJS 1.5.4 (DECISIONS #6: the offer payload has no `browser`
field).

## Decision

Keep `PeerJsWebRtcTransport` as the MVP transport. Do not switch the MVP to WebSocket.

Evidence from the Android matrix on 2026-11-22, same LAN, UDP:

- The DataChannel opened. Connect time through the public cloud was 5.3 s.
- The selected ICE pair was `host/prflx` on the first run and `host/host` after that.
  TURN was not used.
- Quality 0.6, one frame in flight: 23.5–24.1 FPS, median RTT 17–18 ms, JPEG decode
  about 4 ms. That is inside the project budget (≥ 10 FPS, median latency ≤ 200 ms).
- Sent frames matched echoed frames on every run that wrote a `runs.csv` row.
- The no-split probe (about 21 KB, under the 64 KB SCTP limit) completed 429 echoes
  at about 21 FPS and median RTT 19 ms. It did not drop the connection.

## Consequences

- E020 implements the production peer from this spike. It must not require an `OFFER`
  field `browser`.
- Chunking stays (DECISIONS #3). This measurement never sent a frame over 64 KB
  (observed JPEGs were 15–22 KB), so the over-limit path is still an untested
  requirement, not a measured result.
- Default flow control for the phone should be one frame in flight. Two frames in
  flight did not raise FPS.
- A multi-minute gap in the later Android runs, with RTT still around 20 ms and no
  losses, means the phone stopped offering frames. E030 already plans a Wake Lock;
  that need stands.
- Pairing still needs Internet for the PeerJS cloud and STUN. A WebSocket transport
  remains a later option behind `Transport`, not the MVP.
- Safari on iOS was not measured. mDNS candidate translation in `aioice` did not
  block this Chrome Android session; it stays a risk for other browsers.
