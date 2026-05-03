"""ClickUp adapter — REST API.

Quality: MEDIUM — custom statuses require normalization; history may be absent.

Status normalization (case-insensitive, substring match):
  "in progress" / "in dev" / "started" / "в работе" → "in progress"
  "done" / "complete" / "closed" / "resolved" / "finished" → "done"
  everything else                                           → left as-is (treated as backlog)

Date fields:
  date_created → created
  date_done    → resolutiondate  (ms epoch string → ISO-8601)
"""

from server.adapters.base import (
    Adapter, CANONICAL_STARTED, CANONICAL_DONE,
    _with_retry, _http_get,
)

BASE     = "https://api.clickup.com/api/v2"
PAGE_SIZE = 100   # ClickUp page size cap

# Keywords for status normalization
_IN_PROGRESS_KW = ("in progress", "in dev", "started", "в работе", "active", "doing")
_DONE_KW        = ("done", "complete", "closed", "resolved", "finished", "released")


def _normalize_status(raw: str) -> str:
    """Map a ClickUp custom status string to a canonical status."""
    n = (raw or "").lower().strip()
    if any(k in n for k in _IN_PROGRESS_KW):
        return CANONICAL_STARTED
    if any(k in n for k in _DONE_KW):
        return CANONICAL_DONE
    return n  # leave unknown statuses as-is (treated as backlog by metrics layer)


def _ms_to_iso(ms_str):
    """Convert ClickUp millisecond-epoch string/int to ISO-8601 UTC string."""
    if not ms_str:
        return None
    try:
        ms = int(ms_str)
        if ms == 0:
            return None
        from datetime import datetime, timezone
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
    except Exception:
        return None


class ClickUpAdapter(Adapter):
    source = "clickup"

    def __init__(self, api_key: str, list_id: str):
        self.list_id  = list_id
        self._headers = {
            "Authorization": api_key,
            "Accept":        "application/json",
        }

    # ── Fetch ────────────────────────────────────────────────────────────────

    def fetch(self) -> list:
        tasks = self._fetch_tasks()
        return tasks

    def _fetch_tasks(self) -> list:
        """Fetch all tasks from the list, handling ClickUp's page-based pagination."""
        tasks = []
        page  = 0
        while True:
            url = (
                f"{BASE}/list/{self.list_id}/task"
                f"?include_closed=true&subtasks=true"
                f"&page={page}&limit={PAGE_SIZE}"
            )
            data = _with_retry(lambda u=url: _http_get(u, self._headers))
            batch = data.get("tasks", [])
            tasks.extend(batch)
            print(f"  [clickup] fetched {len(tasks)} tasks so far")
            # ClickUp returns fewer than limit on last page
            if len(batch) < PAGE_SIZE:
                break
            page += 1
        return tasks

    # ── Normalize ────────────────────────────────────────────────────────────

    def normalize(self, raw_issues: list) -> list:
        return [self._to_canonical(t) for t in raw_issues]

    def _to_canonical(self, task: dict) -> dict:
        created_at  = _ms_to_iso(task.get("date_created"))
        resolved_at = _ms_to_iso(task.get("date_done"))

        raw_status      = (task.get("status") or {}).get("status", "")
        canonical_status = _normalize_status(raw_status)

        histories = self._build_changelog(task, created_at, resolved_at, canonical_status)

        return {
            "fields": {
                "created":        created_at,
                "resolutiondate": resolved_at,
                "status":         {"name": canonical_status},
            },
            "changelog": {"histories": histories},
        }

    @staticmethod
    def _build_changelog(task, created_at, resolved_at, canonical_status):
        """Build a changelog from ClickUp task history (if present).

        ClickUp tasks include a ``history`` array only when fetched with
        ``?include_history=true`` (premium feature).  We attempt to use it;
        otherwise fall back to a synthesised lifecycle.
        """
        # --- Try to use real history entries ------------------------------------
        history_entries = task.get("history") or []
        histories = []
        for entry in sorted(history_entries, key=lambda e: e.get("date", "")):
            if entry.get("field") != "status":
                continue
            date_iso = _ms_to_iso(entry.get("date"))
            if not date_iso:
                continue
            from_val = _normalize_status(entry.get("before", {}).get("status", ""))
            to_val   = _normalize_status(entry.get("after",  {}).get("status", ""))
            histories.append({
                "created": date_iso,
                "items": [{"field": "status", "fromString": from_val, "toString": to_val}],
            })

        if histories:
            return histories

        # --- Fallback: synthesise minimal lifecycle ----------------------------
        if canonical_status == CANONICAL_DONE and resolved_at:
            if created_at:
                histories.append({
                    "created": created_at,
                    "items": [{"field": "status", "fromString": "backlog", "toString": CANONICAL_STARTED}],
                })
            histories.append({
                "created": resolved_at,
                "items": [{"field": "status", "fromString": CANONICAL_STARTED, "toString": CANONICAL_DONE}],
            })
        elif canonical_status == CANONICAL_STARTED and created_at:
            histories.append({
                "created": created_at,
                "items": [{"field": "status", "fromString": "backlog", "toString": CANONICAL_STARTED}],
            })

        return histories
