"""Limbo Desktop Companion — jendela transparan frameless via PyQt6 WebEngine.

Avatar tetap memakai engine GrokBot asli dari source kamu (hud_web/).
"""
from __future__ import annotations

import ctypes
import sys
import threading

from PyQt6.QtCore import QEvent, QTimer, QUrl, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

from hud_server import LAYOUT, make_server

PORT = 8010
URL = f"http://127.0.0.1:{PORT}/"
user32 = ctypes.windll.user32


ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Windows.UI.Core.CoreWindow"}


def any_app_window() -> bool:
    """True jika ada jendela aplikasi nyata yang terlihat (bukan shell/HUD kita)."""
    found: list[int] = []

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        title = ctypes.create_unicode_buffer(256)
        klass = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, 256)
        user32.GetClassNameW(hwnd, klass, 256)
        if klass.value in SHELL_CLASSES or "Limbo HUD" in title.value:
            return True
        if title.value:
            found.append(int(hwnd))
            return False
        return True

    user32.EnumWindows(ENUMPROC(callback), 0)
    return bool(found)


def geometry() -> tuple[int, int, int, int]:
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)

    if LAYOUT.get("chat"):
        width, height = 480, 560
        return width, height, (w - width) // 2, (h - height) // 2

    if not any_app_window():
        width, height = 320, 360
        return width, height, (w - width) // 2, (h - height) // 2

    width, height = 120, 150
    return width, height, w - width - 22, 28


class LimboPet(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Limbo HUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.view = QWebEngineView()
        self.view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.view.setStyleSheet("background: transparent;")
        self.view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        settings = self.view.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
        self.view.load(QUrl(URL))
        layout.addWidget(self.view)

        self._drag = None
        self._press = None
        self._last_chat = None
        self._focus_pending = False
        self._armed = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)
        self.timer.start(1200)
        self.update_geometry()

    def on_tick(self) -> None:
        self.update_geometry()

    def event(self, event) -> bool:  # type: ignore[override]
        if event.type() == QEvent.Type.WindowActivate:
            self._armed = True
        if (
            event.type() == QEvent.Type.WindowDeactivate
            and self._armed
            and LAYOUT.get("chat")
        ):
            self.toggle_chat()
        return super().event(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape and LAYOUT.get("chat"):
            self.toggle_chat()
        super().keyPressEvent(event)

    def update_geometry(self) -> None:
        width, height, x, y = geometry()
        self.resize(width, height)
        self.move(x, y)
        self.raise_()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if LAYOUT.get("chat"):
            return  # biarkan web view menangani klik/input
        self._drag = event.globalPosition().toPoint()
        self._press = self._drag

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if LAYOUT.get("chat"):
            return
        current = event.globalPosition().toPoint()
        if self._drag is not None:
            delta = current - self._drag
            self.move(self.pos() + delta)
            self._drag = current

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if LAYOUT.get("chat"):
            return
        if self._drag is not None and self._press is not None:
            moved = (self._drag - self._press).manhattanLength()
            if moved < 6:
                self.toggle_chat()
        self._drag = None
        self._press = None

    def toggle_chat(self) -> None:
        opening = not LAYOUT.get("chat", False)
        LAYOUT["chat"] = opening
        self.view.page().runJavaScript(
            "window.limboToggleChat && window.limboToggleChat()"
        )
        if opening:
            # Saat chat terbuka, web view harus menerima mouse supaya input bisa diklik.
            self.view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            self.raise_()
            self.activateWindow()
            self.setFocus()
            self._armed = False
        else:
            self.view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._armed = False
        self.update_geometry()


def main() -> None:
    server = make_server(PORT)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Server avatar aktif di {URL}")

    app = QApplication(sys.argv)
    pet = LimboPet()
    pet.show()
    print("Limbo companion aktif.")
    try:
        app.exec()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
