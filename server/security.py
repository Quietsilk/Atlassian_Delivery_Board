"""Local authentication and bounded JSON request parsing."""

from collections import defaultdict, deque
from http import cookies
import json
import secrets
import socket
import threading
import time


COOKIE_NAME = "ada_session"
MAX_JSON_BODY_BYTES = 64 * 1024
BODY_READ_TIMEOUT_SECONDS = 5
SESSION_TTL_SECONDS = 8 * 60 * 60
LOGIN_WINDOW_SECONDS = 60
LOGIN_MAX_ATTEMPTS = 5


class RequestError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def read_json_body(handler, *, max_bytes=MAX_JSON_BODY_BYTES):
    content_type = (handler.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise RequestError(415, "Content-Type must be application/json")

    raw_length = handler.headers.get("Content-Length")
    if raw_length is None:
        raise RequestError(411, "Content-Length is required")
    try:
        length = int(raw_length)
    except (TypeError, ValueError):
        raise RequestError(400, "Content-Length must be a non-negative integer")
    if length < 0:
        raise RequestError(400, "Content-Length must be a non-negative integer")
    if length > max_bytes:
        raise RequestError(413, "request body is too large")

    try:
        handler.connection.settimeout(BODY_READ_TIMEOUT_SECONDS)
        raw = handler.rfile.read(length)
    except (TimeoutError, socket.timeout):
        raise RequestError(408, "request body read timed out")
    if len(raw) != length:
        raise RequestError(400, "request body is incomplete")
    try:
        body = json.loads(raw) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RequestError(400, "request body must contain valid JSON")
    if not isinstance(body, dict):
        raise RequestError(400, "request JSON must be an object")
    return body


class AuthManager:
    def __init__(self, access_token, *, ttl_seconds=SESSION_TTL_SECONDS):
        if not access_token:
            raise RuntimeError("ADA_ACCESS_TOKEN is required")
        self._access_token = access_token
        self._ttl_seconds = ttl_seconds
        self._sessions = {}
        self._attempts = defaultdict(deque)
        self._lock = threading.Lock()

    @staticmethod
    def _client_key(handler):
        address = getattr(handler, "client_address", None) or ("local", 0)
        return str(address[0])

    def login(self, handler, supplied_token):
        client = self._client_key(handler)
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts[client]
            while attempts and now - attempts[0] > LOGIN_WINDOW_SECONDS:
                attempts.popleft()
            if len(attempts) >= LOGIN_MAX_ATTEMPTS:
                raise RequestError(429, "too many login attempts")
            if not isinstance(supplied_token, str) or not secrets.compare_digest(
                supplied_token.encode(), self._access_token.encode()
            ):
                attempts.append(now)
                raise RequestError(403, "invalid access token")
            attempts.clear()
            session_id = secrets.token_urlsafe(32)
            self._sessions[session_id] = now + self._ttl_seconds
            return session_id

    def authenticated(self, handler):
        session_id = self._session_from_cookie(handler)
        if not session_id:
            return False
        now = time.monotonic()
        with self._lock:
            expires_at = self._sessions.get(session_id)
            if expires_at is None:
                return False
            if expires_at <= now:
                self._sessions.pop(session_id, None)
                return False
            return True

    def logout(self, handler):
        session_id = self._session_from_cookie(handler)
        if session_id:
            with self._lock:
                self._sessions.pop(session_id, None)

    @staticmethod
    def _session_from_cookie(handler):
        raw = handler.headers.get("Cookie")
        if not raw:
            return None
        jar = cookies.SimpleCookie()
        try:
            jar.load(raw)
        except cookies.CookieError:
            return None
        morsel = jar.get(COOKIE_NAME)
        return morsel.value if morsel else None


def session_cookie(session_id, *, secure=False):
    parts = [f"{COOKIE_NAME}={session_id}", "HttpOnly", "SameSite=Strict", "Path=/"]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def clear_session_cookie(*, secure=False):
    parts = [f"{COOKIE_NAME}=", "HttpOnly", "SameSite=Strict", "Path=/", "Max-Age=0"]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)
