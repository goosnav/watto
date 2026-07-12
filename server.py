#!/usr/bin/env python3
"""Watto local web server. Stdlib only — no pip install, nothing to break.

Binds 127.0.0.1 only: the app (and your API key) is never exposed to the
network. Finds a free port automatically; if Watto is already running it
just opens your browser to the existing instance instead of erroring.
"""
import argparse
import json
import os
import sys
import threading
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import engine

STATIC = Path(__file__).resolve().parent / "static"
MAX_BODY = 40 * 1024 * 1024
PORT_TRIES = 20

SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
# ponytail: sessions live in memory and one session is mutated without a lock;
# fine for a single-user local app, move to a store if this ever hosts >1 user.


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj=None, body=None, ctype="application/json", extra=None):
        payload = body if body is not None else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def _json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise engine.EngineError("Upload too large (40 MB max). Use fewer/smaller photos.")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        try:
            if self.path in ("/", "/index.html"):
                self._send(200, body=(STATIC / "index.html").read_bytes(),
                           ctype="text/html; charset=utf-8")
            elif self.path == "/api/health":
                self._send(200, {"app": "watto", "ok": True})
            elif self.path == "/api/settings":
                settings = engine.load_settings()
                key = settings.pop("api_key", "")
                settings["has_key"] = bool(key)
                settings["key_hint"] = ("..." + key[-4:]) if key else ""
                self._send(200, settings)
            elif self.path.startswith("/api/report/"):
                sid = self.path.rsplit("/", 1)[1]
                with SESSIONS_LOCK:
                    session = SESSIONS.get(sid)
                pdf_path = (session or {}).get("report_pdf")
                if not pdf_path or not Path(pdf_path).is_file():
                    self._send(404, {"error": "Report not found (server restarted?). "
                                              "It is still saved in your Watto Appraisals folder."})
                    return
                self._send(200, body=Path(pdf_path).read_bytes(), ctype="application/pdf",
                           extra={"Content-Disposition":
                                  f'inline; filename="Watto-Report-{sid[:6].upper()}.pdf"'})
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

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
            elif self.path == "/api/quit":
                self._send(200, {"ok": True})
                threading.Timer(0.4, os._exit, [0]).start()
            else:
                self._send(404, {"error": "not found"})
        except engine.EngineError as e:
            self._send(502, {"error": str(e)})
        except Exception as e:  # never show a customer a stack trace
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        pass  # keep the double-click terminal window quiet


def _existing_watto(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=0.6) as r:
            return json.loads(r.read()).get("app") == "watto"
    except Exception:
        return False


def _run(args):
    for port in range(args.port, args.port + PORT_TRIES):
        if _existing_watto(port):
            url = f"http://127.0.0.1:{port}"
            print(f"Watto is already running at {url} — opening your browser.")
            if not args.no_browser:
                webbrowser.open(url)
            return
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue  # something else owns this port; try the next one
    else:
        raise RuntimeError(
            f"No free port found between {args.port} and {args.port + PORT_TRIES - 1}. "
            "Close some applications and try again.")

    url = f"http://127.0.0.1:{port}"
    print(f"Watto is running at {url}  (Ctrl+C to quit)")
    if args.open:
        threading.Timer(0.8, webbrowser.open, [url]).start()
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Watto — local AI appraiser")
    parser.add_argument("--port", type=int, default=8177, help="first port to try")
    parser.add_argument("--open", action="store_true", help="open the browser")
    parser.add_argument("--no-browser", action="store_true",
                        help="never open a browser, even for an existing instance")
    args = parser.parse_args()
    try:
        _run(args)
    except KeyboardInterrupt:
        print("\nBye.")
    except Exception as e:
        print(f"\nWatto could not start: {e}")
        if sys.stdin.isatty():
            input("Press Enter to close this window...")
        sys.exit(1)


if __name__ == "__main__":
    main()
