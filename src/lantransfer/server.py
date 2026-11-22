from __future__ import annotations

import datetime
import json
import mimetypes
import shutil
import tempfile
import threading
import urllib.parse
import zipfile
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from lantransfer.security import resolve_unique_path, verify_token
from lantransfer.ui import render_index_html

_CHUNK_SIZE = 64 * 1024  # 64 KB streaming chunks


def _format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


@dataclass
class SharedItem:
    item_id: str
    path: Path
    is_dir: bool
    size: int


@dataclass
class TransferState:
    token: str
    upload_dir: Path
    host_label: str = "LAN"
    shared: dict[str, SharedItem] = field(default_factory=dict)
    notes: list[dict[str, str]] = field(default_factory=list)
    on_event: Callable[[str], None] | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _temp_zips: dict[str, Path] = field(default_factory=dict, repr=False)

    def add_shared_path(self, path: Path) -> SharedItem:
        resolved = path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        with self._lock:
            item_id = str(len(self.shared) + 1)
            is_dir = resolved.is_dir()
            size = 0 if is_dir else resolved.stat().st_size
            item = SharedItem(item_id=item_id, path=resolved, is_dir=is_dir, size=size)
            self.shared[item_id] = item
            return item

    def add_note(self, sender: str, text: str) -> dict[str, str]:
        entry = {
            "sender": sender,
            "text": text,
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
        }
        with self._lock:
            self.notes.append(entry)
        self.emit(f"[NOTE from {sender}] {text}")
        return entry

    def get_download_target(self, item_id: str) -> tuple[Path, str] | None:
        with self._lock:
            item = self.shared.get(item_id)
            if not item:
                return None
            if not item.is_dir:
                return item.path, item.path.name

            cached = self._temp_zips.get(item_id)
            if cached and cached.exists():
                return cached, f"{item.path.name}.zip"

        tmp = Path(tempfile.mkstemp(prefix="lantransfer_", suffix=".zip")[1])
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in item.path.rglob("*"):
                if file_path.is_file():
                    zf.write(file_path, arcname=file_path.relative_to(item.path.parent))

        with self._lock:
            self._temp_zips[item_id] = tmp
        return tmp, f"{item.path.name}.zip"

    def cleanup(self) -> None:
        with self._lock:
            for tmp in self._temp_zips.values():
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass
            self._temp_zips.clear()

    def emit(self, message: str) -> None:
        if self.on_event:
            self.on_event(message)

    def to_public_dict(self) -> dict[str, object]:
        with self._lock:
            files = [
                {
                    "id": item.item_id,
                    "name": item.path.name,
                    "is_dir": item.is_dir,
                    "size": item.size,
                }
                for item in self.shared.values()
            ]
            return {"shared_files": files, "notes": list(self.notes)}


class TransferHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], state: TransferState):
        self.state = state
        super().__init__(server_address, TransferRequestHandler)


class TransferRequestHandler(BaseHTTPRequestHandler):
    server: TransferHTTPServer  # type: ignore[assignment]

    def log_message(self, format: str, *args: object) -> None:
        # Suppress noisy default HTTP logs; clean transfer events are printed via state.emit()
        return

    def _get_query(self) -> tuple[str, dict[str, list[str]]]:
        parsed = urllib.parse.urlsplit(self.path)
        return parsed.path, urllib.parse.parse_qs(parsed.query)

    def _is_authorized(self, query: dict[str, list[str]]) -> bool:
        token = query.get("token", [None])[0] or self.headers.get("X-Auth-Token")
        return verify_token(self.server.state.token, token)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_forbidden(self) -> None:
        self._send_json({"error": "Invalid or missing session token"}, HTTPStatus.FORBIDDEN)

    def do_GET(self) -> None:
        path, query = self._get_query()
        if not self._is_authorized(query):
            self._send_forbidden()
            return

        if path == "/":
            html = render_index_html(self.server.state.token, self.server.state.host_label).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(html)
            return

        if path == "/api/state":
            self._send_json(self.server.state.to_public_dict())
            return

        if path.startswith("/download/"):
            item_id = urllib.parse.unquote(path.removeprefix("/download/"))
            target = self.server.state.get_download_target(item_id)
            if not target:
                self._send_json({"error": "File not found"}, HTTPStatus.NOT_FOUND)
                return

            file_path, download_name = target
            size = file_path.stat().st_size
            mime, _ = mimetypes.guess_type(download_name)
            encoded_name = urllib.parse.quote(download_name)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime or "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header(
                "Content-Disposition",
                f"attachment; filename=\"{download_name}\"; filename*=UTF-8''{encoded_name}",
            )
            self.end_headers()

            with file_path.open("rb") as f:
                shutil.copyfileobj(f, self.wfile, length=_CHUNK_SIZE)

            self.server.state.emit(f"[SENT] {download_name} ({_format_size(size)})")
            return

        self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path, query = self._get_query()
        if not self._is_authorized(query):
            self._send_forbidden()
            return

        if path == "/api/upload":
            raw_name = query.get("filename", ["unnamed_file"])[0]
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json({"error": "Invalid Content-Length"}, HTTPStatus.BAD_REQUEST)
                return

            if content_length < 0:
                self._send_json({"error": "Invalid Content-Length"}, HTTPStatus.BAD_REQUEST)
                return

            upload_dir = self.server.state.upload_dir
            upload_dir.mkdir(parents=True, exist_ok=True)
            dest = resolve_unique_path(upload_dir, raw_name)

            remaining = content_length
            with dest.open("wb") as out:
                while remaining > 0:
                    chunk = self.rfile.read(min(_CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    out.write(chunk)
                    remaining -= len(chunk)

            self.server.state.emit(
                f"[RECEIVED] {dest.name} ({_format_size(content_length)}) -> {dest}"
            )
            self._send_json({"status": "ok", "saved_as": dest.name}, HTTPStatus.CREATED)
            return

        if path == "/api/note":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length).decode("utf-8")
                data = json.loads(raw_body)
                text = str(data.get("text", "")).strip()
            except (ValueError, json.JSONDecodeError):
                self._send_json({"error": "Invalid JSON body"}, HTTPStatus.BAD_REQUEST)
                return

            if not text:
                self._send_json({"error": "Note text cannot be empty"}, HTTPStatus.BAD_REQUEST)
                return

            note = self.server.state.add_note("Phone", text)
            self._send_json({"status": "ok", "note": note}, HTTPStatus.CREATED)
            return

        self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
