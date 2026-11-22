from __future__ import annotations

import io
import socket


def get_local_ip() -> str:
    """
    Detect the primary LAN IPv4 address of this machine without sending network traffic.
    Falls back to 127.0.0.1 if no network interface is available.
    """
    for probe in (("10.255.255.255", 1), ("8.8.8.8", 80)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(probe)
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
        except OSError:
            continue
        finally:
            sock.close()
    return "127.0.0.1"


def render_qr_ascii(url: str) -> str:
    """Render a scannable Unicode QR code for terminal display."""
    import qrcode

    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)

    buf = io.StringIO()
    qr.print_ascii(out=buf, invert=True)
    return buf.getvalue()
