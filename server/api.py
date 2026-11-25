"""Authenticated HTTP API for snapshots and server-side sync profiles."""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from server.security import RequestError, clear_session_cookie, read_json_body, session_cookie
from server.sync_coordinator import QueueFullError


_DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5678", "http://127.0.0.1:5678",
)
_TRELLO_LOOKBACK_DEFAULT = 21
_TRELLO_LOOKBACK_MIN = 1
_TRELLO_LOOKBACK_MAX = 365
_MAX_PROFILE_BATCH = 64


def _allowed_origins():
    configured = os.environ.get("ADA_ALLOWED_ORIGINS") or os.environ.get("ALLOWED_ORIGINS")
    if not configured:
        return set(_DEFAULT_ALLOWED_ORIGINS)
    return {origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()}


def _allowed_jira_hosts():
    configured = os.environ.get("ADA_ALLOWED_JIRA_HOSTS", "")
    return {host.strip().lower().rstrip(".") for host in configured.split(",") if host.strip()}


def _validate_jira_base_url(value):
    parsed = urllib.parse.urlsplit(value)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("jira baseUrl contains an invalid port") from error
    if (
        parsed.scheme != "https" or not hostname or parsed.username or parsed.password
        or parsed.query or parsed.fragment or parsed.path not in ("", "/")
        or port not in (None, 443)
    ):
        raise ValueError("jira baseUrl must be an HTTPS origin without path, query, or credentials")
    if not (hostname.endswith(".atlassian.net") or hostname in _allowed_jira_hosts()):
        raise ValueError("jira baseUrl host is not allowed")
    return f"https://{hostname}"


def _parse_trello_lookback_days(value):
    if value is None:
        return _TRELLO_LOOKBACK_DEFAULT
    if isinstance(value, bool):
        raise ValueError("trello lookbackDays must be an integer from 1 to 365")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("trello lookbackDays must be an integer from 1 to 365")
    if parsed < _TRELLO_LOOKBACK_MIN or parsed > _TRELLO_LOOKBACK_MAX:
        raise ValueError("trello lookbackDays must be an integer from 1 to 365")
    return parsed


def _request_origin(handler):
    origin = handler.headers.get("Origin")
    return origin.rstrip("/") if origin else ""


def _origin_allowed(handler):
    origin = _request_origin(handler)
    return not origin or origin in _allowed_origins()


def _send_cors_headers(handler):
    origin = _request_origin(handler)
    if origin and origin in _allowed_origins():
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Access-Control-Allow-Credentials", "true")
        handler.send_header("Vary", "Origin")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Max-Age", "600")


def _json_response(handler, code, data, *, headers=None):
    body = json.dumps(data).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    _send_cors_headers(handler)
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("Referrer-Policy", "no-referrer")
    for name, value in (headers or {}).items():
        handler.send_header(name, value)
    handler.end_headers()
    handler.wfile.write(body)


def _reject_disallowed_origin(handler):
    if _origin_allowed(handler):
        return False
    _json_response(handler, 403, {"ok": False, "error": "origin not allowed"})
    return True


def _read_body(handler):
    try:
        return read_json_body(handler)
    except RequestError as error:
        _json_response(handler, error.status, {"ok": False, "error": error.message})
        return None


def _require_auth(handler, auth):
    if auth.authenticated(handler):
        return True
    _json_response(handler, 401, {"ok": False, "error": "authentication required"})
    return False


def handle_options(handler):
    if not _origin_allowed(handler):
        handler.send_response(403)
        handler.send_header("Content-Length", "0")
        handler.end_headers()
        return
    handler.send_response(204)
    _send_cors_headers(handler)
    handler.send_header("Content-Length", "0")
    handler.end_headers()


def handle_post_login(handler, auth):
    if _reject_disallowed_origin(handler):
        return
    body = _read_body(handler)
    if body is None:
        return
    try:
        session_id = auth.login(handler, body.get("accessToken"))
    except RequestError as error:
        _json_response(handler, error.status, {"ok": False, "error": error.message})
        return
    secure = os.environ.get("ADA_COOKIE_SECURE") == "1"
    _json_response(handler, 200, {"ok": True}, headers={
        "Set-Cookie": session_cookie(session_id, secure=secure),
    })


def handle_get_session(handler, auth):
    if _reject_disallowed_origin(handler):
        return
    _json_response(handler, 200, {"ok": True, "authenticated": auth.authenticated(handler)})


def handle_post_logout(handler, auth):
    if _reject_disallowed_origin(handler) or not _require_auth(handler, auth):
        return
    body = _read_body(handler)
    if body is None:
        return
    auth.logout(handler)
    secure = os.environ.get("ADA_COOKIE_SECURE") == "1"
    _json_response(handler, 200, {"ok": True}, headers={
        "Set-Cookie": clear_session_cookie(secure=secure),
    })


def handle_get_profiles(handler, profiles, auth):
    if _reject_disallowed_origin(handler) or not _require_auth(handler, auth):
        return
    from server.profiles import public_profile
    _json_response(handler, 200, {
        "ok": True,
        "profiles": [public_profile(profile) for profile in profiles.values()],
    })


def handle_get_latest(handler, db_path, auth):
    if _reject_disallowed_origin(handler) or not _require_auth(handler, auth):
        return
    from server.storage import get_latest
    query = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
    key = query.get("project", [None])[0]
    if not key or len(key) > 64:
        _json_response(handler, 400, {"ok": False, "error": "valid project param required"})
        return
    result = get_latest(key, db_path)
    if not result:
        _json_response(handler, 404, {"ok": False, "error": "no snapshots found"})
        return
    _json_response(handler, 200, {"ok": True, "snapshot": result})


def handle_get_history(handler, db_path, auth):
    if _reject_disallowed_origin(handler) or not _require_auth(handler, auth):
        return
    from server.storage import get_history
    query = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
    key = query.get("project", [None])[0]
    period = query.get("period", [None])[0]
    if not key or len(key) > 64:
        _json_response(handler, 400, {"ok": False, "error": "valid project param required"})
        return
    if period not in (None, "7d", "30d", "90d"):
        _json_response(handler, 400, {"ok": False, "error": "invalid period"})
        return
    _json_response(handler, 200, {"ok": True, "snapshots": get_history(key, period, db_path)})


def handle_get_projects(handler, db_path, auth):
    if _reject_disallowed_origin(handler) or not _require_auth(handler, auth):
        return
    from server.storage import list_projects
    _json_response(handler, 200, {"ok": True, "projects": list_projects(db_path)})


def _profile_ids(body, profiles, *, all_when_empty=False):
    if all_when_empty and "profileIds" not in body:
        return list(profiles)
    values = body.get("profileIds")
    if values is None and body.get("profileId") is not None:
        values = [body.get("profileId")]
    if not isinstance(values, list) or not values or len(values) > _MAX_PROFILE_BATCH:
        raise RequestError(400, "profileIds must be a non-empty array")
    result = []
    for value in values:
        if not isinstance(value, str) or len(value) > 64 or value not in profiles:
            raise RequestError(404, "profile not found")
        if value not in result:
            result.append(value)
    return result


def _enqueue_profiles(handler, profiles, coordinator, body, *, all_when_empty=False):
    try:
        profile_ids = _profile_ids(body, profiles, all_when_empty=all_when_empty)
        queued, already = coordinator.enqueue([profiles[value] for value in profile_ids])
    except RequestError as error:
        _json_response(handler, error.status, {"ok": False, "error": error.message})
        return
    except QueueFullError as error:
        _json_response(handler, 429, {"ok": False, "error": str(error)})
        return
    _json_response(handler, 202, {"ok": True, "queued": queued, "alreadyRunning": already})


def handle_post_sync(handler, profiles, coordinator, auth):
    if _reject_disallowed_origin(handler) or not _require_auth(handler, auth):
        return
    body = _read_body(handler)
    if body is not None:
        _enqueue_profiles(handler, profiles, coordinator, body)


def handle_post_sync_all(handler, profiles, coordinator, auth):
    if _reject_disallowed_origin(handler) or not _require_auth(handler, auth):
        return
    body = _read_body(handler)
    if body is not None:
        _enqueue_profiles(handler, profiles, coordinator, body, all_when_empty=True)


def handle_get_sync_status(handler, coordinator, auth):
    if _reject_disallowed_origin(handler) or not _require_auth(handler, auth):
        return
    _json_response(handler, 200, {"ok": True, **coordinator.status()})


def _validate_jira_credentials(config):
    auth = base64.b64encode(f"{config['email']}:{config['api_token']}".encode()).decode()
    request = urllib.request.Request(
        f"{config['base_url']}/rest/api/3/myself",
        headers={"Accept": "application/json", "Authorization": f"Basic {auth}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def handle_post_validate_profile(handler, profiles, auth):
    if _reject_disallowed_origin(handler) or not _require_auth(handler, auth):
        return
    body = _read_body(handler)
    if body is None:
        return
    try:
        profile_id = _profile_ids(body, profiles)[0]
    except RequestError as error:
        _json_response(handler, error.status, {"ok": False, "error": error.message})
        return
    profile = profiles[profile_id]
    if profile["source"] != "jira":
        _json_response(handler, 400, {"ok": False, "error": "profile validation supports Jira only"})
        return
    try:
        _validate_jira_credentials(profile["config"])
    except urllib.error.HTTPError as error:
        message = "Jira credentials are invalid" if error.code in (401, 403) else f"Jira validation failed: HTTP {error.code}"
        _json_response(handler, 200, {"ok": False, "error": message})
        return
    except Exception as error:
        _json_response(handler, 200, {"ok": False, "error": f"Jira validation failed: {type(error).__name__}"})
        return
    _json_response(handler, 200, {"ok": True})
