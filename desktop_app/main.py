"""
CyberEthos - Desktop Companion
A lightweight tray app that:
  1. Shows a responsibility quote on startup
  2. Listens for a global panic hotkey (default: Ctrl+Alt+P)
  3. On panic: closes known distraction apps, shows a full-screen calming
     overlay with an affirmation, and (only if the user opts in) disables
     network adapters.

Requires (see requirements.txt): PySide6, psutil, keyboard, pywin32
NOTE: the 'keyboard' library needs the app to run as Administrator on Windows
to reliably catch global hotkeys. This is documented in README.md.
"""

import json
import random
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QFont, QAction
from PySide6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog, QLabel, QVBoxLayout,
    QPushButton, QWidget, QCheckBox, QMessageBox
)

import psutil
import keyboard

def resource_dir():
    """Where bundled data files (quotes.json, affirmations.json) live.
    PyInstaller --onefile extracts them into a temp dir at sys._MEIPASS."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def settings_dir():
    """Where settings.json is read/written. Always next to the exe (or
    script) itself, NOT the temp extraction folder, so settings persist
    between runs."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = resource_dir()
SETTINGS_PATH = settings_dir() / "settings.json"
DEFAULT_SETTINGS = {
    "panic_hotkey": "ctrl+alt+p",
    "network_cutoff_enabled": False,  # opt-in, requires admin
    "distraction_processes": ["chrome.exe", "msedge.exe", "firefox.exe"]
}


def load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return fallback


def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    settings.update(load_json(SETTINGS_PATH, {}))
    return settings


def save_settings(settings):
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


class QuotePopup(QDialog):
    def __init__(self, quote_text):
        super().__init__()
        self.setWindowTitle("CyberEthos")
        self.setFixedSize(420, 200)
        layout = QVBoxLayout(self)

        label = QLabel(quote_text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Segoe UI", 12))
        layout.addWidget(label)

        ok_button = QPushButton("Got it")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)


class PanicOverlay(QWidget):
    """Full-screen calming overlay shown after a panic trigger."""

    def __init__(self, affirmation_text):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.setStyleSheet("background-color: #16213e;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Take a breath.")
        title.setStyleSheet("color: white;")
        title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        text = QLabel(affirmation_text)
        text.setStyleSheet("color: #d0d3e6;")
        text.setFont(QFont("Segoe UI", 16))
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignCenter)
        text.setFixedWidth(700)
        layout.addWidget(text)

        close_btn = QPushButton("I'm okay, close this")
        close_btn.setFixedWidth(220)
        close_btn.setStyleSheet(
            "padding: 10px; font-size: 14px; border-radius: 8px; "
            "background-color: #0f3460; color: white;"
        )
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)


class CyberEthosApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.settings = load_settings()
        self.quotes = load_json(APP_DIR / "quotes.json", ["Be thoughtful online."])
        self.affirmations = load_json(
            APP_DIR / "affirmations.json", ["You can step away. That's enough."]
        )

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon.fromTheme("security-medium"))
        self.tray.setToolTip("CyberEthos")
        self.build_tray_menu()
        self.tray.show()

        self.overlay = None
        self.register_hotkey()

        # Show boot quote shortly after launch
        QTimer.singleShot(500, self.show_quote_popup)

    def build_tray_menu(self):
        menu = QMenu()

        show_quote_action = QAction("Show a quote now", self.app)
        show_quote_action.triggered.connect(self.show_quote_popup)
        menu.addAction(show_quote_action)

        panic_action = QAction("Trigger panic mode now", self.app)
        panic_action.triggered.connect(self.trigger_panic)
        menu.addAction(panic_action)

        menu.addSeparator()

        self.network_toggle = QAction("Disconnect network during panic mode", self.app)
        self.network_toggle.setCheckable(True)
        self.network_toggle.setChecked(self.settings["network_cutoff_enabled"])
        self.network_toggle.triggered.connect(self.toggle_network_cutoff)
        menu.addAction(self.network_toggle)

        menu.addSeparator()

        quit_action = QAction("Quit CyberEthos", self.app)
        quit_action.triggered.connect(self.app.quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)

    def toggle_network_cutoff(self, checked):
        self.settings["network_cutoff_enabled"] = checked
        save_settings(self.settings)
        if checked:
            QMessageBox.information(
                None, "CyberEthos",
                "Network cutoff during panic mode is now ON.\n\n"
                "This requires running CyberEthos as Administrator, and will "
                "disconnect ALL network adapters (including calls, other apps, "
                "downloads) until you reconnect manually."
            )

    def show_quote_popup(self):
        quote = random.choice(self.quotes)
        popup = QuotePopup(quote)
        popup.exec()

    def register_hotkey(self):
        try:
            keyboard.add_hotkey(self.settings["panic_hotkey"], self.trigger_panic)
        except Exception as e:
            # Common cause: not running as Administrator
            print(f"[CyberEthos] Could not register global hotkey: {e}")

    def trigger_panic(self):
        self.close_distraction_processes()
        if self.settings["network_cutoff_enabled"]:
            self.disable_network()
        self.show_overlay()

    def close_distraction_processes(self):
        targets = set(self.settings["distraction_processes"])
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] in targets:
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def disable_network(self):
        """Best-effort network disable via netsh. Requires admin."""
        try:
            result = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if "Connected" in line:
                    parts = line.split(None, 3)
                    if len(parts) == 4:
                        iface_name = parts[3]
                        subprocess.run(
                            ["netsh", "interface", "set", "interface",
                             iface_name, "admin=disable"],
                            timeout=5
                        )
        except Exception as e:
            print(f"[CyberEthos] Network disable failed (likely needs admin): {e}")

    def show_overlay(self):
        affirmation = random.choice(self.affirmations)
        self.overlay = PanicOverlay(affirmation)
        self.overlay.show()

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    CyberEthosApp().run()
