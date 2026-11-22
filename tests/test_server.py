import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from lantransfer.server import TransferHTTPServer, TransferState


class TestTransferServer(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.upload_dir = self.root / "uploads"

        self.sample_file = self.root / "hello.txt"
        self.sample_file.write_text("hello lantransfer", encoding="utf-8")

        self.sample_folder = self.root / "my_folder"
        self.sample_folder.mkdir()
        (self.sample_folder / "inside.txt").write_text("nested content", encoding="utf-8")

        self.token = "test-secret-token-123"
        self.state = TransferState(token=self.token, upload_dir=self.upload_dir)
        self.file_item = self.state.add_shared_path(self.sample_file)
        self.dir_item = self.state.add_shared_path(self.sample_folder)

        self.server = TransferHTTPServer(("127.0.0.1", 0), self.state)
        self.port = self.server.server_address[1]
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.state.cleanup()
        self.tmp_dir.cleanup()

    def test_rejects_missing_or_wrong_token(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(f"{self.base_url}/api/state")
        self.assertEqual(ctx.exception.code, 403)

        with self.assertRaises(urllib.error.HTTPError) as ctx2:
            urllib.request.urlopen(f"{self.base_url}/api/state?token=wrong")
        self.assertEqual(ctx2.exception.code, 403)

    def test_download_file(self):
        url = f"{self.base_url}/download/{self.file_item.item_id}?token={self.token}"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.read().decode("utf-8"), "hello lantransfer")

    def test_download_folder_as_zip(self):
        url = f"{self.base_url}/download/{self.dir_item.item_id}?token={self.token}"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            raw_zip = resp.read()

        with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
            names = zf.namelist()
            self.assertIn("my_folder/inside.txt", names)
            self.assertEqual(zf.read("my_folder/inside.txt").decode("utf-8"), "nested content")

    def test_upload_sanitizes_path_traversal(self):
        payload = b"binary-photo-data"
        malicious_name = urllib.parse.quote("../../outside.bin")
        url = f"{self.base_url}/api/upload?token={self.token}&filename={malicious_name}"
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/octet-stream"},
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)
            body = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(body["saved_as"], "outside.bin")

        saved_path = self.upload_dir / "outside.bin"
        self.assertTrue(saved_path.exists())
        self.assertEqual(saved_path.read_bytes(), payload)

    def test_post_note_and_read_state(self):
        url = f"{self.base_url}/api/note?token={self.token}"
        req = urllib.request.Request(
            url,
            data=json.dumps({"text": "https://example.com"}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)

        with urllib.request.urlopen(f"{self.base_url}/api/state?token={self.token}") as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(len(data["notes"]), 1)
            self.assertEqual(data["notes"][0]["text"], "https://example.com")


if __name__ == "__main__":
    unittest.main()
