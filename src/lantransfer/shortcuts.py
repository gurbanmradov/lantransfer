from __future__ import annotations

import os
import platform
import shutil
import stat
import sys
from pathlib import Path


def _resolve_executable() -> str:
    return shutil.which("lantransfer") or f'"{sys.executable}" -m lantransfer'


def create_linux_desktop_entry(applications_dir: Path | None = None) -> Path:
    """Create a clickable .desktop launcher supporting app-menu launch and 'Open With'."""
    app_dir = applications_dir or (Path.home() / ".local" / "share" / "applications")
    app_dir.mkdir(parents=True, exist_ok=True)

    exe = _resolve_executable()
    desktop_file = app_dir / "lantransfer.desktop"
    content = (
        "[Desktop Entry]\n"
        "Name=LAN Transfer\n"
        "Comment=Transfer files and text between PC and phone via QR code\n"
        f"Exec={exe} %F\n"
        "Icon=network-wireless\n"
        "Terminal=true\n"
        "Type=Application\n"
        "Categories=Utility;Network;\n"
    )
    desktop_file.write_text(content, encoding="utf-8")
    return desktop_file


def create_windows_bat_shortcut(desktop_dir: Path | None = None) -> Path:
    """Create a clickable and drag-and-drop enabled .bat launcher on the Windows Desktop."""
    target_dir = desktop_dir or (Path.home() / "Desktop")
    target_dir.mkdir(parents=True, exist_ok=True)

    exe = _resolve_executable()
    bat_file = target_dir / "LAN Transfer.bat"
    content = f"@echo off\n{exe} %*\npause\n"
    bat_file.write_text(content, encoding="utf-8")
    return bat_file


def create_macos_command_shortcut(desktop_dir: Path | None = None) -> Path:
    """Create a clickable .command launcher on the macOS Desktop."""
    target_dir = desktop_dir or (Path.home() / "Desktop")
    target_dir.mkdir(parents=True, exist_ok=True)

    exe = _resolve_executable()
    cmd_file = target_dir / "LAN Transfer.command"
    content = f'#!/bin/sh\n{exe} "$@"\n'
    cmd_file.write_text(content, encoding="utf-8")
    if os.name != "nt":
        cmd_file.chmod(cmd_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return cmd_file


def install_shortcut() -> Path:
    """Create a desktop or app-menu shortcut appropriate for the current OS."""
    system = platform.system().lower()
    if system == "linux":
        return create_linux_desktop_entry()
    if system == "windows":
        return create_windows_bat_shortcut()
    if system == "darwin":
        return create_macos_command_shortcut()
    raise RuntimeError(f"Shortcuts are not supported on {platform.system()}")
