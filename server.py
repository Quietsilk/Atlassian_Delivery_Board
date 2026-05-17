#!/usr/bin/env python3
"""AI Delivery Analyst — main entry point.

Routes:
  GET  /               → React dashboard (dashboard/dist/index.html if built,
                         otherwise redirect to http://localhost:5173 dev server)
  GET  /latest         → latest snapshot
  GET  /history        → snapshot history
  POST /sync           → trigger ingestion

Dashboard (React + Vite):
  Dev:  cd dashboard && npm run dev   → http://localhost:5173
  Prod: cd dashboard && npm run build → dist/ served by this server at GET /

Background scheduler: SYNC_INTERVAL_SECONDS (default 3600).
Configured projects: PROJECTS env var (JSON array).
"""

import json
import mimetypes
import os
import http.server

PORT     = 5678
DB_PATH  = os.environ.get("DB_PATH", "snapshots.db")
HOST     = os.environ.get("HOST", "127.0.0.1")   # bind localhost by default

# Directory that holds the production React build
_DIST_DIR = os.path.join(os.path.dirname(__file__), "dashboard", "dist")


def load_env(path):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._serve_html()
        elif path == "/latest":
            from server.api import handle_get_latest
            handle_get_latest(self, DB_PATH)
        elif path == "/history":
            from server.api import handle_get_history
            handle_get_history(self, DB_PATH)
        elif path.startswith("/assets/"):
            self._serve_static(path)
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path == "/sync":
            from server.api import handle_post_sync
            handle_post_sync(self, DB_PATH, {})
        else:
            self.send_response(404)
            self.end_headers()

    # ── Security helpers ────────────────────────────────────────────────────

    def _security_headers(self):
        """Emit hardening headers on every response."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options",        "DENY")
        self.send_header("Referrer-Policy",        "no-referrer")

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    # ── Static file serving ─────────────────────────────────────────────────

    def _serve_html(self):
        """Serve React dashboard.

        Production: serves dashboard/dist/index.html (after npm run build).
        Development: redirects to Vite dev server on port 5173.
        """
        dist_path = os.path.join(_DIST_DIR, "index.html")
        if os.path.exists(dist_path):
            with open(dist_path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self._security_headers()
            self.send_header("Content-Type",   "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control",  "no-store, no-cache, must-revalidate")
            self.send_header("Pragma",         "no-cache")
            self.end_headers()
            self.wfile.write(body)
        else:
            # No production build — redirect to Vite dev server
            self.send_response(302)
            self.send_header("Location", "http://localhost:5173")
            self.end_headers()

    def _serve_static(self, url_path):
        """Serve /assets/* files from the production build directory.

        Path traversal is prevented by resolving the full path and asserting
        it stays inside _DIST_DIR.
        """
        # Strip leading slash and resolve against dist directory
        rel = url_path.lstrip("/")
        abs_path = os.path.realpath(os.path.join(_DIST_DIR, rel))

        # Path traversal guard: must stay inside _DIST_DIR
        if not abs_path.startswith(os.path.realpath(_DIST_DIR) + os.sep):
            self.send_response(403)
            self.end_headers()
            return

        if not os.path.isfile(abs_path):
            self.send_response(404)
            self.end_headers()
            return

        mime, _ = mimetypes.guess_type(abs_path)
        with open(abs_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self._security_headers()
        self.send_header("Content-Type",   mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        # Vite bundles are content-hashed — cache aggressively
        self.send_header("Cache-Control",  "public, max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._security_headers()
        self._cors_headers()
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"  {fmt % args}")


def _load_projects():
    raw = os.environ.get("PROJECTS", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


if __name__ == "__main__":
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_env(env_path)

    from server.storage import init_db
    init_db(DB_PATH)

    projects = _load_projects()
    if projects:
        from server.scheduler import start_scheduler
        start_scheduler(projects, DB_PATH)

    httpd = http.server.HTTPServer((HOST, PORT), Handler)
    print(f"✓ Server on http://{HOST}:{PORT}")
    print(f"  DB:      {DB_PATH}")
    print(f"  Projects scheduled: {len(projects)}")
    print()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
