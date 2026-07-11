#!/usr/bin/env python3
"""Watto local web server. Stdlib only — no pip install, nothing to break.

Binds 127.0.0.1 only: the app (and your API key) is never exposed to the
network. Run:  python3 server.py --open
"""
import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import engine

STATIC = Path(__file__).resolve().parent / "static"
MAX_BODY = 40 * 1024 * 1024

SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
# ponytail: sessions live in memory and one session is mutated without a lock;
# fine for a single-user local app, move to a store if this ever hosts >1 user.


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj=None, body=None, ctype="application/json"):
        payload = body if body is not None else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise engine.EngineError("Upload too large (40 MB max). Use fewer/smaller photos.")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, body=(STATIC / "index.html").read_bytes(),
                       ctype="text/html; charset=utf-8")
        elif self.path == "/api/settings":
            settings = engine.load_settings()
            key = settings.pop("api_key", "")
            settings["has_key"] = bool(key)
            settings["key_hint"] = ("..." + key[-4:]) if key else ""
            self._send(200, settings)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            body = self._json_body()
            if self.path == "/api/settings":
                updates = {k: body[k] for k in engine.DEFAULTS if k in body}
                if updates.get("api_key") == "":
                    updates.pop("api_key")  # empty field means "keep existing key"
                engine.save_settings(updates)
                self._send(200, {"ok": True})
            elif self.path == "/api/appraise":
                appraiser = engine.Appraiser(engine.load_settings())
                session = appraiser.new_session(body.get("description", ""),
                                                body.get("attachments"))
                with SESSIONS_LOCK:
                    SESSIONS[session["id"]] = session
                self._send(200, engine.public_view(session))
            elif self.path == "/api/answer":
                with SESSIONS_LOCK:
                    session = SESSIONS.get(body.get("session_id"))
                if session is None:
                    self._send(400, {"error": "Session expired (server restarted?). Start over."})
                    return
                appraiser = engine.Appraiser(engine.load_settings())
                appraiser.submit_answers(session, body.get("answers"),
                                         body.get("attachments"))
                self._send(200, engine.public_view(session))
            else:
                self._send(404, {"error": "not found"})
        except engine.EngineError as e:
            self._send(502, {"error": str(e)})
        except Exception as e:  # never show a customer a stack trace
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        pass  # keep the double-click terminal window quiet


def main():
    parser = argparse.ArgumentParser(description="Watto — local AI appraiser")
    parser.add_argument("--port", type=int, default=8177)
    parser.add_argument("--open", action="store_true", help="open the browser")
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"Watto is running at {url}  (Ctrl+C to quit)")
    if args.open:
        threading.Timer(0.8, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye.")


if __name__ == "__main__":
    main()
