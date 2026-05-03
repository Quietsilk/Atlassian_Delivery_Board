"""Asana adapter — REST API.

Quality: MEDIUM — lifecycle limited to TODO → DONE; stories used for transitions.

Status normalisation:
  completed=true              → "done"
  story type=enum_change name containing "in progress" → "in progress"
  everything else             → "backlog"
"""

from server.adapters.base import (
    Adapter, CANONICAL_STARTED, CANONICAL_DONE,
    _with_retry, _http_get,
)
from concurrent.futures import ThreadPoolExecutor

BASE = "https://app.asana.com/api/1.0"
PAGE_SIZE = 100


def _status_from_name(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ("in progress", "in dev", "в работе", "started")):
        return CANONICAL_STARTED
    if any(k in n for k in ("done", "complete", "closed", "resolved", "finished")):
        return CANONICAL_DONE
    return name


class AsanaAdapter(Adapter):
    source = "asana"

    def __init__(self, access_token: str, project_gid: str):
        self.project_gid = project_gid
        self._headers    = {
            "Authorization": f"Bearer {access_token}",
            "Accept":        "application/json",
        }

    # ── Fetch ────────────────────────────────────────────────────────────────

    def fetch(self) -> list:
        tasks    = self._fetch_tasks()
        stories  = self._fetch_stories_parallel(tasks)
        for task in tasks:
            task["_stories"] = stories.get(task["gid"], [])
        return tasks

    def _fetch_tasks(self) -> list:
        tasks  = []
        offset = None
        fields = "gid,created_at,completed,completed_at,name,memberships.section.name"
        while True:
            url = (
                f"{BASE}/tasks?project={self.project_gid}"
                f"&opt_fields={fields}&limit={PAGE_SIZE}"
                f"&completed_since=now"   # fetch all (completed + incomplete)
            )
            # Asana uses offset-based pagination
            if offset:
                url += f"&offset={offset}"

            # completed_since=now returns only incomplete; omit to get all
            url = (
                f"{BASE}/tasks?project={self.project_gid}"
                f"&opt_fields={fields}&limit={PAGE_SIZE}"
            )
            if offset:
                url += f"&offset={offset}"

            data = _with_retry(lambda u=url: _http_get(u, self._headers))
            tasks.extend(data.get("data", []))
            print(f"  [asana] fetched {len(tasks)} tasks so far")
            next_page = (data.get("next_page") or {})
            offset    = next_page.get("offset")
            if not offset:
                break
        return tasks

    def _fetch_stories_parallel(self, tasks: list) -> dict:
        def _fetch_one(gid):
            url  = f"{BASE}/tasks/{gid}/stories?opt_fields=created_at,type,text,resource_subtype"
            data = _with_retry(lambda u=url: _http_get(u, self._headers))
            return gid, data.get("data", [])

        results = {}
        with ThreadPoolExecutor(max_workers=10) as pool:
            for gid, stories in pool.map(_fetch_one, [t["gid"] for t in tasks]):
                results[gid] = stories
        return results

    # ── Normalize ────────────────────────────────────────────────────────────

    def normalize(self, raw_issues: list) -> list:
        return [self._to_canonical(t) for t in raw_issues]

    def _to_canonical(self, task: dict) -> dict:
        completed      = task.get("completed", False)
        completed_at   = task.get("completed_at")
        created_at     = task.get("created_at")
        resolution     = completed_at if completed else None
        current_status = CANONICAL_DONE if completed else "backlog"

        histories = self._build_changelog(task.get("_stories", []), created_at, resolution)

        return {
            "fields": {
                "created":        created_at,
                "resolutiondate": resolution,
                "status":         {"name": current_status},
            },
            "changelog": {"histories": histories},
        }

    @staticmethod
    def _build_changelog(stories: list, created_at, completed_at) -> list:
        """Build changelog from Asana stories.

        Asana stories with resource_subtype=enum_change or text containing
        status keywords can indicate transitions. We extract what we can.
        """
        histories = []
        for story in sorted(stories, key=lambda s: s.get("created_at", "")):
            if story.get("type") != "system":
                continue
            text    = (story.get("text") or "").lower()
            created = story.get("created_at")
            if not created:
                continue

            # Detect "in progress" transition from story text
            if any(k in text for k in ("in progress", "in dev", "started", "в работе")):
                histories.append({
                    "created": created,
                    "items": [{"field": "status", "fromString": "backlog", "toString": CANONICAL_STARTED}],
                })
            # Detect completion
            elif any(k in text for k in ("marked complete", "completed", "done", "closed")):
                prev = histories[-1]["items"][0]["toString"] if histories else "backlog"
                histories.append({
                    "created": created,
                    "items": [{"field": "status", "fromString": prev, "toString": CANONICAL_DONE}],
                })

        # Fallback: if completed but no histories, synthesise
        if not histories and completed_at:
            if created_at:
                histories.append({
                    "created": created_at,
                    "items": [{"field": "status", "fromString": "backlog", "toString": CANONICAL_STARTED}],
                })
            histories.append({
                "created": completed_at,
                "items": [{"field": "status", "fromString": CANONICAL_STARTED, "toString": CANONICAL_DONE}],
            })

        return histories
