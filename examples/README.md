# Examples

Small programs that use `cam_vision_bridge`. They are not part of the library API.

## `run_phone.py`

Starts the phone page when port 5173 is closed, then calls `show_pairing_qr`.
The QR code contains this computer's LAN address and the peer id. Scan it with
the phone or with a PC camera. A box labeled `pc` is sent back on every frame.

```bash
.venv/bin/python examples/run_phone.py
```

The page is plain HTTP. Chrome on the phone will not open the camera until that
exact origin (`http://<shown-ip>:5173`) is listed under `chrome://flags` as an
insecure origin treated as secure. Stop the script with Ctrl+C.

## `run_webcam.py`

The same box as `run_phone.py`, drawn on a webcam window on this PC. Press
`q` to stop. The window needs an OpenCV build with a GUI, so use the qrdet
environment rather than the library venv.

```bash
.venv-qrdet/bin/python examples/run_webcam.py --list-cameras
.venv-qrdet/bin/python examples/run_webcam.py --camera 2
```

`--camera N` is the same on every webcam script. When more than one device
returns a frame and `--camera` is omitted, the script prints the list and
stops instead of opening the built-in camera. The window follows the camera
while detection runs beside it, so a slow detector does not freeze the picture.

## `qrdet_demo/`

QR detection. Torch stays out of the library venv. Phone script and webcam
script share the detector. See [`qrdet_demo/README.md`](qrdet_demo/README.md).

## `qrdet_tiled/`

The same detector on a 2×2 overlap grid at 1920×1080. See
[`qrdet_tiled/README.md`](qrdet_tiled/README.md).

## `qrdet_wechat/`

Tiled qrdet in green and tiled WeChat QR in amber. See
[`qrdet_wechat/README.md`](qrdet_wechat/README.md).

## `wechat_qr/`

WeChat QR once per frame, without qrdet and without tiles. See
[`wechat_qr/README.md`](wechat_qr/README.md).

## `wechat_tiled/`

The largest camera frame, cut into tiles WeChat can detect without shrinking
them. See [`wechat_tiled/README.md`](wechat_tiled/README.md).
