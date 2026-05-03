"""HTTP API handler for the new architecture.

Routes:
  GET  /latest?project=KEY          → latest snapshot
  GET  /history?project=KEY&period= → filtered snapshots
  POST /sync                        → trigger ingestion (returns {ok, queued})

Constraint: calculate_metrics is NEVER called here — only storage reads.
"""

import json
import os
import threading
import urllib.parse


def _json_response(handler, code, data):
    body = json.dumps(data).encode()
    handler.send_response(code)
    handler.send_header("Content-Type",   "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin",  "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


def handle_get_latest(handler, db_path):
    """GET /latest?project=KEY"""
    from server.storage import get_latest
    qs  = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
    key = qs.get("project", [None])[0]
    if not key:
        _json_response(handler, 400, {"ok": False, "error": "project param required"})
        return
    result = get_latest(key, db_path)
    if not result:
        _json_response(handler, 404, {"ok": False, "error": "no snapshots found"})
        return
    _json_response(handler, 200, {"ok": True, "snapshot": result})


def handle_get_history(handler, db_path):
    """GET /history?project=KEY&period=30d"""
    from server.storage import get_history
    qs     = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
    key    = qs.get("project", [None])[0]
    period = qs.get("period",  [None])[0]
    if not key:
        _json_response(handler, 400, {"ok": False, "error": "project param required"})
        return
    snapshots = get_history(key, period=period, db_path=db_path)
    _json_response(handler, 200, {"ok": True, "snapshots": snapshots})


def handle_post_sync(handler, db_path, jira_credentials):
    """POST /sync — triggers ingestion asynchronously.

    Jira body  (JSON): { project, baseUrl, email, apiToken, jql }
    Linear body       : { project, source:"linear",  apiKey, teamId [, filter_] }
    Asana body        : { project, source:"asana",   accessToken, projectGid }
    ClickUp body      : { project, source:"clickup", apiKey, listId }

    Returns immediately with { ok: true, queued: true }.
    Does NOT return metrics — caller must poll /latest.
    """
    length = int(handler.headers.get("Content-Length", 0))
    body = json.loads(handler.rfile.read(length)) if length else {}

    project = body.get("project", "").strip()
    source  = body.get("source",  "jira").lower().strip()

    if not project:
        _json_response(handler, 400, {"ok": False, "error": "project is required"})
        return

    # ── Build adapter config per source ─────────────────────────────────────
    if source == "jira":
        base_url  = body.get("baseUrl",  jira_credentials.get("base_url",  "")).rstrip("/")
        email     = body.get("email",    jira_credentials.get("email",     ""))
        api_token = body.get("apiToken", jira_credentials.get("api_token", ""))
        jql       = body.get("jql", "").strip()
        if not all([base_url, email, api_token, jql]):
            _json_response(handler, 400, {"ok": False,
                "error": "jira requires: baseUrl, email, apiToken, jql"})
            return
        config = {"base_url": base_url, "email": email, "api_token": api_token, "jql": jql}

    elif source == "linear":
        api_key = body.get("apiKey", "").strip()
        team_id = body.get("teamId", "").strip()
        if not all([api_key, team_id]):
            _json_response(handler, 400, {"ok": False,
                "error": "linear requires: apiKey, teamId"})
            return
        config = {"api_key": api_key, "team_id": team_id,
                  "filter_": body.get("filter_", {})}

    elif source == "asana":
        access_token = body.get("accessToken", "").strip()
        project_gid  = body.get("projectGid",  "").strip()
        if not all([access_token, project_gid]):
            _json_response(handler, 400, {"ok": False,
                "error": "asana requires: accessToken, projectGid"})
            return
        config = {"access_token": access_token, "project_gid": project_gid}

    elif source == "clickup":
        api_key = body.get("apiKey", "").strip()
        list_id = body.get("listId", "").strip()
        if not all([api_key, list_id]):
            _json_response(handler, 400, {"ok": False,
                "error": "clickup requires: apiKey, listId"})
            return
        config = {"api_key": api_key, "list_id": list_id}

    else:
        _json_response(handler, 400, {"ok": False,
            "error": f"unknown source {source!r}; supported: jira, linear, asana, clickup"})
        return

    # ── Launch background ingestion thread ───────────────────────────────────
    def _run():
        from server.ingestion import run_ingestion_with_adapter
        try:
            run_ingestion_with_adapter(project, source, config, db_path)
        except Exception as e:
            print(f"[api] sync error for {project} ({source}): {e}")

    threading.Thread(target=_run, daemon=True).start()
    _json_response(handler, 202, {"ok": True, "queued": True})
