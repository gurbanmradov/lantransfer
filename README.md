# lantransfer

[![CI](https://github.com/gurbanmradov/lantransfer/actions/workflows/ci.yml/badge.svg)](https://github.com/gurbanmradov/lantransfer/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Zero-app, QR-code powered bidirectional file and text transfer over your local network.**

Transfer files, folders, photos, and links between **iOS, Android, Linux, Windows, and macOS** at full Wi-Fi speed without cables, cloud uploads, or mobile app installations.

---

## Features

- **Single QR Code, Both Directions:** Scan once with your phone camera to download files from your PC, upload multiple photos/files to your PC, and exchange text/links in real time.
- **One-Click Desktop Shortcut (`--setup`):** Generates a native launcher on Linux (`.desktop`), Windows (`.bat` with drag-and-drop), and macOS (`.command`).
- **Live Drag & Drop Sharing:** While a session is running, drag any file/folder into the terminal window (or type a link) and press Enter to push it live to your phone.
- **Zero Mobile App Required:** Works directly in iOS Safari and Android Chrome with live upload progress bars.
- **On-the-Fly Folder Archiving:** Share entire directories; `lantransfer` zips them automatically on demand and cleans up temporary archives on exit.
- **Memory-Safe Streaming:** Transfers files in 64 KB chunks so large videos do not spike RAM usage.
- **Built-in Security:**
  - Cryptographically random per-session token verified in constant time (`secrets.compare_digest`).
  - Strict filename sanitization and path-traversal protection (`../../` blocked).
  - Non-destructive collision handling (`photo.jpg` -> `photo (1).jpg`).
- **Minimal Dependencies:** Built on Python's standard library (`http.server`, `socket`, `zipfile`) with only `qrcode` for terminal QR rendering.

---

## Installation & Quick Setup

```bash
git clone [https://github.com/gurbanmradov/lantransfer.git](https://github.com/gurbanmradov/lantransfer.git)
cd lantransfer
pip install .
lantransfer --setup
```

Running `lantransfer --setup` creates a clickable **LAN Transfer** shortcut for your OS:
- **Linux:** Application menu entry (`~/.local/share/applications/lantransfer.desktop`) with *"Open With"* support.
- **Windows:** Desktop shortcut (`LAN Transfer.bat`) — double-click to start or drag files directly onto the icon.
- **macOS:** Desktop shortcut (`LAN Transfer.command`).

---

## Usage

Start a bidirectional session (or just click the **LAN Transfer** shortcut):
```bash
lantransfer
```

Share specific files or folders from your PC while also accepting uploads:
```bash
lantransfer report.pdf ./slides_folder --text "Meeting link: [https://example.com](https://example.com)"
```

Customize destination directory or port:
```bash
lantransfer -d ~/Downloads/from-phone -p 9000
```

| Flag | Description |
|---|---|
| `paths` | Optional files or folders to make downloadable from your phone |
| `--setup` | Create a one-click desktop/menu shortcut for your OS and exit |
| `-d, --dir` | Folder where uploaded files are saved (default: `./lantransfer_received`) |
| `-p, --port` | Preferred port (default: `8765`, falls back to a free port if busy) |
| `--host` | Manually override the auto-detected local IPv4 address |
| `-t, --text` | Share an initial text note or URL from PC to phone |

---

## Troubleshooting

- **Campus / Public Wi-Fi (`eduroam`, cafes, hotels):** Enterprise networks enable **AP / Client Isolation**, blocking direct device-to-device connections on the LAN. Use your phone's **Personal Hotspot** (Wi-Fi or USB tethering) instead — local transfers do not consume mobile data.
- **Linux Firewall (`firewalld` on Fedora/RHEL):** Allow the port temporarily or permanently:
  ```bash
  sudo firewall-cmd --add-port=8765/tcp
  ```
- **Windows Firewall:** Allow Python access on **Private networks** when Windows Defender prompts on first launch.

---

## Development & Testing

```bash
python -m unittest discover -s tests -v
```
