"""Extended ingestion tests — wip_items, predictability, adapter path, error handling.

Complements test_ingestion.py (which covers throughput/completedCount/interval logic).
Coverage targets:
  _compute_wip_items  — field extraction, sorting, cap, url, assignee variants
  _calc_predictability — committed/completed window logic
  run_ingestion_with_adapter — adapter path, empty result, snapshot saved
  run_ingestion           — fetch errors don't save snapshot
"""

import sys
import os
import unittest
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.ingestion import (
    _compute_wip_items,
    _calc_predictability,
    run_ingestion,
    run_ingestion_with_adapter,
)
from server.metrics import _map_issue
from server.storage import init_db, get_latest


def tmp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    init_db(f.name)
    return f.name


def make_issue(key="T-1", status="In Progress", created="2024-01-01T00:00:00Z",
               resolutiondate=None, transitions=None, assignee=None, summary=None):
    histories = []
    for t in (transitions or []):
        histories.append({
            "created": t["date"],
            "items": [{"field": "status", "fromString": t["from"], "toString": t["to"]}],
        })
    return {
        "key": key,
        "fields": {
            "status": {"name": status},
            "created": created,
            "resolutiondate": resolutiondate,
            "assignee": assignee,
            "summary": summary or f"Issue {key}",
        },
        "changelog": {"histories": histories},
    }


# A simple in-progress issue started 2024-01-03
IN_PROGRESS = make_issue(
    key="T-10", status="In Progress", created="2024-01-01T00:00:00Z",
    transitions=[{"date": "2024-01-03T00:00:00Z", "from": "To Do", "to": "In Progress"}],
)

# A completed issue (should not appear in WIP)
DONE_ISSUE = make_issue(
    key="T-20", status="Done", created="2024-01-01T00:00:00Z",
    resolutiondate="2024-01-05T12:00:00Z",
    transitions=[
        {"date": "2024-01-02T00:00:00Z", "from": "To Do",      "to": "In Progress"},
        {"date": "2024-01-05T12:00:00Z", "from": "In Progress", "to": "Done"},
    ],
)


# ── _compute_wip_items ─────────────────────────────────────────────────────────

class TestComputeWipItems(unittest.TestCase):

    def test_empty_inputs_return_empty(self):
        self.assertEqual(_compute_wip_items([], []), [])

    def test_resolved_issue_not_included(self):
        mapped = [_map_issue(DONE_ISSUE)]
        self.assertEqual(_compute_wip_items([DONE_ISSUE], mapped), [])

    def test_in_progress_issue_included(self):
        mapped = [_map_issue(IN_PROGRESS)]
        result = _compute_wip_items([IN_PROGRESS], mapped)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["key"], "T-10")

    def test_never_started_issue_not_included(self):
        issue = make_issue(key="T-1", status="To Do", created="2024-01-01T00:00:00Z")
        mapped = [_map_issue(issue)]
        self.assertEqual(_compute_wip_items([issue], mapped), [])

    def test_wip_item_has_all_required_fields(self):
        mapped = [_map_issue(IN_PROGRESS)]
        item = _compute_wip_items([IN_PROGRESS], mapped)[0]
        for field in ("key", "title", "assignee", "daysInProgress", "status", "url", "blockedReason"):
            self.assertIn(field, item, f"Missing field: {field}")

    def test_assignee_dict_displayname_extracted(self):
        issue = make_issue(
            key="T-1", status="In Progress",
            assignee={"displayName": "Alice Smith"},
            transitions=[{"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"}],
        )
        mapped = [_map_issue(issue)]
        result = _compute_wip_items([issue], mapped)
        self.assertEqual(result[0]["assignee"], "Alice Smith")

    def test_assignee_dict_name_fallback(self):
        issue = make_issue(
            key="T-1", status="In Progress",
            assignee={"name": "bob"},
            transitions=[{"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"}],
        )
        mapped = [_map_issue(issue)]
        result = _compute_wip_items([issue], mapped)
        self.assertEqual(result[0]["assignee"], "bob")

    def test_assignee_none_becomes_empty_string(self):
        mapped = [_map_issue(IN_PROGRESS)]
        result = _compute_wip_items([IN_PROGRESS], mapped)
        self.assertEqual(result[0]["assignee"], "")

    def test_assignee_string_used_directly(self):
        issue = make_issue(
            key="T-1", status="In Progress",
            assignee="Charlie",
            transitions=[{"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"}],
        )
        mapped = [_map_issue(issue)]
        result = _compute_wip_items([issue], mapped)
        self.assertEqual(result[0]["assignee"], "Charlie")

    def test_browse_url_taken_from_issue(self):
        issue = {**IN_PROGRESS, "browseUrl": "https://jira.example.com/browse/T-10"}
        mapped = [_map_issue(issue)]
        result = _compute_wip_items([issue], mapped)
        self.assertEqual(result[0]["url"], "https://jira.example.com/browse/T-10")

    def test_url_field_used_when_browse_url_absent(self):
        issue = {**IN_PROGRESS, "url": "https://trello.com/c/card-id"}
        mapped = [_map_issue(issue)]
        result = _compute_wip_items([issue], mapped)
        self.assertEqual(result[0]["url"], "https://trello.com/c/card-id")

    def test_url_is_none_when_neither_present(self):
        mapped = [_map_issue(IN_PROGRESS)]
        result = _compute_wip_items([IN_PROGRESS], mapped)
        self.assertIsNone(result[0]["url"])

    def test_blocked_reason_is_always_none(self):
        # blockedReason is set by Jira-specific logic; ingestion always stores None
        mapped = [_map_issue(IN_PROGRESS)]
        result = _compute_wip_items([IN_PROGRESS], mapped)
        self.assertIsNone(result[0]["blockedReason"])

    def test_sorted_by_days_in_progress_descending(self):
        old = make_issue(
            key="T-old", status="In Progress", created="2020-01-01T00:00:00Z",
            transitions=[{"date": "2020-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"}],
        )
        new = make_issue(
            key="T-new", status="In Progress", created="2024-01-01T00:00:00Z",
            transitions=[{"date": "2024-01-10T00:00:00Z", "from": "To Do", "to": "In Progress"}],
        )
        mapped = [_map_issue(old), _map_issue(new)]
        result = _compute_wip_items([old, new], mapped)
        self.assertGreater(result[0]["daysInProgress"], result[1]["daysInProgress"])

    def test_capped_at_20_items(self):
        issues, mapped = [], []
        for i in range(25):
            issue = make_issue(
                key=f"T-{i}", status="In Progress", created="2024-01-01T00:00:00Z",
                transitions=[{"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"}],
            )
            issues.append(issue)
            mapped.append(_map_issue(issue))
        result = _compute_wip_items(issues, mapped)
        self.assertLessEqual(len(result), 20)

    def test_days_in_progress_is_positive_number(self):
        mapped = [_map_issue(IN_PROGRESS)]
        result = _compute_wip_items([IN_PROGRESS], mapped)
        self.assertGreater(result[0]["daysInProgress"], 0)

    def test_issue_without_key_falls_back_to_id(self):
        issue = {
            "id": "issue-uuid-123",
            "fields": {"status": {"name": "in progress"}, "created": "2024-01-01T00:00:00Z",
                       "resolutiondate": None, "assignee": None, "summary": "No key"},
            "changelog": {"histories": [{
                "created": "2024-01-02T00:00:00Z",
                "items": [{"field": "status", "fromString": "backlog", "toString": "in progress"}],
            }]},
        }
        mapped = [_map_issue(issue)]
        result = _compute_wip_items([issue], mapped)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["key"], "issue-uuid-123")


# ── _calc_predictability ───────────────────────────────────────────────────────

class TestCalcPredictability(unittest.TestCase):

    def _m(self, started_days_ago, resolved_days_ago=None):
        """Helper: build a mapped issue dict with relative timestamps."""
        now = datetime.now(timezone.utc)
        started = (now - timedelta(days=started_days_ago)).isoformat()
        resolved = (now - timedelta(days=resolved_days_ago)).isoformat() if resolved_days_ago is not None else None
        return {"started_at": started, "resolved_at": resolved,
                "created_at": started, "reopened": False}

    def test_empty_input_returns_zero(self):
        self.assertEqual(_calc_predictability([]), 0)

    def test_all_committed_resolved_in_window(self):
        # started 20d ago, resolved 5d ago → inside 30d window
        result = _calc_predictability([self._m(20, 5)])
        self.assertEqual(result, 100.0)

    def test_committed_not_resolved_gives_zero(self):
        # started 10d ago, not resolved → committed but not completed
        result = _calc_predictability([self._m(10, None)])
        self.assertEqual(result, 0)

    def test_issue_resolved_before_window_excluded_from_committed(self):
        # started 60d ago, resolved 40d ago — resolved_before_period → not committed
        result = _calc_predictability([self._m(60, 40)])
        self.assertEqual(result, 0)

    def test_partial_completion_gives_correct_ratio(self):
        # 2 committed, 1 resolved in period → 50%
        result = _calc_predictability([self._m(10, 5), self._m(10, None)])
        self.assertEqual(result, 50.0)

    def test_no_started_at_is_skipped(self):
        m = {"started_at": None, "resolved_at": None, "created_at": None, "reopened": False}
        self.assertEqual(_calc_predictability([m]), 0)

    def test_returns_float_rounded_to_one_decimal(self):
        # 3 committed, 1 resolved → 33.3%
        result = _calc_predictability([
            self._m(10, 5), self._m(10, None), self._m(10, None),
        ])
        self.assertEqual(result, 33.3)


# ── run_ingestion — error handling ─────────────────────────────────────────────

class TestRunIngestionErrorHandling(unittest.TestCase):

    def setUp(self):
        self.db = tmp_db()

    def tearDown(self):
        os.unlink(self.db)

    def test_fetch_exception_propagates(self):
        with patch("server.ingestion.fetch_jira", side_effect=ConnectionError("timeout")):
            with self.assertRaises(ConnectionError):
                run_ingestion("PROJ", "https://j.test", "u", "t", "jql", self.db)

    def test_no_snapshot_saved_when_fetch_raises(self):
        with patch("server.ingestion.fetch_jira", side_effect=RuntimeError("boom")):
            try:
                run_ingestion("PROJ", "https://j.test", "u", "t", "jql", self.db)
            except RuntimeError:
                pass
        self.assertIsNone(get_latest("PROJ", self.db))

    def test_empty_result_raises_value_error(self):
        with patch("server.ingestion.fetch_jira", return_value=[]):
            with self.assertRaises(ValueError):
                run_ingestion("PROJ", "https://j.test", "u", "t", "jql", self.db)

    def test_no_snapshot_saved_on_empty_result(self):
        with patch("server.ingestion.fetch_jira", return_value=[]):
            try:
                run_ingestion("PROJ", "https://j.test", "u", "t", "jql", self.db)
            except ValueError:
                pass
        self.assertIsNone(get_latest("PROJ", self.db))


# ── run_ingestion_with_adapter ─────────────────────────────────────────────────

class TestRunIngestionWithAdapter(unittest.TestCase):

    def setUp(self):
        self.db = tmp_db()

    def tearDown(self):
        os.unlink(self.db)

    def _canonical_done_issue(self):
        return {
            "fields": {
                "created": "2024-01-01T00:00:00Z",
                "resolutiondate": "2024-01-05T00:00:00Z",
                "status": {"name": "done"},
                "summary": "Adapter issue",
                "assignee": None,
            },
            "changelog": {"histories": [
                {"created": "2024-01-02T00:00:00Z",
                 "items": [{"field": "status", "fromString": "backlog", "toString": "in progress"}]},
                {"created": "2024-01-05T00:00:00Z",
                 "items": [{"field": "status", "fromString": "in progress", "toString": "done"}]},
            ]},
        }

    def _mock_adapter(self, issues):
        adapter = MagicMock()
        adapter.fetch_and_normalize.return_value = issues
        return adapter

    def test_empty_adapter_result_raises_value_error(self):
        with patch("server.adapters.build_adapter", return_value=self._mock_adapter([])):
            with self.assertRaises(ValueError):
                run_ingestion_with_adapter("PROJ", "trello", {}, self.db)

    def test_no_snapshot_saved_on_empty_adapter_result(self):
        with patch("server.adapters.build_adapter", return_value=self._mock_adapter([])):
            try:
                run_ingestion_with_adapter("PROJ", "trello", {}, self.db)
            except ValueError:
                pass
        self.assertIsNone(get_latest("PROJ", self.db))

    def test_saves_snapshot_when_adapter_returns_issues(self):
        issues = [self._canonical_done_issue()]
        with patch("server.adapters.build_adapter", return_value=self._mock_adapter(issues)):
            run_ingestion_with_adapter("PROJ", "trello", {}, self.db)
        self.assertIsNotNone(get_latest("PROJ", self.db))

    def test_returns_metrics_with_required_keys(self):
        issues = [self._canonical_done_issue()]
        with patch("server.adapters.build_adapter", return_value=self._mock_adapter(issues)):
            metrics = run_ingestion_with_adapter("PROJ", "trello", {}, self.db)
        for key in ("completedCount", "wipItems", "throughput",
                    "cycleTimeP50", "flowEfficiencyPercent"):
            self.assertIn(key, metrics, f"Missing: {key}")

    def test_build_adapter_called_with_source_and_config(self):
        config = {"api_key": "k", "token": "t", "board_id": "b"}
        with patch("server.adapters.build_adapter",
                   return_value=self._mock_adapter([self._canonical_done_issue()])) as mock_ba:
            run_ingestion_with_adapter("PROJ", "trello", config, self.db)
        mock_ba.assert_called_once_with("trello", config)

    def test_adapter_exception_propagates(self):
        adapter = MagicMock()
        adapter.fetch_and_normalize.side_effect = ConnectionError("API down")
        with patch("server.adapters.build_adapter", return_value=adapter):
            with self.assertRaises(ConnectionError):
                run_ingestion_with_adapter("PROJ", "trello", {}, self.db)


if __name__ == "__main__":
    unittest.main(verbosity=2)
