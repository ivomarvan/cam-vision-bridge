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
