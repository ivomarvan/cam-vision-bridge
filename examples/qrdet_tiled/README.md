# Tiled qrdet demo

Same detector as [`../qrdet_demo`](../qrdet_demo/README.md), on a 2×2 grid with
20% overlap. Quads are mapped back to the full frame and duplicates on the
overlap are dropped. The stroke is green (`#39d353`).

Detector: [qrdet](https://github.com/Eric-Canas/qrdet) through
[QReader](https://github.com/Eric-Canas/qreader).

Install the qrdet environment first (`examples/qrdet_demo/README.md`), then:

```bash
.venv-qrdet/bin/python examples/qrdet_tiled/run_phone.py
.venv-qrdet/bin/python examples/qrdet_tiled/run_webcam.py
```

The phone capture size is 1920×1080. The webcam script draws on a window on
this PC. Pass `--camera N` to select the USB camera. Press `q` or close the
window to stop.
