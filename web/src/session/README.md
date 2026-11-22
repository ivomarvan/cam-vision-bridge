# Peer session

`peerSession.ts` connects to the Python peer id, sends protocol v1 `hello`, and posts JPEG frames.

PeerJS is injected (`createPeer`). Unit tests pass a fake and do not open a socket. The browser factory is `importPeerJsFactory`, which constructs PeerJS 1.5.4. Connect options are `serialization: "raw"` and `reliable: true`. When the data channel opens, `binaryType` is set to `arraybuffer` and `hello` (`v: 1`, `t: "hello"`) is sent once. `setCaptureSize` changes the width and height on later frame headers and does not send another `hello`. The module does not add a `browser` field to the offer.

`welcome` with `v` other than 1 sets status `version-mismatch` and further `sendFrame` calls do nothing. After `welcome` v1, at most one frame is in flight (`DEFAULT_IN_FLIGHT` is 1) until `result` or `error`. A JPEG larger than 16384 bytes is split with `splitFrame`. There is no camera DOM in this module.
