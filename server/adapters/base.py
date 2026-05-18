"""Base adapter interface.

All adapters MUST return issues in the canonical Jira-shaped format so that
calculate_metrics() / calculate_flow_metrics() can consume them without
any modification.

Canonical issue shape:
{
    "fields": {
        "created":        "<ISO datetime>",
        "resolutiondate": "<ISO datetime | null>",
        "status":         {"name": "<string>"},
    },
    "changelog": {
        "histories": [
            {
                "created": "<ISO datetime>",
                "items": [
                    {
                        "field":      "status",
                        "fromString": "<string>",
                        "toString":   "<string>",
                    }
                ],
            }
        ]
    },
}
"""

import time
import urllib.request
import urllib.error
import json


# ── Status normalization maps ────────────────────────────────────────────────

# Metrics layer recognises these sets (case-insensitive in metrics.py)
CANONICAL_STARTED = "in progress"
CANONICAL_DONE    = "done"


def normalize_status(raw_name: str, status_map: dict) -> str:
    """Map a source-specific status name to a canonical status.

    status_map: {source_status_lower → canonical_status}
    Falls through to returning raw_name (treated as backlog by metrics).
    """
    return status_map.get(raw_name.lower().strip(), raw_name)


# ── Retry / HTTP helpers ─────────────────────────────────────────────────────

def _with_retry(fn, max_attempts: int = 3, backoff: float = 2.0):
    """Call fn() up to max_attempts times with exponential backoff."""
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            if e.code == 429:                  # rate-limited — always retry
                time.sleep(backoff ** attempt)
            elif e.code >= 500:                # server error — retry
                time.sleep(backoff ** attempt)
            else:
                raise                          # 4xx client error — fail fast
            last_exc = e
        except Exception as e:
            time.sleep(backoff ** attempt)
            last_exc = e
    raise last_exc


def _http_get(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _http_post(url: str, headers: dict, body: dict) -> dict:
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers={**headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


# ── Abstract base ────────────────────────────────────────────────────────────

class Adapter:
    """Abstract adapter. Subclasses implement fetch() and normalize()."""

    source: str = "unknown"

    def fetch(self) -> list:
        """Return raw issues from the source API."""
        raise NotImplementedError

    def normalize(self, raw_issues: list) -> list:
        """Convert raw issues into the canonical Jira-shaped format."""
        raise NotImplementedError

    def fetch_and_normalize(self) -> list:
        """Convenience: fetch then normalize in one call."""
        raw = self.fetch()
        return self.normalize(raw)


# ── Adapter factory ──────────────────────────────────────────────────────────

def build_adapter(source: str, config: dict) -> Adapter:
    """Return the correct Adapter subclass for *source*.

    config keys per source:
      jira:    base_url, email, api_token, jql
      trello:  api_key, token, board_id
    """
    source = (source or "jira").lower().strip()
    if source == "jira":
        from server.adapters.jira import JiraAdapter
        return JiraAdapter(
            base_url  = config["base_url"],
            email     = config["email"],
            api_token = config["api_token"],
            jql       = config["jql"],
        )
    if source == "trello":
        from server.adapters.trello import TrelloAdapter
        return TrelloAdapter(
            api_key           = config["api_key"],
            token             = config["token"],
            board_id          = config["board_id"],
            lists_in_progress = config.get("lists_in_progress", ""),
            lists_done        = config.get("lists_done", ""),
        )
    raise ValueError(f"Unknown source: {source!r}. Supported: jira, trello")
