"""
CyberEthos - Desktop Companion
A lightweight tray app that:
  1. Shows a responsibility quote on startup
  2. Listens for a global panic hotkey (default: Ctrl+Alt+P)
  3. On panic: closes known distraction apps, shows a full-screen calming
     overlay with an affirmation, and (only if the user opts in) disables
     network adapters.
     Basically encouragement and a reminder that accountability still exists but that you don't need to fear it because you can do the right thing and use it for good.

Requires (see requirements.txt): PySide6, psutil, keyboard, pywin32
NOTE: the 'keyboard' library needs the app to run as Administrator on Windows
to reliably catch global hotkeys. This is documented in README.md so users are aware. 
"""

import json
import random
import subprocess
import sys
import webbrowser
import winreg
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
    "launch_at_startup": True,
    "panic_trigger_count": 0,
    "distraction_processes": ["chrome.exe", "msedge.exe", "firefox.exe"]
}

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "CyberEthos"


def set_launch_at_startup(enabled: bool):
    """Adds/removes a per-user (HKCU) autostart entry. No admin needed."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
        if enabled:
            exe_path = sys.executable if getattr(sys, "frozen", False) else \
                f'"{sys.executable}" "{Path(__file__).resolve()}"'
            winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, RUN_VALUE_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[CyberEthos] Could not update startup registration: {e}")
        return False


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

#maybe revise later
class QuotePopup(QDialog):
    def __init__(self, quote_text):
        super().__init__()
        self.setWindowTitle("CyberEthos")
        self.setFixedSize(420, 220)
        self.setStyleSheet("""
            QDialog {
                background-color: #16213e;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        label = QLabel(quote_text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Segoe UI", 13))
        label.setStyleSheet("color: #eaeaf0;")
        layout.addWidget(label)

        ok_button = QPushButton("Got it")
        ok_button.setFixedWidth(140)
        ok_button.setStyleSheet("""
            QPushButton {
                padding: 10px;
                border-radius: 8px;
                background-color: #0f3460;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #16447a;
            }
        """)
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button, alignment=Qt.AlignCenter)


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


class Dashboard(QDialog):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.setWindowTitle("CyberEthos Dashboard")
        self.setFixedSize(380, 340)
        self.setStyleSheet("background-color: #16213e; color: #eaeaf0;")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("CyberEthos")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        stats = QLabel(
            f"Panic mode used: {app_ref.settings['panic_trigger_count']} time(s)"
        )
        stats.setAlignment(Qt.AlignCenter)
        stats.setStyleSheet("color: #c4c6d6;")
        layout.addWidget(stats)

        self.startup_checkbox = QCheckBox("Launch CyberEthos when Windows starts")
        self.startup_checkbox.setChecked(app_ref.settings["launch_at_startup"])
        self.startup_checkbox.stateChanged.connect(self.on_startup_toggled)
        layout.addWidget(self.startup_checkbox)

        self.network_checkbox = QCheckBox("Disconnect network during panic mode")
        self.network_checkbox.setChecked(app_ref.settings["network_cutoff_enabled"])
        self.network_checkbox.stateChanged.connect(self.on_network_toggled)
        layout.addWidget(self.network_checkbox)

        btn_style = (
            "padding: 8px; border-radius: 8px; background-color: #0f3460; "
            "color: white; font-size: 13px;"
        )

        quote_btn = QPushButton("Show a quote now")
        quote_btn.setStyleSheet(btn_style)
        quote_btn.clicked.connect(app_ref.show_quote_popup)
        layout.addWidget(quote_btn)

        panic_btn = QPushButton("Trigger panic mode now")
        panic_btn.setStyleSheet(btn_style)
        panic_btn.clicked.connect(app_ref.trigger_panic)
        layout.addWidget(panic_btn)

        learn_btn = QPushButton("Learn about cyber safety")
        learn_btn.setStyleSheet(btn_style)
        learn_btn.clicked.connect(app_ref.open_learn_page)
        layout.addWidget(learn_btn)

        support_btn = QPushButton("Support & get help")
        support_btn.setStyleSheet(btn_style)
        support_btn.clicked.connect(app_ref.open_support_page)
        layout.addWidget(support_btn)

    def on_startup_toggled(self, state):
        enabled = bool(state)
        self.app_ref.settings["launch_at_startup"] = enabled
        save_settings(self.app_ref.settings)
        set_launch_at_startup(enabled)

    def on_network_toggled(self, state):
        self.app_ref.toggle_network_cutoff(bool(state))
        self.app_ref.network_toggle.setChecked(bool(state))


class CyberEthosApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.settings = load_settings()
        set_launch_at_startup(self.settings["launch_at_startup"])
        self.quotes = load_json(APP_DIR / "quotes.json", ["Be thoughtful online."])
        self.affirmations = load_json(
            APP_DIR / "affirmations.json", ["You can step away. That's enough."]
        )

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon(str(APP_DIR / "icon.ico")))
        self.tray.setToolTip("CyberEthos")
        self.tray.activated.connect(self.on_tray_activated)
        self.build_tray_menu()
        self.tray.show()

        self.overlay = None
        self.register_hotkey()

        # show boot quote after launch
        QTimer.singleShot(500, self.show_quote_popup)

    def build_tray_menu(self):
        menu = QMenu()

        dashboard_action = QAction("Open Dashboard", self.app)
        dashboard_action.triggered.connect(self.open_dashboard)
        menu.addAction(dashboard_action)

        menu.addSeparator()

        show_quote_action = QAction("Show a quote now", self.app)
        show_quote_action.triggered.connect(self.show_quote_popup)
        menu.addAction(show_quote_action)

        panic_action = QAction("Trigger panic mode now", self.app)
        panic_action.triggered.connect(self.trigger_panic)
        menu.addAction(panic_action)

        menu.addSeparator()

        learn_action = QAction("Learn about cyber safety", self.app)
        learn_action.triggered.connect(self.open_learn_page)
        menu.addAction(learn_action)

        support_action = QAction("Support & get help", self.app)
        support_action.triggered.connect(self.open_support_page)
        menu.addAction(support_action)

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

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.open_dashboard()

    def open_dashboard(self):
        self.dashboard = Dashboard(self)
        self.dashboard.exec()

    def open_learn_page(self):
        webbrowser.open((APP_DIR / "resources" / "learn.html").as_uri())

    def open_support_page(self):
        webbrowser.open((APP_DIR / "resources" / "support.html").as_uri())

    def show_quote_popup(self):
        quote = random.choice(self.quotes)
        popup = QuotePopup(quote)
        popup.exec()

    def register_hotkey(self):
        try:
            keyboard.add_hotkey(self.settings["panic_hotkey"], self.trigger_panic)
        except Exception as e:
            # this could be caused by not running as admin
            print(f"[CyberEthos] Could not register global hotkey: {e}")

    def trigger_panic(self):
        self.settings["panic_trigger_count"] = self.settings.get("panic_trigger_count", 0) + 1
        save_settings(self.settings)
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