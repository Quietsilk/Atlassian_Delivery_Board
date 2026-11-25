"""Tests for server.ingestion — pipeline and interval-based throughput logic."""

import sys
import os
import sqlite3
import unittest
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.ingestion import (
    run_ingestion,
    fetch_jira,
    _get_completed_in_interval,
    _select_flow_sample,
    _compute_wip_items,
    _sprint_completion_from_report,
)
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


def make_done_issue_with_offsets(key, now, resolved_days_ago, cycle_days=1, lead_days=2):
    resolved = now - timedelta(days=resolved_days_ago)
    started = resolved - timedelta(days=cycle_days)
    created = resolved - timedelta(days=lead_days)
    return make_issue(
        key=key,
        status="Done",
        created=created.isoformat().replace("+00:00", "Z"),
        resolutiondate=resolved.isoformat().replace("+00:00", "Z"),
        transitions=[
            {
                "date": started.isoformat().replace("+00:00", "Z"),
                "from": "To Do",
                "to": "In Progress",
            },
            {
                "date": resolved.isoformat().replace("+00:00", "Z"),
                "from": "In Progress",
                "to": "Done",
            },
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

    @contextmanager
    def _mock_fetch(self, issues):
        sprint_metrics = {
            "sprintCompletionPercent": 75.0,
            "sprintCommittedCount": 4,
            "sprintCompletedCount": 3,
            "sprintAddedCount": 1,
            "sprintRemovedCount": 0,
            "sprintCompletionBasis": "final_scope",
            "sprintName": "Sprint 1",
            "sprintStartDate": "2024-01-01T00:00:00Z",
            "sprintCompleteDate": "2024-01-14T00:00:00Z",
        }
        with patch("server.ingestion.fetch_jira", return_value=issues), \
             patch("server.ingestion._fetch_jira_sprint_completion", return_value=sprint_metrics):
            yield

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
            "flowSampleSize", "flowSampleWindowDays", "flowSampleMode",
            "throughput", "completedCount",
            "backlogSize", "inProgressCount",
            "sprintCompletionPercent", "sprintCommittedCount", "sprintCompletedCount",
            "predictabilityPercent", "backlogAgingDays",
        )
        for key in required:
            self.assertIn(key, m, f"Missing key: {key}")

    def test_wip_ratio_not_in_metrics(self):
        """wipRatio is deprecated and must not be saved (Step 8)."""
        with self._mock_fetch([DONE_ISSUE]):
            m = run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)
        self.assertNotIn("wipRatio", m)

    def test_flow_metrics_do_not_use_interval_completions(self):
        """Flow sample is independent from interval throughput."""
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
        self.assertEqual(m["flowSampleMode"], "all_completed")
        self.assertEqual(m["flowSampleSize"], 1)
        self.assertGreater(m["cycleTimeP50"], 0)
        # completedCount is cumulative total — 1 completed issue regardless of interval
        self.assertEqual(m["completedCount"], 1)

    def test_first_snapshot_throughput_zero_but_flow_uses_completed_sample(self):
        now = datetime.now(timezone.utc)
        issues = [make_done_issue_with_offsets(f"PROJ-{i}", now, i + 1) for i in range(3)]

        with self._mock_fetch(issues):
            m = run_ingestion("PROJ", "https://j.test", "u", "t", "project=X", self.db)

        self.assertEqual(m["throughput"], 0)
        self.assertEqual(m["flowSampleMode"], "all_completed")
        self.assertEqual(m["flowSampleSize"], 3)
        self.assertGreater(m["cycleTimeP50"], 0)

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


class TestSelectFlowSample(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 5, 22, tzinfo=timezone.utc)

    def _mapped(self, count, offset_start=1):
        issues = [
            make_done_issue_with_offsets(f"PROJ-{i}", self.now, offset_start + i)
            for i in range(count)
        ]
        return [_map_issue(issue) for issue in issues]

    def test_uses_rolling_30d_when_window_has_minimum_sample(self):
        sample, meta = _select_flow_sample(self._mapped(10), now=self.now)

        self.assertEqual(len(sample), 10)
        self.assertEqual(meta["flowSampleMode"], "rolling_30d")
        self.assertEqual(meta["flowSampleSize"], 10)
        self.assertEqual(meta["flowSampleWindowDays"], 30)

    def test_falls_back_to_last_10_when_rolling_window_is_small(self):
        recent = self._mapped(3)
        old = self._mapped(9, offset_start=40)
        sample, meta = _select_flow_sample(recent + old, now=self.now)

        self.assertEqual(len(sample), 10)
        self.assertEqual(meta["flowSampleMode"], "last_10")
        self.assertEqual(meta["flowSampleWindowDays"], 30)

    def test_uses_all_completed_when_total_is_below_minimum_sample(self):
        sample, meta = _select_flow_sample(self._mapped(6), now=self.now)

        self.assertEqual(len(sample), 6)
        self.assertEqual(meta["flowSampleMode"], "all_completed")
        self.assertEqual(meta["flowSampleWindowDays"], 30)

    def test_empty_when_no_completed_items(self):
        issue = make_issue(
            key="PROJ-1",
            status="In Progress",
            created="2026-05-01T00:00:00Z",
            transitions=[
                {"date": "2026-05-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
            ],
        )

        sample, meta = _select_flow_sample([_map_issue(issue)], now=self.now)

        self.assertEqual(sample, [])
        self.assertEqual(meta["flowSampleMode"], "empty")
        self.assertEqual(meta["flowSampleSize"], 0)
        self.assertEqual(meta["flowSampleWindowDays"], 30)


class TestFetchJiraChangelogCompleteness(unittest.TestCase):
    def _search_page(self):
        return {
            "issues": [
                {
                    "key": "PROJ-1",
                    "fields": {
                        "summary": "First",
                        "status": {"name": "Done"},
                        "created": "2024-01-01T00:00:00Z",
                        "resolutiondate": "2024-01-02T00:00:00Z",
                        "assignee": None,
                        "project": {"key": "PROJ"},
                        "labels": [],
                    },
                },
                {
                    "key": "PROJ-2",
                    "fields": {
                        "summary": "Second",
                        "status": {"name": "In Progress"},
                        "created": "2024-01-01T00:00:00Z",
                        "resolutiondate": None,
                        "assignee": None,
                        "project": {"key": "PROJ"},
                        "labels": [],
                    },
                },
            ],
            "isLast": True,
        }

    def test_fetch_jira_raises_when_any_changelog_fetch_fails(self):
        def fake_jira_request(url, auth, body=None):
            if url.endswith("/rest/api/3/search/jql"):
                return self._search_page()
            if url.endswith("/issue/PROJ-1/changelog?maxResults=100"):
                return {"values": []}
            if url.endswith("/issue/PROJ-2/changelog?maxResults=100"):
                raise TimeoutError("timeout")
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("server.ingestion._jira_request", side_effect=fake_jira_request):
            with self.assertRaisesRegex(RuntimeError, "snapshot was not saved"):
                fetch_jira("https://j.test", "u", "t", "project=PROJ")

    def test_fetch_jira_attaches_changelogs_when_all_fetches_succeed(self):
        search_bodies = []

        def fake_jira_request(url, auth, body=None):
            if url.endswith("/rest/api/3/search/jql"):
                search_bodies.append(body)
                return self._search_page()
            if url.endswith("/issue/PROJ-1/changelog?maxResults=100"):
                return {"values": [{"created": "2024-01-02T00:00:00Z", "items": []}]}
            if url.endswith("/issue/PROJ-2/changelog?maxResults=100"):
                return {"values": []}
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("server.ingestion._jira_request", side_effect=fake_jira_request):
            issues = fetch_jira("https://j.test", "u", "t", "project=PROJ")

        self.assertEqual(len(issues), 2)
        self.assertEqual(len(issues[0]["changelog"]["histories"]), 1)
        self.assertEqual(issues[0]["browseUrl"], "https://j.test/browse/PROJ-1")
        self.assertIn("issuetype", search_bodies[0]["fields"])
        self.assertIn("labels", search_bodies[0]["fields"])

    def test_fetch_jira_fails_closed_at_changelog_limit(self):
        def fake_jira_request(url, auth, body=None):
            if url.endswith("/rest/api/3/search/jql"):
                return self._search_page()
            if "/changelog?maxResults=100" in url:
                return {"values": [{"created": "2024-01-02T00:00:00Z"}] * 100}
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("server.ingestion._jira_request", side_effect=fake_jira_request):
            with self.assertRaisesRegex(RuntimeError, "snapshot was not saved"):
                fetch_jira("https://j.test", "u", "t", "project=PROJ")

    def test_fetch_jira_fails_closed_when_issue_limit_exceeded(self):
        with patch.dict(os.environ, {"ADA_MAX_JIRA_ISSUES": "1"}), \
             patch("server.ingestion._jira_request", return_value=self._search_page()):
            with self.assertRaisesRegex(RuntimeError, "issue limit"):
                fetch_jira("https://j.test", "u", "t", "project=PROJ")

    def test_fetch_jira_fails_closed_on_ambiguous_pagination(self):
        page = self._search_page()
        page["isLast"] = False
        page.pop("nextPageToken", None)

        with patch("server.ingestion._jira_request", return_value=page):
            with self.assertRaisesRegex(RuntimeError, "ambiguously"):
                fetch_jira("https://j.test", "u", "t", "project=PROJ")


class TestSprintCompletionFromReport(unittest.TestCase):
    def test_counts_completed_from_final_scope(self):
        report = {"contents": {
            "completedIssues": [{"key": "PROJ-1"}, {"key": "PROJ-2"}, {"key": "PROJ-3"}],
            "issuesNotCompletedInCurrentSprint": [{"key": "PROJ-4"}],
            "puntedIssues": [{"key": "PROJ-5"}],
            "issueKeysAddedDuringSprint": {"PROJ-3": True},
        }}

        result = _sprint_completion_from_report(report)

        self.assertEqual(result["sprintCommittedCount"], 4)
        self.assertEqual(result["sprintCompletedCount"], 3)
        self.assertEqual(result["sprintAddedCount"], 1)
        self.assertEqual(result["sprintRemovedCount"], 1)
        self.assertEqual(result["sprintCompletionBasis"], "final_scope")
        self.assertEqual(result["sprintCompletionPercent"], 75.0)

    def test_added_completed_items_count_in_final_scope(self):
        result = _sprint_completion_from_report({"contents": {
            "completedIssues": [{"key": "PROJ-1"}],
            "issuesNotCompletedInCurrentSprint": [{"key": "PROJ-2"}, {"key": "PROJ-3"}],
            "issueKeysAddedDuringSprint": {"PROJ-1": True, "PROJ-2": True, "PROJ-3": True},
        }})

        self.assertEqual(result["sprintCompletionPercent"], 33.3)
        self.assertEqual(result["sprintCommittedCount"], 3)
        self.assertEqual(result["sprintCompletionBasis"], "final_scope")


if __name__ == "__main__":
    unittest.main(verbosity=2)
