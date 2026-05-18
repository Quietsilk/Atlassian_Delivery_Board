"""Ingestion pipeline: fetch_jira → calculate_metrics → save_snapshot.

Flow metrics use the interval [prev_snapshot_ts, now] so they are
independent of sync frequency (Step 10).
"""

import json
import base64
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

from server.metrics import (
    calculate_metrics, calculate_flow_metrics,
    _map_issue, _parse_dt, DONE,
)
from server.storage import save_snapshot, get_latest


PAGE_SIZE = 50


def _jira_request(url, auth, body=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Basic {auth}",
            "Accept":        "application/json",
            "Content-Type":  "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_jira(base_url, email, api_token, jql):
    """Fetch all issues + changelogs for the given JQL query."""
    auth = base64.b64encode(f"{email}:{api_token}".encode()).decode()

    all_issues = []
    next_page_token = None
    while True:
        body = {
            "jql": jql, "maxResults": PAGE_SIZE,
            "fieldsByKeys": True,
            "fields": ["summary", "status", "created", "resolutiondate", "assignee", "project"],
        }
        if next_page_token:
            body["nextPageToken"] = next_page_token
        data = _jira_request(f"{base_url}/rest/api/3/search/jql", auth, body)
        page = data.get("issues", [])
        all_issues.extend(page)
        print(f"  Fetched {len(all_issues)} issues so far")
        next_page_token = data.get("nextPageToken")
        if data.get("isLast", True) or not next_page_token or len(page) < PAGE_SIZE:
            break

    def _fetch_changelog(key):
        try:
            cl = _jira_request(f"{base_url}/rest/api/3/issue/{key}/changelog?maxResults=100", auth)
            values = cl.get("values", [])
            if len(values) == 100:
                print(f"  [warn] {key}: changelog at 100-entry limit — history may be truncated")
            return key, values
        except Exception:
            return key, []

    print(f"  Fetching changelogs for {len(all_issues)} issues (parallel)…")
    changelogs = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        for key, values in pool.map(_fetch_changelog, [i["key"] for i in all_issues]):
            changelogs[key] = values

    browse_base = base_url.rstrip("/")
    for issue in all_issues:
        issue["changelog"] = {"histories": changelogs.get(issue["key"], [])}
        issue["browseUrl"] = f"{browse_base}/browse/{issue['key']}"

    return all_issues


# ── Jira sprint completion ──────────────────────────────────────────────────

def _issue_keys(items):
    keys = set()
    for item in items or []:
        key = item.get("key") or item.get("issueKey")
        if key:
            keys.add(key)
    return keys


def _added_issue_keys(value):
    if isinstance(value, dict):
        return set(value.keys())
    if isinstance(value, list):
        return {v for v in value if isinstance(v, str)}
    return set()


def _sprint_completion_from_report(report):
    """Compute completion % from Jira sprint report contents.

    Formula:
      completed initial commitment / issues committed at sprint start * 100

    Jira sprint report exposes:
      completedIssues, issuesNotCompletedInCurrentSprint, puntedIssues,
      issueKeysAddedDuringSprint.
    """
    contents = report.get("contents") or {}
    completed = _issue_keys(contents.get("completedIssues"))
    not_completed = _issue_keys(contents.get("issuesNotCompletedInCurrentSprint"))
    removed = _issue_keys(contents.get("puntedIssues"))
    added = _added_issue_keys(contents.get("issueKeysAddedDuringSprint"))

    committed = (completed | not_completed | removed) - added
    completed_committed = completed - added

    basis = "start_commitment"
    if not committed:
        # Jira can report every issue as added after sprint start. In that case
        # use final sprint scope, excluding removed/punted issues, so the KPI is
        # still populated instead of returning an unusable empty commitment.
        committed = completed | not_completed
        completed_committed = completed
        basis = "final_scope"

    if not committed:
        return {
            "sprintCompletionPercent": None,
            "sprintCommittedCount": 0,
            "sprintCompletedCount": 0,
            "sprintAddedCount": len(added),
            "sprintRemovedCount": len(removed),
            "sprintCompletionBasis": basis,
        }

    return {
        "sprintCompletionPercent": round(len(completed_committed) / len(committed) * 100, 1),
        "sprintCommittedCount": len(committed),
        "sprintCompletedCount": len(completed_committed),
        "sprintAddedCount": len(added),
        "sprintRemovedCount": len(removed),
        "sprintCompletionBasis": basis,
    }


def _project_key_from_issues(project_key, issues):
    for issue in issues:
        fields = issue.get("fields") or {}
        project = fields.get("project") or {}
        if project.get("key"):
            return project["key"]
        key = issue.get("key") or ""
        if "-" in key:
            return key.split("-", 1)[0]
    return (project_key or "").upper()


def _fetch_jira_sprint_completion(base_url, auth, project_key, issues):
    """Fetch latest closed Jira sprint completion via Agile sprint report."""
    result = {
        "sprintCompletionPercent": None,
        "sprintCommittedCount": 0,
        "sprintCompletedCount": 0,
        "sprintAddedCount": 0,
        "sprintRemovedCount": 0,
        "sprintName": None,
        "sprintStartDate": None,
        "sprintCompleteDate": None,
    }

    key = _project_key_from_issues(project_key, issues)
    if not key:
        return result

    try:
        query = urllib.parse.urlencode({
            "projectKeyOrId": key,
            "type": "scrum",
            "maxResults": 50,
        })
        boards = _jira_request(f"{base_url}/rest/agile/1.0/board?{query}", auth).get("values", [])
        if not boards:
            return result
        board_id = boards[0]["id"]

        sprints = _jira_request(
            f"{base_url}/rest/agile/1.0/board/{board_id}/sprint?state=closed&maxResults=50",
            auth,
        ).get("values", [])
        if not sprints:
            return result

        closed = sorted(
            sprints,
            key=lambda s: s.get("completeDate") or s.get("endDate") or "",
            reverse=True,
        )
        project_named = [
            sprint for sprint in closed
            if key.lower() in (sprint.get("name") or "").lower()
        ]
        latest = (project_named or closed)[0]
        report_query = urllib.parse.urlencode({
            "rapidViewId": board_id,
            "sprintId": latest["id"],
        })
        report = _jira_request(
            f"{base_url}/rest/greenhopper/1.0/rapid/charts/sprintreport?{report_query}",
            auth,
        )
        result.update(_sprint_completion_from_report(report))
        result.update({
            "sprintName": latest.get("name"),
            "sprintStartDate": latest.get("startDate"),
            "sprintCompleteDate": latest.get("completeDate") or latest.get("endDate"),
        })
    except Exception as e:
        print(f"  [warn] sprint completion unavailable for {key}: {e}")
    return result


# ── WIP items ────────────────────────────────────────────────────────────────

def _compute_wip_items(issues, mapped):
    """Build a list of in-progress issue details for the StaleIssuesPanel.

    Returns at most 20 items, sorted by daysInProgress descending.
    Works with both Jira issues (have key/summary/assignee) and canonical
    issues from other adapters (fallback to id / empty strings).
    """
    now = datetime.now(timezone.utc)
    wip = []
    for issue, m in zip(issues, mapped):
        if not (m["started_at"] and not m["resolved_at"]):
            continue
        try:
            started = _parse_dt(m["started_at"])
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            days = round((now - started).total_seconds() / 86400, 1)
        except Exception:
            days = 0

        fields   = issue.get("fields") or {}
        key      = issue.get("key") or issue.get("id") or "—"
        title    = fields.get("summary") or fields.get("name") or ""
        assignee_raw = fields.get("assignee") or {}
        if isinstance(assignee_raw, dict):
            assignee = (assignee_raw.get("displayName")
                        or assignee_raw.get("name") or "")
        else:
            assignee = str(assignee_raw) if assignee_raw else ""
        status = (fields.get("status") or {}).get("name") or "In Progress"

        wip.append({
            "key":             key,
            "title":           title,
            "assignee":        assignee,
            "daysInProgress":  days,
            "status":          status,
            "url":             issue.get("browseUrl") or issue.get("url"),
            "blockedReason":   None,
        })

    wip.sort(key=lambda x: x["daysInProgress"], reverse=True)
    return wip[:20]


# ── Step 2: interval-based completed extraction ──────────────────────────────

def _get_completed_in_interval(mapped, since_ts):
    """Return mapped issues resolved strictly after since_ts.

    Replaces _count_resolved_since — returns items, not a count,
    so the same list can feed calculate_flow_metrics (Step 5/7).
    """
    if not since_ts:
        return []
    result = []
    for m in mapped:
        if m["resolved_at"]:
            try:
                if _parse_dt(m["resolved_at"]) > _parse_dt(since_ts):
                    result.append(m)
            except Exception:
                pass
    return result


# ── Step 8: predictability (kept as approximation) ──────────────────────────

def _calc_predictability(mapped):
    """Predictability % over a rolling 30-day window (approximation).

    committed = started before period_end AND not finished before period_start
    completed = resolved inside the 30-day window
    """
    period_end   = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=30)

    committed           = []
    completed_in_period = []
    for m in mapped:
        if not m["started_at"]:
            continue
        try:
            started_dt = _parse_dt(m["started_at"])
        except Exception:
            continue
        resolved_before_period = False
        if m["resolved_at"]:
            try:
                resolved_before_period = _parse_dt(m["resolved_at"]) < period_start
            except Exception:
                pass
        if started_dt < period_end and not resolved_before_period:
            committed.append(m)
        if m["resolved_at"]:
            try:
                resolved_dt = _parse_dt(m["resolved_at"])
                if period_start <= resolved_dt <= period_end:
                    completed_in_period.append(m)
            except Exception:
                pass

    if not committed:
        return 0
    return round(len(completed_in_period) / len(committed) * 100, 1)


# ── Shared pipeline ───────────────────────────────────────────────────────────

def _run_pipeline(project_key, issues, db_path, extra_metrics=None):
    """map → structural metrics → interval flow metrics → save snapshot."""
    mapped = [_map_issue(issue) for issue in issues]

    metrics = calculate_metrics(issues, mapped=mapped)

    prev     = get_latest(project_key, db_path)
    since_ts = prev["timestamp"] if prev else None

    completed_interval = _get_completed_in_interval(mapped, since_ts)
    metrics["throughput"] = len(completed_interval)

    completed_all = [m for m in mapped if m["resolved_at"]]
    flow_source   = completed_interval if completed_interval else completed_all
    metrics.update(calculate_flow_metrics(flow_source))

    metrics["predictabilityPercent"] = _calc_predictability(mapped)
    metrics["wipItems"]              = _compute_wip_items(issues, mapped)
    if extra_metrics:
        metrics.update(extra_metrics)

    ts = save_snapshot(project_key, metrics, db_path)
    print(f"[ingestion] {project_key}: snapshot saved at {ts}")
    return metrics


# ── Public entry points ───────────────────────────────────────────────────────

def run_ingestion(project_key, base_url, email, api_token, jql, db_path="snapshots.db"):
    """Fetch from Jira and run the ingestion pipeline."""
    print(f"[ingestion] {project_key}: fetching Jira…")
    auth = base64.b64encode(f"{email}:{api_token}".encode()).decode()
    issues = fetch_jira(base_url, email, api_token, jql)
    if not issues:
        raise ValueError("Jira query returned no issues; snapshot was not saved")
    sprint_metrics = _fetch_jira_sprint_completion(base_url.rstrip("/"), auth, project_key, issues)
    return _run_pipeline(project_key, issues, db_path, extra_metrics=sprint_metrics)


def run_ingestion_with_adapter(project_key, source, config, db_path="snapshots.db"):
    """Fetch via any registered adapter and run the ingestion pipeline.

    Parameters
    ----------
    project_key : str  — storage key
    source : str       — "jira" | "trello"
    config : dict      — adapter-specific config (see build_adapter)
    db_path : str      — SQLite path
    """
    from server.adapters import build_adapter

    print(f"[ingestion] {project_key}: fetching via {source} adapter…")
    adapter = build_adapter(source, config)
    issues  = adapter.fetch_and_normalize()
    if not issues:
        raise ValueError(f"{source} adapter returned no issues; snapshot was not saved")

    extra_metrics = None
    if (source or "").lower().strip() == "jira":
        auth = base64.b64encode(f"{config['email']}:{config['api_token']}".encode()).decode()
        extra_metrics = _fetch_jira_sprint_completion(
            config["base_url"].rstrip("/"),
            auth,
            project_key,
            issues,
        )

    return _run_pipeline(project_key, issues, db_path, extra_metrics=extra_metrics)
