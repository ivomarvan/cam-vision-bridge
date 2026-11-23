# WeChat QR alone

One WeChat pass on the whole frame. No qrdet, and no tile grid. The combined
example runs both detectors four times each, which is why this one is the
faster way to try WeChat.

- Detector: [WeChatQRCode](https://docs.opencv.org/5.x/d5/d04/classcv_1_1wechat__qrcode_1_1WeChatQRCode.html)
  in OpenCV (`cv2.wechat_qrcode_WeChatQRCode`)

Install the qrdet environment first (`examples/qrdet_demo/README.md`), then
the contrib build from [`../qrdet_wechat/README.md`](../qrdet_wechat/README.md).

```bash
.venv-qrdet/bin/python examples/wechat_qr/run_phone.py
.venv-qrdet/bin/python examples/wechat_qr/run_webcam.py --list-cameras
.venv-qrdet/bin/python examples/wechat_qr/run_webcam.py --camera 4
```

The phone capture size is 1280×720. Strokes are amber (`#ffb000`). The webcam
window keeps showing the live camera while detection updates the boxes.
Press `q` or close the window to stop.
