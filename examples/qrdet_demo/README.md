# QR detection demo

Reads QR codes from the phone frames and sends a quad plus the decoded text.

Detector: [qrdet](https://github.com/Eric-Canas/qrdet) (YOLOv8 QR segmentation).
Decoding goes through [QReader](https://github.com/Eric-Canas/qreader), which uses
that detector and then pyzbar.

```bash
python3.12 -m venv .venv-qrdet
.venv-qrdet/bin/pip install -e .
.venv-qrdet/bin/pip install -r examples/qrdet_demo/requirements.txt
.venv-qrdet/bin/python examples/qrdet_demo/run_demo.py
```

The webcam script is the same detector, drawn in a window on this PC:

```bash
.venv-qrdet/bin/python examples/qrdet_demo/run_webcam.py
```

`run_webcam.py` draws the same detections in a window on this PC. Press `q`
to stop. `--list-cameras` prints the devices. `--camera N` selects one, which
is how a USB camera is chosen instead of the built-in laptop camera.

Use Python 3.12 for this environment. A bare `python` may be older, and the
library does not install on Python 3.10. Torch stays in this environment, not
in the library one. The script starts the phone page on port 5173 when it is
not already running, then prints one QR code.
Scan it with the phone, then point the phone at a QR code. The page draws the
quad and shows the decoded text in the panel. Chrome still needs the insecure
origin listed in [`../README.md`](../README.md).

The first run downloads the detector weights.
