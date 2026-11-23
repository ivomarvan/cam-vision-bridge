# qrdet and WeChat QR

Both detectors run on the same 2×2 overlapping tiles. qrdet is green
(`#39d353`). WeChat QR is amber (`#ffb000`). Panel lines start with the
detector name.

- Detector: [qrdet](https://github.com/Eric-Canas/qrdet) through
  [QReader](https://github.com/Eric-Canas/qreader)
- Detector: [WeChatQRCode](https://docs.opencv.org/5.x/d5/d04/classcv_1_1wechat__qrcode_1_1WeChatQRCode.html)
  in OpenCV (`cv2.wechat_qrcode_WeChatQRCode`). OpenCV 5 loads the ONNX
  weights `detect.onnx` and `sr.onnx`.

Install the qrdet environment, then add the contrib build. That replaces the
plain `opencv-python` wheel, which does not contain WeChat QR.

```bash
.venv-qrdet/bin/pip install opencv-contrib-python==5.1.0.95
.venv-qrdet/bin/python examples/qrdet_wechat/run_phone.py
.venv-qrdet/bin/python examples/qrdet_wechat/run_webcam.py
```

The first run downloads `detect.onnx` and `sr.onnx` into `.models/` and checks
their SHA-256. The phone
capture size is 1920×1080. Pass `--camera N` on the webcam script to select
the USB camera. Press `q` or close the window to stop.
