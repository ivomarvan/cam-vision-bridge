# WeChat QR on native-sized tiles

The camera frame is as large as the camera will give. WeChat's detector is a
384×384 network. A bigger picture is scaled down to about 400×400 before that
network runs, so this example cuts the frame into overlapping tiles that stay
at or under 384 pixels on each side. Each hit is in that tile's coordinates.
Those coordinates are mapped back onto the full frame. The decoded text is
unchanged.

- Detector: [WeChatQRCode](https://docs.opencv.org/5.x/d5/d04/classcv_1_1wechat__qrcode_1_1WeChatQRCode.html)
  in OpenCV (`cv2.wechat_qrcode_WeChatQRCode`)

Install the qrdet environment and the contrib build
([`../qrdet_wechat/README.md`](../qrdet_wechat/README.md)).

```bash
.venv-qrdet/bin/python examples/wechat_tiled/run_phone.py
.venv-qrdet/bin/python examples/wechat_tiled/run_webcam.py --camera 4
```

The phone page will not send a side longer than 1920, so the phone script
asks for 1920×1080. The webcam script asks the device for its largest mode.
A C920 then delivers 1920×1080 MJPEG; without that request it stays at
640×480. Strokes are amber (`#ffb000`). A 1920×1080 frame is a 4×6 tile
grid, so this example is thorough rather than fast. The webcam window still
follows the camera while the tiles run.
