"""Trello adapter — REST API.

Config keys:
  api_key          — Trello API key
  token            — Trello OAuth token
  board_id         — board ID (from board URL or API)
  lists_in_progress — comma-separated list names that mean "in progress"
  lists_done        — comma-separated list names that mean "done"

Trello has no native changelog — card movement history is fetched from
the Action API (/1/cards/{id}/actions?filter=updateCard:idList).

Card creation timestamp is encoded in the first 8 hex chars of card.id
(BSON ObjectId convention).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from server.adapters.base import (
    Adapter, CANONICAL_STARTED, CANONICAL_DONE,
    _with_retry, _http_get,
)

_BASE = "https://api.trello.com/1"
_MAX_ACTIONS = 1000


def _created_from_id(card_id: str) -> str:
    """Extract creation timestamp from Trello card ID (first 8 hex chars = unix ts)."""
    ts = int(card_id[:8], 16)
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _parse_list_names(raw: str) -> set:
    return {name.strip().lower() for name in raw.split(",") if name.strip()}


class TrelloAdapter(Adapter):
    source = "trello"

    def __init__(self, api_key: str, token: str, board_id: str,
                 lists_in_progress: str = "", lists_done: str = ""):
        self.api_key   = api_key
        self.token     = token
        self.board_id  = board_id
        self._in_prog  = _parse_list_names(lists_in_progress)
        self._done     = _parse_list_names(lists_done)
        self._auth_qs  = f"key={api_key}&token={token}"

    # ── Fetch ────────────────────────────────────────────────────────────────

    def fetch(self) -> list:
        # Fetch all cards (including archived) with member info
        cards = _with_retry(lambda: _http_get(
            f"{_BASE}/boards/{self.board_id}/cards"
            f"?filter=all&members=true&{self._auth_qs}",
            headers={},
        ))
        print(f"  [trello] {len(cards)} cards, fetching actions…")

        # Fetch list names to resolve idList → list name
        lists = _with_retry(lambda: _http_get(
            f"{_BASE}/boards/{self.board_id}/lists?{self._auth_qs}",
            headers={},
        ))
        list_names = {lst["id"]: lst["name"] for lst in lists}

        def _fetch_actions(card):
            actions = _with_retry(lambda: _http_get(
                f"{_BASE}/cards/{card['id']}/actions"
                f"?filter=updateCard:idList&limit={_MAX_ACTIONS}&{self._auth_qs}",
                headers={},
            ))
            if len(actions) >= _MAX_ACTIONS:
                print(f"  [trello] [warn] {card['id']}: actions at {_MAX_ACTIONS} limit — history may be truncated")
            card["_actions"]   = actions
            card["_listNames"] = list_names
            return card

        with ThreadPoolExecutor(max_workers=10) as pool:
            enriched = list(pool.map(_fetch_actions, cards))

        print(f"  [trello] fetched actions for {len(enriched)} cards")
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

    def _to_canonical(self, card: dict) -> dict:
        actions    = card.get("_actions", [])
        list_names = card.get("_listNames", {})

        current_list = list_names.get(card.get("idList", ""), "")
        # Archived cards that are in a "done" list count as done;
        # otherwise fall back to "done" if closed
        if card.get("closed") and not current_list:
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

        if not histories:
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
                "assignee":       {"displayName": assignee} if assignee else None,
            },
            "changelog": {"histories": histories},
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
