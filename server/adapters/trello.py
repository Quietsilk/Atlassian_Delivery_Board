"""Trello adapter — REST API.

Config keys:
  api_key  — Trello API key
  token    — Trello OAuth token
  board_id — board ID (from board URL or API)

List names are matched case-insensitively against built-in defaults.
Override via lists_in_progress / lists_done (comma-separated) if needed.

Trello has no native changelog — card movement history is fetched from
the Action API (/1/cards/{id}/actions?filter=updateCard:idList).

Card creation timestamp is encoded in the first 8 hex chars of card.id
(BSON ObjectId convention).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
import time
from urllib.parse import urlencode

from server.adapters.base import (
    Adapter, CANONICAL_STARTED, CANONICAL_DONE,
    _with_retry, _http_get,
)

_BASE = "https://api.trello.com/1"
_MAX_ACTIONS = 1000
_DEFAULT_LOOKBACK_DAYS = 21
_MAX_WORKERS = 3


def _positive_env_int(name, default):
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _created_from_id(card_id: str) -> str:
    """Extract creation timestamp from Trello card ID (first 8 hex chars = unix ts)."""
    return _created_from_id_dt(card_id).isoformat()


def _created_from_id_dt(card_id: str) -> datetime:
    """Extract creation datetime from Trello card ID."""
    ts = int(card_id[:8], 16)
    return datetime.fromtimestamp(ts, tz=timezone.utc)


_DEFAULT_IN_PROGRESS = {
    "in progress", "doing", "in development", "in dev", "development",
    "в работе", "в разработке",
}
_DEFAULT_DONE = {
    "done", "released", "complete", "completed", "closed", "finished",
    "выполнено", "готово",
}
_LABEL_IN_PROGRESS = {
    "в работе", "на согласовании", "блок",
}
_LABEL_DONE = {
    "готово",
}
_LABEL_BACKLOG = {
    "бэклог", "долг", "отложено",
}
_LABEL_BLOCKED = {
    "блок",
}


def _parse_list_names(raw: str) -> set:
    return {name.strip().lower() for name in raw.split(",") if name.strip()}


def _parse_trello_dt(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _label_names(card: dict) -> list:
    labels = card.get("labels") or []
    return [(label.get("name") or "").strip() for label in labels if (label.get("name") or "").strip()]


def _has_lifecycle_signal(histories: list) -> bool:
    for history in histories:
        for item in history.get("items", []):
            if (item.get("toString") or "").lower() in (CANONICAL_STARTED, CANONICAL_DONE):
                return True
    return False


class TrelloAdapter(Adapter):
    source = "trello"

    def __init__(self, api_key: str, token: str, board_id: str,
                 lists_in_progress: str = "", lists_done: str = "",
                 lookback_days: int = _DEFAULT_LOOKBACK_DAYS):
        self.api_key   = api_key
        self.token     = token
        self.board_id  = board_id
        self._in_prog  = _parse_list_names(lists_in_progress) or _DEFAULT_IN_PROGRESS
        self._done     = _parse_list_names(lists_done)        or _DEFAULT_DONE
        self._lookback_days = max(int(lookback_days or _DEFAULT_LOOKBACK_DAYS), 1)
        self._headers = {
            "Authorization": (
                f'OAuth oauth_consumer_key="{api_key}", oauth_token="{token}"'
            ),
            "Accept": "application/json",
        }

    # ── Fetch ────────────────────────────────────────────────────────────────

    def fetch(self) -> list:
        deadline = time.monotonic() + _positive_env_int(
            "ADA_INGESTION_DEADLINE_SECONDS", 300
        )

        def require_time():
            if time.monotonic() >= deadline:
                raise TimeoutError("Trello ingestion deadline exceeded; snapshot was not saved")

        # Fetch all cards (including archived) with member info
        cards = _with_retry(lambda: _http_get(
            f"{_BASE}/boards/{self.board_id}/cards"
            f"?{urlencode({'filter': 'all', 'members': 'true'})}",
            headers=self._headers,
        ))
        require_time()
        max_cards = _positive_env_int("ADA_MAX_TRELLO_CARDS", 5000)
        if len(cards) > max_cards:
            raise RuntimeError("Trello card limit exceeded; snapshot was not saved")
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._lookback_days)
        # Fetch list names to resolve idList → list name
        lists = _with_retry(lambda: _http_get(
            f"{_BASE}/boards/{self.board_id}/lists",
            headers=self._headers,
        ))
        require_time()
        list_names = {lst["id"]: lst["name"] for lst in lists}
        recent_ids = {
            card["id"] for card in cards
            if (_parse_trello_dt(card.get("dateLastActivity")) or _created_from_id_dt(card["id"])) >= cutoff
        }
        print(f"  [trello] {len(cards)} cards, fetching actions for {len(recent_ids)} changed in last {self._lookback_days}d…")

        def _fetch_actions(card):
            require_time()
            if card["id"] not in recent_ids:
                card["_actions"] = []
                card["_listNames"] = list_names
                return card
            actions = _with_retry(lambda: _http_get(
                f"{_BASE}/cards/{card['id']}/actions"
                f"?{urlencode({'filter': 'updateCard:idList', 'limit': _MAX_ACTIONS})}",
                headers=self._headers,
            ))
            if len(actions) >= _MAX_ACTIONS:
                raise RuntimeError(
                    "Trello action limit reached; snapshot was not saved"
                )
            card["_actions"]   = actions
            card["_listNames"] = list_names
            return card

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            enriched = list(pool.map(_fetch_actions, cards))

        require_time()

        print(f"  [trello] enriched {len(enriched)} cards")
        return enriched

    # ── Normalize ────────────────────────────────────────────────────────────

    def normalize(self, raw_issues: list) -> list:
        return [self._to_canonical(card) for card in raw_issues]

    def _canonical_status(self, list_name: str) -> str:
        name = list_name.lower().strip()
        if name in self._done:
            return CANONICAL_DONE
        if name in self._in_prog:
            return CANONICAL_STARTED
        return list_name  # treated as backlog by metrics layer

    def _status_from_labels(self, card: dict):
        names = _label_names(card)
        lowered = {name.lower() for name in names}
        if lowered & _LABEL_DONE:
            return CANONICAL_DONE
        if lowered & _LABEL_IN_PROGRESS:
            return CANONICAL_STARTED
        for name in names:
            if name.lower() in _LABEL_BACKLOG:
                return name
        return None

    def _to_canonical(self, card: dict) -> dict:
        actions    = card.get("_actions", [])
        list_names = card.get("_listNames", {})

        current_list = list_names.get(card.get("idList", ""), "")
        label_status = self._status_from_labels(card)
        # Archived cards that are in a "done" list count as done;
        # otherwise fall back to "done" if closed
        if label_status:
            current_status = label_status
        elif card.get("closed") and not current_list:
            current_status = CANONICAL_DONE
        else:
            current_status = self._canonical_status(current_list)

        resolution_date = None
        if current_status == CANONICAL_DONE:
            # Best approximation: last action date or dateLastActivity
            resolution_date = (
                actions[0]["date"] if actions else card.get("dateLastActivity")
            )

        # Build changelog from actions (newest-first from API → reverse to oldest-first)
        histories = []
        for action in reversed(actions):
            data         = action.get("data", {})
            list_before  = (data.get("listBefore") or {}).get("name", "")
            list_after   = (data.get("listAfter")  or {}).get("name", "")
            if not list_before or not list_after:
                continue
            histories.append({
                "created": action["date"],
                "items": [{
                    "field":      "status",
                    "fromString": self._canonical_status(list_before),
                    "toString":   self._canonical_status(list_after),
                }],
            })

        if not histories or (label_status and not _has_lifecycle_signal(histories)):
            histories = self._synthesise_lifecycle(card, current_status, resolution_date)

        # Assignee: first member's fullName (Trello allows multiple)
        members  = card.get("members") or []
        assignee = members[0].get("fullName", "") if members else ""

        return {
            "key":    card.get("shortLink", card["id"]),
            "id":     card["id"],
            "url":    f"https://trello.com/c/{card.get('shortLink', card['id'])}",
            "fields": {
                "summary":        card.get("name", ""),
                "created":        _created_from_id(card["id"]),
                "resolutiondate": resolution_date,
                "status":         {"name": current_status},
                "issuetype":      None,
                "labels":         _label_names(card),
                "assignee":       {"displayName": assignee} if assignee else None,
            },
            "changelog": {"histories": histories},
            "blockedReason": "БЛОК" if {name.lower() for name in _label_names(card)} & _LABEL_BLOCKED else None,
        }

    @staticmethod
    def _synthesise_lifecycle(card: dict, status: str, resolution_date) -> list:
        """Fallback when no list-move actions exist."""
        created_at = _created_from_id(card["id"])
        histories  = []
        if status == CANONICAL_STARTED and created_at:
            histories.append({
                "created": created_at,
                "items": [{"field": "status", "fromString": "backlog", "toString": CANONICAL_STARTED}],
            })
        elif status == CANONICAL_DONE and resolution_date:
            histories.append({
                "created": created_at,
                "items": [{"field": "status", "fromString": "backlog", "toString": CANONICAL_STARTED}],
            })
            histories.append({
                "created": resolution_date,
                "items": [{"field": "status", "fromString": CANONICAL_STARTED, "toString": CANONICAL_DONE}],
            })
        return histories
