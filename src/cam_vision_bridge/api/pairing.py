"""Pairing URL a phone can open, and the QR code that carries it.

The peer id is already inside the URL fragment. This module only makes the host
reachable from another device: a loopback address is replaced with the IPv4
address of this computer's default route.
"""

from __future__ import annotations

import socket
import sys
from urllib.parse import urlsplit, urlunsplit

import qrcode  # type: ignore[import-untyped]  # qrcode==8.2 has no type stubs.

DEV_PAGE_PORT = 5173
DEV_PAGE_PATH = "/cam-vision-bridge/v1/"

_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
# Documentation range. UDP connect selects a route and does not send a packet.
_ROUTE_PROBE = ("192.0.2.1", 9)


def lan_ipv4() -> str:
    """Return the IPv4 address other devices on this LAN can use to reach us.

    Returns:
        Dotted IPv4 address of the default route, or another non-loopback address.

    Raises:
        RuntimeError: If every discovered address is loopback or link-local.
    """
    routed = _routed_ipv4()
    if _usable_lan(routed):
        return routed
    for candidate in _hostname_ipv4s():
        if _usable_lan(candidate):
            return candidate
    raise RuntimeError("no LAN IPv4 address is available for the pairing QR")


def local_page_url(port: int = DEV_PAGE_PORT, path: str = DEV_PAGE_PATH) -> str:
    """Build the dev-server page URL using this computer's LAN address.

    Args:
        port: TCP port of the Vite page.
        path: Absolute path of the phone page, without a fragment.

    Returns:
        ``http://<lan-ip>:<port><path>`` with no ``#peer=`` fragment.

    Raises:
        RuntimeError: If :func:`lan_ipv4` cannot find an address.
        ValueError: If ``port`` is outside 1..65535 or ``path`` is empty.
    """
    if not 1 <= port <= 65535:
        raise ValueError("port must be in 1..65535")
    if path == "":
        raise ValueError("path must be non-empty")
    suffix = path if path.startswith("/") else f"/{path}"
    return f"http://{lan_ipv4()}:{port}{suffix}"


def url_for_phone(url: str, host: str | None = None) -> str:
    """Return ``url`` with a loopback host replaced by a LAN address.

    A URL that already names a non-loopback host is returned unchanged.
    ``host`` skips discovery so tests can pin the address.

    Args:
        url: Absolute page URL. The fragment, path, and port are kept.
        host: Address to write instead of loopback. ``None`` calls :func:`lan_ipv4`.

    Returns:
        URL a device other than this computer can open.

    Raises:
        ValueError: If ``url`` is empty or breaks across lines.
        RuntimeError: If a replacement is required and no LAN address exists.
    """
    _require_single_line(url)
    parts = urlsplit(url)
    if parts.hostname not in _LOOPBACK_HOSTS:
        return url
    replacement = host if host is not None else lan_ipv4()
    netloc = f"{replacement}:{parts.port}" if parts.port is not None else replacement
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def show_pairing_qr(url: str, host: str | None = None) -> str:
    """Print a pairing URL and an ASCII QR code of that same URL.

    Loopback hosts are rewritten first, so the scan opens this computer from
    the phone or from another camera on the LAN. The peer id stays in the
    fragment. The write is user-facing output, not a log line.

    Args:
        url: Absolute page URL, including the ``#peer=`` fragment.
        host: Optional LAN address used when ``url`` is loopback. Tests pass it.

    Returns:
        The URL that was printed and encoded.

    Raises:
        ValueError: If ``url`` is empty or contains a newline.
        RuntimeError: If a loopback URL cannot be rewritten.
    """
    reachable = url_for_phone(url, host)
    print(reachable, flush=True)
    code = qrcode.QRCode()
    code.add_data(reachable)
    code.make(fit=True)
    code.print_ascii(out=sys.stdout)
    sys.stdout.flush()
    return reachable


def _require_single_line(url: str) -> None:
    if url == "" or any(char in url for char in "\n\r"):
        raise ValueError("url must be a single non-empty line")


def _usable_lan(address: str) -> bool:
    return address != "" and not address.startswith("127.") and not address.startswith("169.254.")


def _routed_ipv4() -> str:
    """Ask the OS which source address the default route would use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(_ROUTE_PROBE)
            address = sock.getsockname()[0]
    except OSError:
        return ""
    return address if isinstance(address, str) else ""


def _hostname_ipv4s() -> list[str]:
    """Return IPv4 addresses the hostname resolves to, without duplicates."""
    found: list[str] = []
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM)
    except socket.gaierror:
        return found
    for info in infos:
        sockaddr = info[4]
        ip = sockaddr[0]
        if isinstance(ip, str) and ip not in found:
            found.append(ip)
    return found
