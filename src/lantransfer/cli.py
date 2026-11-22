from __future__ import annotations

import argparse
import os
import sys
import threading
from pathlib import Path
from typing import Sequence

from lantransfer import __version__
from lantransfer.network import get_local_ip, render_qr_ascii
from lantransfer.security import generate_token
from lantransfer.server import TransferHTTPServer, TransferState
from lantransfer.shortcuts import install_shortcut


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
        "--setup",
        action="store_true",
        help="Create a one-click desktop/menu shortcut for your operating system and exit.",
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


def _handle_console_line(state: TransferState, line: str) -> None:
    cleaned = line.strip()
    if not cleaned:
        return

    candidate_str = cleaned
    if (candidate_str.startswith("'") and candidate_str.endswith("'")) or (
        candidate_str.startswith('"') and candidate_str.endswith('"')
    ):
        candidate_str = candidate_str[1:-1]

    candidate_path = Path(candidate_str).expanduser()
    if not candidate_path.exists() and os.name != "nt":
        unescaped = Path(candidate_str.replace("\\ ", " ")).expanduser()
        if unescaped.exists():
            candidate_path = unescaped

    if candidate_path.exists():
        item = state.add_shared_path(candidate_path)
        kind = "folder" if item.is_dir else "file"
        state.emit(f"[SHARED] Added {kind}: {item.path.name} (visible on phone)")
    else:
        state.add_note("PC", cleaned)


def _start_console_listener(state: TransferState) -> None:
    if not sys.stdin or not sys.stdin.isatty():
        return

    def _loop() -> None:
        while True:
            try:
                line = sys.stdin.readline()
            except OSError:
                break
            if not line:
                break
            _handle_console_line(state, line)

    threading.Thread(target=_loop, daemon=True).start()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.setup:
        try:
            created = install_shortcut()
            print(f"Created LAN Transfer shortcut at: {created}")
            return 0
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

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
    print("  Tip       : Drag & drop a file or type text here + Enter to share live.")
    print("  Press Ctrl+C to stop.\n")

    _start_console_listener(state)

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
