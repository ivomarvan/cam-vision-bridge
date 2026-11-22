# ADR-002: JSON shape of protocol v1 geometry and metrics

**Status**: Accepted
**Date**: 2026-11-22

## Context

E020.T020 makes Pydantic models the only source of the v1 contract and commits
the JSON Schema generated from them. The task spec names every message field and
the result tags. It states cardinalities for point lists ("exactly four", "at
least three", "at least two") and says each coordinate is in 0..1, but it does
not spell the JSON key that holds those points, nor the key that holds the
metrics list. Keypoint edges are specified as pairs of indexes under `edges`.

Later tasks and the phone UI will bind to this schema. Two encodings would be a
second protocol.

## Decision

- A point is an object `{"x": <0..1>, "y": <0..1>}`.
- `quad`, `polygon`, `keypoints`, and `polyline` store those objects in `points`.
- A keypoint edge is a JSON array of two indexes, `[i, j]`, each `i >= 0`.
  The model does not check that the index falls inside `points`; the spec asks
  for a pair of indexes, not a graph check.
- A `metrics` item stores `{name, value}` objects in `metrics`. `value` is a
  float with no 0..1 clamp. `label` and `score` exist only on the geometric
  tags, not on `text` or `metrics`.
- Result items do not carry `v`. The `result` message does.
- The committed schema is the discriminated union of every JSON message:
  `hello`, `welcome`, `error`, `frame`, and `result`. The frame header is JSON
  inside the binary chunk; the JPEG bytes are outside this schema.
- Unknown fields fail validation (`extra=forbid`). A parsed model is frozen.

`part`, `parts`, and `total_bytes` stay unconstrained integers on `FrameHeader`.
The frame codec (E020.T030) owns those limits.

## Consequences

- E030 reads `FrameHeader` and must not add a second header shape.
- Frontend types generated from `schema/cam-vision-bridge-v1.schema.json` use
  `points`, `edges` as index pairs, and `metrics` as `{name, value}` rows.
- Requested `welcome` width and height are optional integers with no lower
  bound in v1. Only `fps`, when present, is an integer ≥ 1. Hello capture
  `width` and `height` are integers ≥ 1.
