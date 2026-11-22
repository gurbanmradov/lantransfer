import tempfile
import unittest
from pathlib import Path

from lantransfer.security import (
    generate_token,
    resolve_unique_path,
    sanitize_filename,
    verify_token,
)


class TestSecurity(unittest.TestCase):
    def test_token_generation_and_verification(self):
        token = generate_token()
        self.assertTrue(len(token) >= 16)
        self.assertTrue(verify_token(token, token))
        self.assertFalse(verify_token(token, "wrong-token"))
        self.assertFalse(verify_token(token, None))

    def test_sanitize_filename_blocks_path_traversal(self):
        self.assertEqual(sanitize_filename("../../etc/passwd"), "passwd")
        self.assertEqual(sanitize_filename("..\\..\\Windows\\cmd.exe"), "cmd.exe")
        self.assertEqual(sanitize_filename("..."), "unnamed_file")
        self.assertEqual(sanitize_filename("rapor:2026?.pdf"), "rapor_2026_.pdf")

    def test_resolve_unique_path_avoids_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first = resolve_unique_path(base, "photo.jpg")
            self.assertEqual(first.name, "photo.jpg")
            first.write_text("a", encoding="utf-8")

            second = resolve_unique_path(base, "photo.jpg")
            self.assertEqual(second.name, "photo (1).jpg")
            second.write_text("b", encoding="utf-8")

            third = resolve_unique_path(base, "photo.jpg")
            self.assertEqual(third.name, "photo (2).jpg")


if __name__ == "__main__":
    unittest.main()


class TestShortcuts(unittest.TestCase):
    def test_create_linux_windows_and_macos_shortcuts(self):
        from lantransfer.shortcuts import (
            create_linux_desktop_entry,
            create_macos_command_shortcut,
            create_windows_bat_shortcut,
        )

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            linux_file = create_linux_desktop_entry(applications_dir=base)
            self.assertTrue(linux_file.exists())
            self.assertIn("Terminal=true", linux_file.read_text(encoding="utf-8"))

            win_file = create_windows_bat_shortcut(desktop_dir=base)
            self.assertTrue(win_file.exists())
            self.assertIn("%*", win_file.read_text(encoding="utf-8"))

            mac_file = create_macos_command_shortcut(desktop_dir=base)
            self.assertTrue(mac_file.exists())
            self.assertIn('"$@"', mac_file.read_text(encoding="utf-8"))
