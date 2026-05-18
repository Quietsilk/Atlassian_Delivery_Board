"""Metric calculations — pure functions, no period/cutoff dependency.

All metrics are derived from Jira changelog and computed at ingestion time.
Period filtering is done at the API layer (over stored snapshots), never here.
"""

from datetime import datetime, timezone

STARTED = {"in progress", "selected for development", "в работе", "in development"}
DONE    = {"done", "closed", "resolved", "выполнено", "complete"}


def _parse_dt(s):
    s = s.replace("Z", "+00:00")
    # Python 3.9 fromisoformat requires +HH:MM, not +HHMM
    if len(s) > 5 and s[-5] in ("+", "-") and ":" not in s[-5:]:
        s = s[:-2] + ":" + s[-2:]
    return datetime.fromisoformat(s)


def _percentile(values, p):
    """Return the p-th percentile of a list of numeric values (p in 0–100)."""
    if not values:
        return 0
    sv = sorted(values)
    k  = (len(sv) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(sv) - 1)
    return round(sv[lo] + (k - lo) * (sv[hi] - sv[lo]), 1)


def _map_issue(issue):
    """Extract timing fields from a single Jira issue with changelog."""
    histories = issue.get("changelog", {}).get("histories", [])
    transitions = sorted(
        [
            {"date": h["created"], "from": i.get("fromString", ""), "to": i.get("toString", "")}
            for h in histories
            for i in h.get("items", [])
            if i.get("field") == "status"
        ],
        key=lambda t: t["date"]
    )

    last_done = next((t for t in reversed(transitions) if t["to"].lower() in DONE), None)
    started   = next((t for t in reversed(transitions)
                      if t["to"].lower() in STARTED
                      and (not last_done or t["date"] <= last_done["date"])), None)
    status    = (issue.get("fields") or {}).get("status", {}).get("name", "")
    is_done   = status.lower() in DONE
    resolved  = None
    if is_done:
        resolved = (issue.get("fields") or {}).get("resolutiondate") or (last_done["date"] if last_done else None)
    reopened = any(t["from"].lower() in DONE and t["to"].lower() not in DONE for t in transitions)

    return {
        "started_at":  started["date"] if started else None,
        "resolved_at": resolved,
        "created_at":  (issue.get("fields") or {}).get("created"),
        "reopened":    reopened,
    }


def calculate_flow_metrics(completed_items):
    """Compute P50/P85 flow metrics from a list of completed mapped issues.

    Args:
        completed_items: list of _map_issue() dicts with resolved_at set.

    Returns dict with:
        cycleTimeP50, cycleTimeP85  — days In Progress → Done
        timeToMarketP50, timeToMarketP85  — days created → Done
        flowEfficiencyPercent  — P50 cycle / P50 TTM × 100 (capped 100%)
    """
    cycle_days = []
    lead_days  = []

    for m in completed_items:
        if m["started_at"] and m["resolved_at"]:
            try:
                d = (_parse_dt(m["resolved_at"]) - _parse_dt(m["started_at"])).total_seconds() / 86400
                if d >= 0:
                    cycle_days.append(d)
            except Exception:
                pass
        if m["created_at"] and m["resolved_at"]:
            try:
                d = (_parse_dt(m["resolved_at"]) - _parse_dt(m["created_at"])).total_seconds() / 86400
                if d >= 0:
                    lead_days.append(d)
            except Exception:
                pass

    cycle_p50 = _percentile(cycle_days, 50)
    cycle_p85 = _percentile(cycle_days, 85)
    ttm_p50   = _percentile(lead_days,  50)
    ttm_p85   = _percentile(lead_days,  85)
    flow_eff  = round(min(cycle_p50 / ttm_p50 * 100, 100.0), 1) if ttm_p50 > 0 else 0

    return {
        "cycleTimeP50":          cycle_p50,
        "cycleTimeP85":          cycle_p85,
        "timeToMarketP50":       ttm_p50,
        "timeToMarketP85":       ttm_p85,
        "flowEfficiencyPercent": flow_eff,
    }


def calculate_metrics(issues, mapped=None):
    """Compute structural delivery metrics from a list of Jira issues.

    Accepts an optional pre-computed mapped list (Step 1 optimization).
    Flow metrics (cycle time, TTM, flow efficiency) are NOT computed here —
    they are interval-based and computed by the ingestion layer via
    calculate_flow_metrics(completed_in_interval).

    Returns a dict with:
        backlogSize, inProgressCount, backlogAgingDays
    """
    if mapped is None:
        mapped = [_map_issue(issue) for issue in issues]

    in_progress = [m for m in mapped if m["started_at"] and not m["resolved_at"]]
    backlog     = [m for m in mapped if not m["started_at"] and not m["resolved_at"]]
    completed   = [m for m in mapped if m["resolved_at"]]

    # Backlog aging: avg days from created_at to now for pure backlog issues
    now = datetime.now(timezone.utc)
    aging_vals = []
    for m in backlog:
        if m["created_at"]:
            try:
                created = _parse_dt(m["created_at"])
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                aging_vals.append((now - created).total_seconds() / 86400)
            except Exception:
                pass
    backlog_aging = round(sum(aging_vals) / len(aging_vals), 1) if aging_vals else 0

    return {
        "backlogSize":      len(backlog),
        "inProgressCount":  len(in_progress),
        "completedCount":   len(completed),
        "backlogAgingDays": backlog_aging,
    }
