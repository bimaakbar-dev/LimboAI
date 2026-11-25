"""Server HUD: avatar + state AI + chat + layout."""
from __future__ import annotations

import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import hud_state
from core.assistant import Assistant

ROOT = Path(__file__).resolve().parent
LAYOUT = {"chat": False}


class Handler(SimpleHTTPRequestHandler):
    assistant: Assistant

    def __init__(self, *args: Any, assistant: Assistant | None = None, **kwargs: Any) -> None:
        self.assistant = assistant  # type: ignore[assignment]
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith("/api/state"):
            self._json(hud_state.get_state())
            return
        if self.path.startswith("/api/status"):
            self._json({
                "mode": self.assistant.mode,
                "local": self.assistant.local.available(),
                "cloud": self.assistant.cloud.available(),
            })
            return
        if self.path.startswith("/api/layout"):
            self._json(LAYOUT)
            return
        super().do_GET()

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, OSError):
            self._json({"error": "request tidak valid"}, status=400)
            return

        if self.path.startswith("/api/chat"):
            reply = self.assistant.handle(str(data.get("text", "")))
            self._json({"reply": reply, "route": self.assistant.last_route})
            return
        if self.path.startswith("/api/mode"):
            mode = data.get("mode")
            if mode in {"auto", "local", "cloud"}:
                self.assistant.mode = mode
                self._json({"ok": True, "mode": mode})
            else:
                self._json({"error": "mode tidak dikenal"}, status=400)
            return
        if self.path.startswith("/api/layout"):
            LAYOUT["chat"] = bool(data.get("chat", False))
            self._json({"ok": True, **LAYOUT})
            return
        self._json({"error": "endpoint tidak ditemukan"}, status=404)


def make_server(port: int = 8010) -> ThreadingHTTPServer:
    assistant = Assistant(ROOT)
    handler = partial(Handler, directory=str(ROOT / "hud_web"), assistant=assistant)
    return ThreadingHTTPServer(("127.0.0.1", port), handler)
