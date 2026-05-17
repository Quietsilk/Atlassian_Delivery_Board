"""Tests for server.ingestion — pipeline and interval-based throughput logic."""

import sys
import os
import sqlite3
import unittest
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.ingestion import run_ingestion, _get_completed_in_interval, _compute_wip_items
from server.metrics import _map_issue
from server.storage import init_db, get_latest


def tmp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    init_db(f.name)
    return f.name


def make_issue(key="T-1", status="Done", created="2024-01-01T00:00:00Z",
               resolutiondate=None, transitions=None):
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
        },
        "changelog": {"histories": histories},
    }


DONE_ISSUE = make_issue(
    status="Done",
    created="2024-01-01T00:00:00Z",
    resolutiondate="2024-01-05T12:00:00Z",
    transitions=[
        {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
        {"date": "2024-01-05T12:00:00Z", "from": "In Progress", "to": "Done"},
    ],
)


# ── _get_completed_in_interval (replaces _count_resolved_since) ────────────

class TestGetCompletedInInterval(unittest.TestCase):
    def setUp(self):
        self.mapped = [_map_issue(DONE_ISSUE)]  # resolved 2024-01-05T12:00:00Z

    def test_no_since_returns_empty(self):
        result = _get_completed_in_interval(self.mapped, None)
        self.assertEqual(result, [])

    def test_resolved_after_cutoff_is_included(self):
        result = _get_completed_in_interval(self.mapped, "2024-01-04T00:00:00+00:00")
        self.assertEqual(len(result), 1)

    def test_resolved_before_cutoff_excluded(self):
        result = _get_completed_in_interval(self.mapped, "2024-01-10T00:00:00+00:00")
        self.assertEqual(result, [])

    def test_no_resolutiondate_uses_changelog(self):
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate=None,
            transitions=[
                {"date": "2024-01-06T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        mapped = [_map_issue(issue)]
        result = _get_completed_in_interval(mapped, "2024-01-05T00:00:00+00:00")
        self.assertEqual(len(result), 1)

    def test_returns_mapped_dicts_not_issues(self):
        result = _get_completed_in_interval(self.mapped, "2024-01-04T00:00:00+00:00")
        self.assertIn("resolved_at", result[0])
        self.assertIn("started_at", result[0])


# ── run_ingestion ──────────────────────────────────────────────────────────

class TestRunIngestion(unittest.TestCase):
    def setUp(self):
        self.db = tmp_db()

    def tearDown(self):
        os.unlink(self.db)

    def _mock_fetch(self, issues):
        return patch("server.ingestion.fetch_jira", return_value=issues)

    def test_first_snapshot_throughput_zero(self):
        """No previous snapshot → no interval → throughput = 0."""
        with self._mock_fetch([DONE_ISSUE]):
            m = run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        self.assertEqual(m["throughput"], 0)

    def test_completed_count_is_cumulative(self):
        """completedCount = total completed issues, independent of sync interval."""
        with self._mock_fetch([DONE_ISSUE]):
            m = run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        # DONE_ISSUE is completed → completedCount = 1 regardless of interval
        self.assertEqual(m["completedCount"], 1)

    def test_throughput_per_day_not_in_snapshot(self):
        """throughputPerDay is computed by the frontend from snapshot deltas, not stored."""
        with self._mock_fetch([DONE_ISSUE]):
            m = run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        self.assertNotIn("throughputPerDay", m)

    def test_snapshot_is_saved(self):
        with self._mock_fetch([DONE_ISSUE]):
            run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        result = get_latest("PROJ", self.db)
        self.assertIsNotNone(result)

    def test_empty_jira_result_does_not_save_snapshot(self):
        with self._mock_fetch([]):
            with self.assertRaises(ValueError):
                run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        self.assertIsNone(get_latest("PROJ", self.db))

    def test_metrics_contain_required_keys(self):
        with self._mock_fetch([DONE_ISSUE]):
            m = run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        required = (
            "cycleTimeP50", "cycleTimeP85",
            "timeToMarketP50", "timeToMarketP85",
            "flowEfficiencyPercent",
            "throughput", "completedCount",
            "backlogSize", "inProgressCount", "reopenedCount",
            "predictabilityPercent", "backlogAgingDays",
        )
        for key in required:
            self.assertIn(key, m, f"Missing key: {key}")

    def test_wip_ratio_not_in_metrics(self):
        """wipRatio is deprecated and must not be saved (Step 8)."""
        with self._mock_fetch([DONE_ISSUE]):
            m = run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        self.assertNotIn("wipRatio", m)

    def test_flow_metrics_use_interval_not_all_time(self):
        """On first sync (no prev), falls back to all completed; on second sync uses interval."""
        con = sqlite3.connect(self.db)
        con.execute(
            "INSERT INTO snapshots (project_key, timestamp, metrics_json) VALUES (?, ?, ?)",
            ("PROJ", "2024-01-10T00:00:00+00:00", '{"throughput": 0}'),
        )
        con.commit()
        con.close()

        # DONE_ISSUE resolved 2024-01-05, which is BEFORE prev snapshot 2024-01-10
        with self._mock_fetch([DONE_ISSUE]):
            m = run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        # No issue resolved in interval → throughput 0
        self.assertEqual(m["throughput"], 0)
        # completedCount is cumulative total — 1 completed issue regardless of interval
        self.assertEqual(m["completedCount"], 1)

    def test_wip_items_include_issue_url(self):
        issue = make_issue(
            key="PROJ-7",
            status="In Progress",
            created="2024-01-01T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
            ],
        )
        issue["browseUrl"] = "https://jira.example.com/browse/PROJ-7"
        mapped = [_map_issue(issue)]

        result = _compute_wip_items([issue], mapped)

        self.assertEqual(result[0]["url"], "https://jira.example.com/browse/PROJ-7")


if __name__ == "__main__":
    unittest.main(verbosity=2)
