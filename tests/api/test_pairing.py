"""LAN rewrite of the pairing URL and the QR printed from it."""

from __future__ import annotations

import pytest

from cam_vision_bridge.api.pairing import local_page_url, show_pairing_qr, url_for_phone

_LOOPBACK = "http://127.0.0.1:5173/cam-vision-bridge/v1/#peer=cvb-aa"
_LAN = "http://192.0.2.10:5173/cam-vision-bridge/v1/#peer=cvb-aa"


def test_url_for_phone_replaces_loopback_and_keeps_the_fragment() -> None:
    assert url_for_phone(_LOOPBACK, "192.0.2.10") == _LAN


def test_url_for_phone_leaves_a_public_host_unchanged() -> None:
    public = "https://ivomarvan.github.io/cam-vision-bridge/v1/#peer=cvb-aa"
    assert url_for_phone(public, "192.0.2.10") == public


def test_local_page_url_uses_the_discovered_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cam_vision_bridge.api.pairing.lan_ipv4", lambda: "192.0.2.10")
    assert local_page_url() == "http://192.0.2.10:5173/cam-vision-bridge/v1/"


def test_show_pairing_qr_prints_the_reachable_url(capsys: pytest.CaptureFixture[str]) -> None:
    printed = show_pairing_qr(_LOOPBACK, host="192.0.2.10")
    out = capsys.readouterr().out
    assert printed == _LAN
    assert _LAN in out
    assert "127.0.0.1" not in out
    assert "█" in out


def test_show_pairing_qr_rejects_a_blank_url() -> None:
    with pytest.raises(ValueError, match="single non-empty line"):
        show_pairing_qr("")
