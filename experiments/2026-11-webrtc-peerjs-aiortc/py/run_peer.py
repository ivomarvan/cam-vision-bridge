"""CLI: register an echo peer with the PeerJS cloud and print a QR code.

Run from ``experiments/2026-11-webrtc-peerjs-aiortc/py`` so the default
``--results-dir ../results`` lands in the spike results directory. Stop the
process with Ctrl+C; open peer connections and the signaling socket are closed
on the way out.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import secrets
import socket
from pathlib import Path

import qrcode

from echo_peer import EchoPeer
from peerjs_signaling import PeerJsSignaling, SignalingError
from results_writer import ResultsWriter

logger = logging.getLogger(__name__)

_DEFAULT_HOST = "0.peerjs.com"
_DEFAULT_PORT = 443
_DEFAULT_KEY = "peerjs"
_DEFAULT_RESULTS_DIR = "../results"
_LAN_ROUTE_ADDR = ("8.8.8.8", 80)
_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


def generate_peer_id() -> str:
    """Return a new PeerJS id with the ``cvb-`` prefix and 16 hex characters.

    Returns:
        An id such as ``cvb-0123456789abcdef``. Collision is handled by the
        server as ``ID-TAKEN``; the process then exits.
    """
    return "cvb-" + secrets.token_hex(8)


def discover_lan_ip() -> str:
    """Return this host's LAN address without transmitting a packet.

    A UDP ``connect`` only selects the outbound route. No datagram is sent.

    Returns:
        The chosen IPv4 address, or ``127.0.0.1`` when no route is available.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(_LAN_ROUTE_ADDR)
        address = sock.getsockname()[0]
    except OSError as exc:
        logger.warning("lan_ip_discovery_failed error=%s fallback=127.0.0.1", exc)
        return "127.0.0.1"
    finally:
        sock.close()
    if not address:
        return "127.0.0.1"
    return str(address)


def main() -> None:
    """Parse arguments, register with PeerJS, and serve until Ctrl+C."""
    args = _parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        asyncio.run(_async_main(args))
    except KeyboardInterrupt:
        logger.info("shutdown reason=keyboard_interrupt")
    except SignalingError as exc:
        logger.error("signaling_failed reason=%s", exc.reason)
        raise SystemExit(1) from exc


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PeerJS echo peer for the WebRTC spike."
    )
    parser.add_argument("--host", default=_DEFAULT_HOST, help="PeerJS signaling host.")
    parser.add_argument(
        "--port", type=int, default=_DEFAULT_PORT, help="PeerJS signaling port."
    )
    parser.add_argument("--key", default=_DEFAULT_KEY, help="PeerJS API key.")
    parser.add_argument(
        "--page-url",
        default=None,
        help="Measurement page base URL. Default: http://<LAN-IP>:8080/",
    )
    parser.add_argument(
        "--results-dir",
        default=_DEFAULT_RESULTS_DIR,
        help="Directory for runs.csv and frames/. Default: ../results",
    )
    parser.add_argument("--log-level", default="INFO", choices=_LOG_LEVELS)
    return parser.parse_args()


async def _async_main(args: argparse.Namespace) -> None:
    peer_id = generate_peer_id()
    page_url = args.page_url if args.page_url else f"http://{discover_lan_ip()}:8080/"
    signaling = PeerJsSignaling(
        peer_id=peer_id,
        host=args.host,
        port=args.port,
        key=args.key,
    )
    peer = EchoPeer(
        peer_id=peer_id,
        signaling=signaling,
        results=ResultsWriter(Path(args.results_dir)),
    )
    try:
        await signaling.connect()
        _print_pairing_url(f"{page_url}#peer={peer_id}")
        async for message in signaling:
            await peer.handle_signaling_message(message)
    finally:
        await peer.close()
        await signaling.close()


def _print_pairing_url(url: str) -> None:
    """Print the page URL and an ASCII QR code. This is user-facing output."""
    print(url, flush=True)
    code = qrcode.QRCode(border=1)
    code.add_data(url)
    code.make(fit=True)
    code.print_ascii(invert=True)


if __name__ == "__main__":
    main()
