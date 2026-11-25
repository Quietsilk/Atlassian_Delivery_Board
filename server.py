#!/usr/bin/env python3
"""AI Delivery Analyst — main entry point.

Routes (all data routes require an authenticated HttpOnly session):
  GET  /               → React dashboard (dashboard/dist/index.html if built,
                         otherwise redirect to http://localhost:5173 dev server)
  POST /api/login             → exchange ADA_ACCESS_TOKEN for a session cookie
  GET  /api/profiles          → public server-side profile metadata
  GET  /api/latest            → latest snapshot
  GET  /api/history           → snapshot history
  POST /api/validate-profile  → validate a configured Jira profile
  POST /api/sync              → enqueue selected profiles
  POST /api/sync-all          → atomically enqueue all selected profiles

Dashboard (React + Vite):
  Dev:  cd dashboard && npm run dev   → http://localhost:5173
  Prod: cd dashboard && npm run build → dist/ served by this server at GET /

Background scheduler and HTTP share one bounded sync coordinator.
Configured profiles: ADA_PROFILES env var (JSON array).
"""

import json
import mimetypes
import os
import http.server
import ipaddress

PORT     = 5678
DB_PATH  = os.environ.get("DB_PATH", "snapshots.db")
HOST     = os.environ.get("HOST", "127.0.0.1")   # bind localhost by default

# Directory that holds the production React build
_DIST_DIR = os.path.join(os.path.dirname(__file__), "dashboard", "dist")
_AUTH = None
_PROFILES = {}
_COORDINATOR = None


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


def _jira_credentials_from_env():
    return {
        "base_url": (
            os.environ.get("JIRA_BASE_URL")
            or os.environ.get("JIRA_BASEURL")
            or os.environ.get("JIRA_URL")
            or ""
        ),
        "email": os.environ.get("JIRA_EMAIL") or "",
        "api_token": (
            os.environ.get("JIRA_API_TOKEN")
            or os.environ.get("JIRA_TOKEN")
            or ""
        ),
    }


def _trello_credentials_from_env():
    return {
        "api_key": os.environ.get("TRELLO_API_KEY") or "",
        "token": os.environ.get("TRELLO_TOKEN") or "",
    }


def _validate_bind_host(host):
    candidate = host.strip().lower()
    if candidate == "localhost":
        return
    try:
        if ipaddress.ip_address(candidate).is_loopback:
            return
    except ValueError:
        pass
    raise RuntimeError("HOST must resolve to an explicit loopback address")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._serve_html()
        elif path in ("/api/latest", "/latest"):
            from server.api import handle_get_latest
            handle_get_latest(self, DB_PATH, _AUTH)
        elif path in ("/api/history", "/history"):
            from server.api import handle_get_history
            handle_get_history(self, DB_PATH, _AUTH)
        elif path in ("/api/projects", "/projects"):
            from server.api import handle_get_projects
            handle_get_projects(self, DB_PATH, _AUTH)
        elif path in ("/api/profiles", "/profiles"):
            from server.api import handle_get_profiles
            handle_get_profiles(self, _PROFILES, _AUTH)
        elif path in ("/api/session", "/session"):
            from server.api import handle_get_session
            handle_get_session(self, _AUTH)
        elif path in ("/api/sync-status", "/sync-status"):
            from server.api import handle_get_sync_status
            handle_get_sync_status(self, _COORDINATOR, _AUTH)
        elif path.startswith("/assets/"):
            self._serve_static(path)
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        from server.api import handle_options
        handle_options(self)

    def do_POST(self):
        path = self.path.split("?")[0]
        if path in ("/api/login", "/login"):
            from server.api import handle_post_login
            handle_post_login(self, _AUTH)
        elif path in ("/api/logout", "/logout"):
            from server.api import handle_post_logout
            handle_post_logout(self, _AUTH)
        elif path in ("/api/sync", "/sync"):
            from server.api import handle_post_sync
            handle_post_sync(self, _PROFILES, _COORDINATOR, _AUTH)
        elif path in ("/api/sync-all", "/sync-all"):
            from server.api import handle_post_sync_all
            handle_post_sync_all(self, _PROFILES, _COORDINATOR, _AUTH)
        elif path in ("/api/validate-profile", "/validate-profile"):
            from server.api import handle_post_validate_profile
            handle_post_validate_profile(self, _PROFILES, _AUTH)
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
        from server.api import _send_cors_headers
        _send_cors_headers(self)

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


if __name__ == "__main__":
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_env(env_path)
    DB_PATH = os.environ.get("DB_PATH", "snapshots.db")
    HOST = os.environ.get("HOST", "127.0.0.1")
    _validate_bind_host(HOST)

    from server.storage import init_db
    init_db(DB_PATH)

    from server.profiles import load_profiles
    from server.security import AuthManager
    from server.sync_coordinator import SyncCoordinator

    _AUTH = AuthManager(os.environ.get("ADA_ACCESS_TOKEN"))
    _PROFILES = load_profiles(
        os.environ.get("ADA_PROFILES", "[]"),
        _jira_credentials_from_env(),
        _trello_credentials_from_env(),
    )
    _COORDINATOR = SyncCoordinator(
        DB_PATH,
        worker_count=int(os.environ.get("ADA_SYNC_WORKERS", "2")),
        max_jobs=int(os.environ.get("ADA_SYNC_QUEUE_SIZE", "32")),
    )
    _COORDINATOR.start()

    if _PROFILES:
        from server.scheduler import start_scheduler
        start_scheduler(list(_PROFILES.values()), _COORDINATOR)

    httpd = http.server.HTTPServer((HOST, PORT), Handler)
    print(f"✓ Server on http://{HOST}:{PORT}")
    print(f"  DB:      {DB_PATH}")
    print(f"  Profiles configured: {len(_PROFILES)}")
    print()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
