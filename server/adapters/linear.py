"""Linear adapter — GraphQL API.

Quality: HIGH — full lifecycle via issue history.

Linear state types map to canonical statuses:
  started   → "in progress"
  completed → "done"
  cancelled → "done"       (treated as resolved for flow metrics)
  backlog / unstarted → left as-is (backlog in metrics layer)
"""

from server.adapters.base import (
    Adapter, CANONICAL_STARTED, CANONICAL_DONE,
    _with_retry, _http_post,
)

ENDPOINT = "https://api.linear.app/graphql"

# Linear stateType → canonical status name
_STATE_TYPE_MAP = {
    "started":   CANONICAL_STARTED,
    "completed": CANONICAL_DONE,
    "cancelled": CANONICAL_DONE,
}

_ISSUES_QUERY = """
query($teamId: String!, $filter: IssueFilter, $after: String) {
  issues(
    filter: { team: { id: { eq: $teamId } } }
    first: 250
    after: $after
  ) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      identifier
      createdAt
      completedAt
      canceledAt
      state { name type }
      history(first: 50) {
        nodes {
          createdAt
          fromState { name type }
          toState   { name type }
        }
      }
    }
  }
}
"""


class LinearAdapter(Adapter):
    source = "linear"

    def __init__(self, api_key: str, team_id: str, filter_: dict = None):
        self.api_key  = api_key
        self.team_id  = team_id
        self.filter_  = filter_ or {}
        self._headers = {
            "Authorization": api_key,
            "Content-Type":  "application/json",
        }

    # ── Fetch ────────────────────────────────────────────────────────────────

    def fetch(self) -> list:
        all_nodes = []
        cursor    = None
        while True:
            variables = {"teamId": self.team_id, "after": cursor}
            if self.filter_:
                variables["filter"] = self.filter_

            def _call(variables=variables):
                return _http_post(ENDPOINT, self._headers, {
                    "query":     _ISSUES_QUERY,
                    "variables": variables,
                })

            data  = _with_retry(_call)
            page  = data["data"]["issues"]
            nodes = page["nodes"]
            all_nodes.extend(nodes)
            print(f"  [linear] fetched {len(all_nodes)} issues so far")

            if not page["pageInfo"]["hasNextPage"]:
                break
            cursor = page["pageInfo"]["endCursor"]

        return all_nodes

    # ── Normalize ────────────────────────────────────────────────────────────

    def normalize(self, raw_issues: list) -> list:
        return [self._to_canonical(issue) for issue in raw_issues]

    def _to_canonical(self, issue: dict) -> dict:
        state_type = (issue.get("state") or {}).get("type", "")
        state_name = (issue.get("state") or {}).get("name", "backlog")

        # Canonical status name
        canonical_status = _STATE_TYPE_MAP.get(state_type, state_name)

        # Resolution date: completedAt or canceledAt
        resolution_date = issue.get("completedAt") or issue.get("canceledAt")

        # Build changelog from history nodes
        histories = []
        for h in (issue.get("history") or {}).get("nodes", []):
            from_state = h.get("fromState") or {}
            to_state   = h.get("toState")   or {}
            if not from_state or not to_state:
                continue
            from_type = from_state.get("type", "")
            to_type   = to_state.get("type",   "")
            histories.append({
                "created": h["createdAt"],
                "items": [{
                    "field":      "status",
                    "fromString": _STATE_TYPE_MAP.get(from_type, from_state.get("name", "")),
                    "toString":   _STATE_TYPE_MAP.get(to_type,   to_state.get("name",   "")),
                }],
            })

        # Fallback: if no history but issue is done/started, synthesise minimal lifecycle
        if not histories:
            histories = self._synthesise_lifecycle(issue, canonical_status)

        return {
            "fields": {
                "created":        issue["createdAt"],
                "resolutiondate": resolution_date,
                "status":         {"name": canonical_status},
            },
            "changelog": {"histories": histories},
        }

    @staticmethod
    def _synthesise_lifecycle(issue: dict, canonical_status: str) -> list:
        """Fallback when history is empty: synthesise minimal transitions."""
        histories = []
        created_at = issue.get("createdAt")
        resolved_at = issue.get("completedAt") or issue.get("canceledAt")

        if canonical_status == CANONICAL_STARTED and created_at:
            histories.append({
                "created": created_at,
                "items": [{"field": "status", "fromString": "backlog", "toString": CANONICAL_STARTED}],
            })
        elif canonical_status == CANONICAL_DONE and resolved_at:
            if created_at:
                histories.append({
                    "created": created_at,
                    "items": [{"field": "status", "fromString": "backlog", "toString": CANONICAL_STARTED}],
                })
            histories.append({
                "created": resolved_at,
                "items": [{"field": "status", "fromString": CANONICAL_STARTED, "toString": CANONICAL_DONE}],
            })
        return histories
