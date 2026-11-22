from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from lantransfer import __version__
from lantransfer.network import get_local_ip, render_qr_ascii
from lantransfer.security import generate_token
from lantransfer.server import TransferHTTPServer, TransferState


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lantransfer",
        description="Bidirectional, QR-code powered local network file and text transfer.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional files or folders to share from this PC to your phone.",
    )
    parser.add_argument(
        "-d",
        "--dir",
        default="./lantransfer_received",
        help="Directory where files uploaded from your phone will be saved (default: ./lantransfer_received).",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8765,
        help="Port to bind on (default: 8765, falls back to a random free port if busy).",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Override auto-detected local IP address.",
    )
    parser.add_argument(
        "-t",
        "--text",
        default=None,
        help="Optional initial text or link to share with your phone.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _bind_server(state: TransferState, preferred_port: int) -> TransferHTTPServer:
    try:
        return TransferHTTPServer(("0.0.0.0", preferred_port), state)
    except OSError:
        return TransferHTTPServer(("0.0.0.0", 0), state)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    local_ip = args.host or get_local_ip()
    token = generate_token()
    upload_dir = Path(args.dir).expanduser().resolve()

    state = TransferState(
        token=token,
        upload_dir=upload_dir,
        host_label=local_ip,
        on_event=lambda msg: print(msg, flush=True),
    )

    for raw_path in args.paths:
        try:
            state.add_shared_path(Path(raw_path))
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.text:
        state.add_note("PC", args.text)

    server = _bind_server(state, args.port)
    actual_port = server.server_address[1]
    url = f"http://{local_ip}:{actual_port}/?token={token}"

    print("\n" + "=" * 54)
    print(f"  lantransfer v{__version__} — Scan QR code with your phone")
    print("=" * 54)
    print(render_qr_ascii(url))
    print(f"  URL       : {url}")
    print(f"  Save Dir  : {upload_dir}")
    print(f"  Shared    : {len(state.shared)} item(s)")
    print("  Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down lantransfer...")
    finally:
        server.shutdown()
        server.server_close()
        state.cleanup()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
