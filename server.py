#!/usr/bin/env python3
"""AI Delivery Analyst — main entry point.

Routes:
  GET  /               → dashboard HTML
  GET  /latest         → latest snapshot
  GET  /history        → snapshot history
  POST /sync           → trigger ingestion

Background scheduler: SYNC_INTERVAL_SECONDS (default 3600).
Configured projects: PROJECTS env var (JSON array).
"""

import json
import os
import http.server

PORT     = 5678
DB_PATH  = os.environ.get("DB_PATH", "snapshots.db")


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
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_POST(self):
        if self.path == "/sync":
            from server.api import handle_post_sync
            handle_post_sync(self, DB_PATH, {})
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_html(self):
        html_path = os.path.join(os.path.dirname(__file__), "ai-delivery-analyst-dashboard.html")
        with open(html_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type",    "text/html; charset=utf-8")
        self.send_header("Content-Length",  str(len(body)))
        self.send_header("Cache-Control",   "no-store, no-cache, must-revalidate")
        self.send_header("Pragma",          "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
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

    httpd = http.server.HTTPServer(("", PORT), Handler)
    print(f"✓ Server on http://localhost:{PORT}")
    print(f"  DB:      {DB_PATH}")
    print(f"  Projects scheduled: {len(projects)}")
    print()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
