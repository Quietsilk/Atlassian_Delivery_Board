"""Tests for server.adapters.trello — TrelloAdapter fetch + normalize."""

import sys
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.adapters.trello import TrelloAdapter, _created_from_id, _parse_list_names
from server.adapters.base import CANONICAL_STARTED, CANONICAL_DONE


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_adapter(lists_in_progress="In Progress", lists_done="Done"):
    return TrelloAdapter(
        api_key="key", token="tok", board_id="board1",
        lists_in_progress=lists_in_progress,
        lists_done=lists_done,
    )


def _make_card(card_id="507f1f77bcf86cd799439011", name="Fix bug",
               short_link="abc123", id_list="list1",
               closed=False, members=None, date_last="2024-01-10T00:00:00Z"):
    return {
        "id":               card_id,
        "name":             name,
        "shortLink":        short_link,
        "idList":           id_list,
        "closed":           closed,
        "members":          members or [],
        "dateLastActivity": date_last,
    }


def _make_action(date, list_before, list_after):
    return {
        "date": date,
        "data": {
            "listBefore": {"name": list_before},
            "listAfter":  {"name": list_after},
        },
    }


# ── _created_from_id ──────────────────────────────────────────────────────────

class TestCreatedFromId(unittest.TestCase):

    def test_known_id_decodes_correctly(self):
        # 507f1f77... → first 8 hex = 0x507f1f77 = 1350474615 unix
        dt = datetime.fromtimestamp(0x507f1f77, tz=timezone.utc)
        result = _created_from_id("507f1f77bcf86cd799439011")
        self.assertEqual(result, dt.isoformat())

    def test_returns_iso_string(self):
        result = _created_from_id("507f1f77bcf86cd799439011")
        self.assertIsInstance(result, str)
        self.assertIn("T", result)


# ── _parse_list_names ─────────────────────────────────────────────────────────

class TestParseListNames(unittest.TestCase):

    def test_splits_by_comma(self):
        self.assertEqual(_parse_list_names("In Progress,Doing"), {"in progress", "doing"})

    def test_strips_whitespace(self):
        self.assertEqual(_parse_list_names("  Done , Released  "), {"done", "released"})

    def test_empty_string_returns_empty_set(self):
        self.assertEqual(_parse_list_names(""), set())

    def test_single_value(self):
        self.assertEqual(_parse_list_names("Done"), {"done"})


# ── TrelloAdapter.normalize ───────────────────────────────────────────────────

class TestTrelloAdapterNormalize(unittest.TestCase):

    def setUp(self):
        self.adapter = _make_adapter()

    def _card_with_actions(self, card=None, actions=None, list_names=None):
        c = card or _make_card()
        c["_actions"]   = actions or []
        c["_listNames"] = list_names or {"list1": "In Progress"}
        return c

    def test_canonical_status_in_progress(self):
        card = self._card_with_actions(list_names={"list1": "In Progress"})
        result = self.adapter._to_canonical(card)
        self.assertEqual(result["fields"]["status"]["name"], CANONICAL_STARTED)

    def test_canonical_status_done(self):
        card = self._card_with_actions(
            card=_make_card(id_list="list2"),
            list_names={"list2": "Done"},
        )
        result = self.adapter._to_canonical(card)
        self.assertEqual(result["fields"]["status"]["name"], CANONICAL_DONE)

    def test_canonical_status_unknown_list_passthrough(self):
        card = self._card_with_actions(
            card=_make_card(id_list="list3"),
            list_names={"list3": "Review"},
        )
        result = self.adapter._to_canonical(card)
        self.assertEqual(result["fields"]["status"]["name"], "Review")

    def test_resolution_date_set_for_done_card(self):
        action = _make_action("2024-01-05T00:00:00Z", "In Progress", "Done")
        card = self._card_with_actions(
            card=_make_card(id_list="list2"),
            actions=[action],
            list_names={"list2": "Done"},
        )
        result = self.adapter._to_canonical(card)
        self.assertIsNotNone(result["fields"]["resolutiondate"])

    def test_resolution_date_none_for_in_progress_card(self):
        card = self._card_with_actions()
        result = self.adapter._to_canonical(card)
        self.assertIsNone(result["fields"]["resolutiondate"])

    def test_changelog_built_from_actions(self):
        # Trello API returns actions newest-first; adapter reverses to oldest-first
        actions = [
            _make_action("2024-01-05T00:00:00Z", "In Progress", "Done"),
            _make_action("2024-01-02T00:00:00Z", "To Do", "In Progress"),
        ]
        card = self._card_with_actions(
            card=_make_card(id_list="list2"),
            actions=actions,
            list_names={"list2": "Done"},
        )
        result = self.adapter._to_canonical(card)
        histories = result["changelog"]["histories"]
        self.assertEqual(len(histories), 2)
        # oldest-first after reversal
        self.assertEqual(histories[0]["items"][0]["toString"], CANONICAL_STARTED)
        self.assertEqual(histories[1]["items"][0]["toString"], CANONICAL_DONE)

    def test_action_without_list_before_skipped(self):
        # Incomplete action (no listBefore) is ignored; backlog card → no synthesize either
        action = {"date": "2024-01-02T00:00:00Z", "data": {"listAfter": {"name": "In Progress"}}}
        card = self._card_with_actions(
            card=_make_card(id_list="list3"),
            actions=[action],
            list_names={"list3": "Backlog"},  # not in_progress / done → no synthesize
        )
        result = self.adapter._to_canonical(card)
        self.assertEqual(result["changelog"]["histories"], [])

    def test_assignee_extracted_from_members(self):
        card = self._card_with_actions(
            card=_make_card(members=[{"fullName": "Alice"}]),
        )
        result = self.adapter._to_canonical(card)
        self.assertEqual(result["fields"]["assignee"]["displayName"], "Alice")

    def test_no_members_gives_none_assignee(self):
        card = self._card_with_actions()
        result = self.adapter._to_canonical(card)
        self.assertIsNone(result["fields"]["assignee"])

    def test_url_uses_short_link(self):
        card = self._card_with_actions(card=_make_card(short_link="xyz789"))
        result = self.adapter._to_canonical(card)
        self.assertEqual(result["url"], "https://trello.com/c/xyz789")

    def test_key_uses_short_link(self):
        card = self._card_with_actions(card=_make_card(short_link="xyz789"))
        result = self.adapter._to_canonical(card)
        self.assertEqual(result["key"], "xyz789")

    def test_created_extracted_from_id(self):
        card = self._card_with_actions(card=_make_card(card_id="507f1f77bcf86cd799439011"))
        result = self.adapter._to_canonical(card)
        expected = _created_from_id("507f1f77bcf86cd799439011")
        self.assertEqual(result["fields"]["created"], expected)

    def test_synthesise_lifecycle_for_in_progress_no_actions(self):
        card = self._card_with_actions()  # In Progress, no actions
        result = self.adapter._to_canonical(card)
        histories = result["changelog"]["histories"]
        self.assertEqual(len(histories), 1)
        self.assertEqual(histories[0]["items"][0]["toString"], CANONICAL_STARTED)

    def test_synthesise_lifecycle_for_done_no_actions(self):
        card = self._card_with_actions(
            card=_make_card(id_list="list2"),
            list_names={"list2": "Done"},
        )
        result = self.adapter._to_canonical(card)
        histories = result["changelog"]["histories"]
        self.assertEqual(len(histories), 2)
        self.assertEqual(histories[-1]["items"][0]["toString"], CANONICAL_DONE)

    def test_closed_card_without_list_name_treated_as_done(self):
        card = _make_card(closed=True, id_list="list_unknown")
        card["_actions"]   = []
        card["_listNames"] = {}  # list not found
        result = self.adapter._to_canonical(card)
        self.assertEqual(result["fields"]["status"]["name"], CANONICAL_DONE)

    def test_normalize_returns_list(self):
        card = self._card_with_actions()
        result = self.adapter.normalize([card])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)


# ── TrelloAdapter.fetch (mocked HTTP) ────────────────────────────────────────

class TestTrelloAdapterFetch(unittest.TestCase):

    def setUp(self):
        self.adapter = _make_adapter()

    def _mock_http(self, cards, lists, actions_per_card=None):
        actions_per_card = actions_per_card or {}

        def fake_http_get(url, headers):
            if "/cards" in url and "/actions" not in url:
                return cards
            if "/lists" in url:
                return lists
            # actions for a card
            for card_id, actions in actions_per_card.items():
                if card_id in url:
                    return actions
            return []

        return fake_http_get

    def test_fetch_returns_enriched_cards(self):
        cards = [_make_card()]
        lists = [{"id": "list1", "name": "In Progress"}]

        with patch("server.adapters.trello._http_get",
                   side_effect=self._mock_http(cards, lists, {"507f1f77bcf86cd799439011": []})):
            result = self.adapter.fetch()

        self.assertEqual(len(result), 1)
        self.assertIn("_actions", result[0])
        self.assertIn("_listNames", result[0])

    def test_list_names_attached_to_cards(self):
        cards = [_make_card()]
        lists = [{"id": "list1", "name": "In Progress"}]

        with patch("server.adapters.trello._http_get",
                   side_effect=self._mock_http(cards, lists)):
            result = self.adapter.fetch()

        self.assertEqual(result[0]["_listNames"]["list1"], "In Progress")

    def test_actions_attached_to_cards(self):
        actions = [_make_action("2024-01-02T00:00:00Z", "To Do", "In Progress")]
        cards = [_make_card()]
        lists = [{"id": "list1", "name": "In Progress"}]

        with patch("server.adapters.trello._http_get",
                   side_effect=self._mock_http(cards, lists, {"507f1f77bcf86cd799439011": actions})):
            result = self.adapter.fetch()

        self.assertEqual(result[0]["_actions"], actions)

    def test_warns_when_actions_at_limit(self):
        actions = [_make_action("2024-01-01T00:00:00Z", "To Do", "In Progress")] * 1000
        cards = [_make_card()]
        lists = [{"id": "list1", "name": "In Progress"}]

        with patch("server.adapters.trello._http_get",
                   side_effect=self._mock_http(cards, lists, {"507f1f77bcf86cd799439011": actions})):
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.adapter.fetch()
        self.assertIn("warn", buf.getvalue())

    def test_empty_board_returns_empty_list(self):
        with patch("server.adapters.trello._http_get",
                   side_effect=self._mock_http([], [])):
            result = self.adapter.fetch()
        self.assertEqual(result, [])


# ── build_adapter integration ─────────────────────────────────────────────────

class TestBuildAdapterTrello(unittest.TestCase):

    def test_build_adapter_returns_trello_instance(self):
        from server.adapters.base import build_adapter
        adapter = build_adapter("trello", {
            "api_key": "k", "token": "t", "board_id": "b",
            "lists_in_progress": "In Progress",
            "lists_done": "Done",
        })
        self.assertIsInstance(adapter, TrelloAdapter)

    def test_build_adapter_trello_source_attribute(self):
        from server.adapters.base import build_adapter
        adapter = build_adapter("trello", {
            "api_key": "k", "token": "t", "board_id": "b",
        })
        self.assertEqual(adapter.source, "trello")


if __name__ == "__main__":
    unittest.main(verbosity=2)
