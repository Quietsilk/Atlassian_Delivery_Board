"""Tests for server.metrics — pure metric calculations, no period dependency."""

import sys
import os
import unittest
from datetime import timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server.metrics import (
    calculate_metrics, calculate_flow_metrics, _map_issue, _percentile,
    _parse_dt, STARTED, DONE,
)


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


# ── Structural metrics (calculate_metrics) ─────────────────────────────────

class TestMetricsEmpty(unittest.TestCase):
    def test_empty_returns_zeros(self):
        m = calculate_metrics([])
        self.assertEqual(m["backlogSize"], 0)
        self.assertEqual(m["inProgressCount"], 0)
        self.assertNotIn("reopenedCount", m)
        self.assertEqual(m["backlogAgingDays"], 0)

    def test_no_period_in_signature(self):
        import inspect
        sig = inspect.signature(calculate_metrics)
        self.assertNotIn("cutoff", sig.parameters)
        self.assertNotIn("period", sig.parameters)

    def test_no_flow_metrics_in_calculate_metrics(self):
        """calculate_metrics no longer returns flow metrics — those are in calculate_flow_metrics."""
        m = calculate_metrics([])
        self.assertNotIn("cycleTimeDays", m)
        self.assertNotIn("timeToMarketDays", m)
        self.assertNotIn("flowEfficiencyPercent", m)


class TestMetricsBasic(unittest.TestCase):
    def test_single_completed_counts_structural_metrics(self):
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-05T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([issue])
        self.assertEqual(m["backlogSize"], 0)
        self.assertEqual(m["inProgressCount"], 0)

    def test_wip_count(self):
        issue = make_issue(
            status="In Progress",
            created="2024-01-01T00:00:00Z",
            transitions=[{"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"}],
        )
        m = calculate_metrics([issue])
        self.assertEqual(m["inProgressCount"], 1)

    def test_backlog_count(self):
        issue = make_issue(status="To Do", created="2024-01-01T00:00:00Z")
        m = calculate_metrics([issue])
        self.assertEqual(m["backlogSize"], 1)

    def test_reopened_count_not_returned_for_wip(self):
        wip = make_issue(
            status="In Progress",
            created="2024-01-01T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-03T00:00:00Z", "from": "In Progress", "to": "Done"},
                {"date": "2024-01-04T00:00:00Z", "from": "Done",        "to": "In Progress"},
            ],
        )
        m = calculate_metrics([wip])
        self.assertNotIn("reopenedCount", m)

    def test_reopened_count_not_returned_for_completed(self):
        done = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-06T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-03T00:00:00Z", "from": "In Progress", "to": "Done"},
                {"date": "2024-01-04T00:00:00Z", "from": "Done",        "to": "In Progress"},
                {"date": "2024-01-06T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([done])
        self.assertNotIn("reopenedCount", m)

    def test_accepts_precomputed_mapped(self):
        """calculate_metrics accepts pre-computed mapped list (Step 1 optimization)."""
        issue = make_issue(status="To Do", created="2024-01-01T00:00:00Z")
        mapped = [_map_issue(issue)]
        m = calculate_metrics([issue], mapped=mapped)
        self.assertEqual(m["backlogSize"], 1)


# ── Flow metrics (calculate_flow_metrics) ──────────────────────────────────

def make_mapped(started, resolved, created="2024-01-01T00:00:00Z", reopened=False):
    return {
        "started_at":  started,
        "resolved_at": resolved,
        "created_at":  created,
        "reopened":    reopened,
    }


class TestFlowMetrics(unittest.TestCase):
    def test_single_issue_cycle_time(self):
        items = [make_mapped("2024-01-02T00:00:00Z", "2024-01-05T00:00:00Z",
                             created="2024-01-01T00:00:00Z")]
        r = calculate_flow_metrics(items)
        self.assertEqual(r["cycleTimeP50"], 3.0)   # Jan 2 → Jan 5
        self.assertEqual(r["timeToMarketP50"], 4.0) # Jan 1 → Jan 5

    def test_flow_efficiency_50_percent(self):
        # cycle 3d, TTM 6d → 50%
        items = [make_mapped("2024-01-04T00:00:00Z", "2024-01-07T00:00:00Z",
                             created="2024-01-01T00:00:00Z")]
        r = calculate_flow_metrics(items)
        self.assertEqual(r["flowEfficiencyPercent"], 50.0)

    def test_flow_efficiency_capped_at_100(self):
        # anomalous: created after started → cycle > lead
        items = [make_mapped("2024-01-03T00:00:00Z", "2024-01-07T00:00:00Z",
                             created="2024-01-05T00:00:00Z")]
        r = calculate_flow_metrics(items)
        self.assertLessEqual(r["flowEfficiencyPercent"], 100.0)

    def test_empty_returns_zeros(self):
        r = calculate_flow_metrics([])
        self.assertEqual(r["cycleTimeP50"], 0)
        self.assertEqual(r["cycleTimeP85"], 0)
        self.assertEqual(r["timeToMarketP50"], 0)
        self.assertEqual(r["timeToMarketP85"], 0)
        self.assertEqual(r["flowEfficiencyPercent"], 0)

    def test_p85_gte_p50(self):
        items = [
            make_mapped(f"2024-01-0{i}T00:00:00Z", f"2024-01-{10+i}T00:00:00Z",
                        created="2024-01-01T00:00:00Z")
            for i in range(1, 6)
        ]
        r = calculate_flow_metrics(items)
        self.assertGreaterEqual(r["cycleTimeP85"], r["cycleTimeP50"])

    def test_cycle_time_from_last_started(self):
        """_map_issue uses last STARTED before DONE."""
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-10T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-04T00:00:00Z", "from": "In Progress", "to": "To Do"},
                {"date": "2024-01-06T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-10T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        mapped = [_map_issue(issue)]
        completed = [m for m in mapped if m["resolved_at"]]
        r = calculate_flow_metrics(completed)
        self.assertEqual(r["cycleTimeP50"], 4.0)  # Jan 6 → Jan 10

    def test_done_without_resolutiondate(self):
        issue = make_issue(
            status="Done",
            created="2024-01-01T00:00:00Z",
            resolutiondate=None,
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        mapped = [_map_issue(issue)]
        completed = [m for m in mapped if m["resolved_at"]]
        r = calculate_flow_metrics(completed)
        self.assertEqual(r["cycleTimeP50"], 3.0)  # Jan 2 → Jan 5 via changelog


# ── Percentile helper ──────────────────────────────────────────────────────

class TestPercentile(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_percentile([], 50), 0)

    def test_single(self):
        self.assertEqual(_percentile([5.0], 50), 5.0)
        self.assertEqual(_percentile([5.0], 85), 5.0)

    def test_median_even(self):
        # [1, 2, 3, 4] → P50 = 2.5
        self.assertEqual(_percentile([1, 2, 3, 4], 50), 2.5)

    def test_p85(self):
        vals = list(range(1, 11))  # [1..10]
        p85 = _percentile(vals, 85)
        self.assertGreater(p85, _percentile(vals, 50))


# ── _parse_dt ──────────────────────────────────────────────────────────────

class TestParseDt(unittest.TestCase):
    def test_z_suffix(self):
        dt = _parse_dt("2024-03-15T10:00:00Z")
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_plus_offset(self):
        dt = _parse_dt("2024-03-15T10:00:00+00:00")
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_hhmm_without_colon(self):
        dt = _parse_dt("2024-03-15T12:00:00+0400")
        self.assertEqual(dt.hour, 12)


# ── completedCount ─────────────────────────────────────────────────────────

class TestCompletedCount(unittest.TestCase):
    """calculate_metrics must return completedCount = ALL resolved issues (cumulative)."""

    def test_completedcount_zero_for_empty(self):
        m = calculate_metrics([])
        self.assertEqual(m["completedCount"], 0)

    def test_completedcount_one_done_issue(self):
        issue = make_issue(
            status="Done", created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-05T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([issue])
        self.assertEqual(m["completedCount"], 1)

    def test_completedcount_done_without_resolutiondate(self):
        issue = make_issue(
            status="Done", created="2024-01-01T00:00:00Z",
            resolutiondate=None,
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([issue])
        self.assertEqual(m["completedCount"], 1)

    def test_completedcount_excludes_wip_and_backlog(self):
        done = make_issue(
            key="T-1", status="Done", created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-05T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        wip = make_issue(key="T-2", status="In Progress", created="2024-01-01T00:00:00Z",
                         transitions=[{"date": "2024-01-03T00:00:00Z", "from": "To Do", "to": "In Progress"}])
        backlog = make_issue(key="T-3", status="To Do", created="2024-01-01T00:00:00Z")
        m = calculate_metrics([done, wip, backlog])
        self.assertEqual(m["completedCount"], 1)
        self.assertEqual(m["inProgressCount"], 1)
        self.assertEqual(m["backlogSize"], 1)

    def test_completedcount_multiple_done_statuses(self):
        """Closed and Resolved are Done-like and must be counted."""
        issues = []
        for i, status in enumerate(["Done", "Closed", "Resolved"]):
            issues.append(make_issue(
                key=f"T-{i}", status=status, created="2024-01-01T00:00:00Z",
                resolutiondate="2024-01-05T00:00:00Z",
                transitions=[
                    {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                    {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": status},
                ],
            ))
        m = calculate_metrics(issues)
        self.assertEqual(m["completedCount"], 3)

    def test_completedcount_in_result_keys(self):
        """completedCount must always be present in the result."""
        m = calculate_metrics([])
        self.assertIn("completedCount", m)

    def test_completedcount_cumulative_not_throughput(self):
        """completedCount counts ALL resolved, regardless of when — unlike throughput (interval)."""
        issue = make_issue(
            status="Done", created="2020-01-01T00:00:00Z",
            resolutiondate="2020-01-10T00:00:00Z",  # old issue
            transitions=[
                {"date": "2020-01-05T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2020-01-10T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([issue])
        # completedCount is always 1 — no cutoff here
        self.assertEqual(m["completedCount"], 1)


# ── backlogAgingDays ────────────────────────────────────────────────────────

class TestBacklogAging(unittest.TestCase):
    def test_zero_for_empty(self):
        m = calculate_metrics([])
        self.assertEqual(m["backlogAgingDays"], 0)

    def test_zero_for_no_backlog_issues(self):
        issue = make_issue(
            status="Done", created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-05T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        m = calculate_metrics([issue])
        self.assertEqual(m["backlogAgingDays"], 0)

    def test_aging_positive_for_old_backlog(self):
        """A backlog issue created 1 year ago must have aging >> 0."""
        issue = make_issue(status="To Do", created="2020-01-01T00:00:00Z")
        m = calculate_metrics([issue])
        self.assertGreater(m["backlogAgingDays"], 365)

    def test_aging_average_across_backlog_items(self):
        """Aging is averaged across all backlog items."""
        old = make_issue(key="T-1", status="To Do", created="2020-01-01T00:00:00Z")
        recent = make_issue(key="T-2", status="To Do", created="2024-01-01T00:00:00Z")
        m_old = calculate_metrics([old])
        m_recent = calculate_metrics([recent])
        m_both = calculate_metrics([old, recent])
        # Average must be between the two individual values
        self.assertGreater(m_both["backlogAgingDays"], m_recent["backlogAgingDays"])
        self.assertLess(m_both["backlogAgingDays"], m_old["backlogAgingDays"])

    def test_wip_not_counted_in_aging(self):
        """WIP issues (started but not resolved) must NOT affect backlogAgingDays."""
        wip = make_issue(
            status="In Progress", created="2020-01-01T00:00:00Z",
            transitions=[{"date": "2020-06-01T00:00:00Z", "from": "To Do", "to": "In Progress"}],
        )
        m = calculate_metrics([wip])
        self.assertEqual(m["backlogAgingDays"], 0)


# ── _map_issue direct tests ─────────────────────────────────────────────────

class TestMapIssueDirect(unittest.TestCase):
    def test_no_transitions_no_started_at(self):
        issue = make_issue(status="To Do", created="2024-01-01T00:00:00Z")
        mapped = _map_issue(issue)
        self.assertIsNone(mapped["started_at"])
        self.assertIsNone(mapped["resolved_at"])

    def test_done_with_resolutiondate_uses_it(self):
        issue = make_issue(
            status="Done", created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-05T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        mapped = _map_issue(issue)
        self.assertEqual(mapped["resolved_at"], "2024-01-05T00:00:00Z")

    def test_done_without_resolutiondate_uses_changelog(self):
        issue = make_issue(
            status="Done", created="2024-01-01T00:00:00Z",
            resolutiondate=None,
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-07T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        mapped = _map_issue(issue)
        self.assertEqual(mapped["resolved_at"], "2024-01-07T00:00:00Z")

    def test_in_progress_has_no_resolved_at(self):
        issue = make_issue(
            status="In Progress", created="2024-01-01T00:00:00Z",
            transitions=[{"date": "2024-01-02T00:00:00Z", "from": "To Do", "to": "In Progress"}],
        )
        mapped = _map_issue(issue)
        self.assertIsNone(mapped["resolved_at"])
        self.assertIsNotNone(mapped["started_at"])

    def test_reopened_flag_true_when_done_to_wip(self):
        issue = make_issue(
            status="Done", created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-06T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-03T00:00:00Z", "from": "In Progress", "to": "Done"},
                {"date": "2024-01-04T00:00:00Z", "from": "Done",        "to": "In Progress"},
                {"date": "2024-01-06T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        mapped = _map_issue(issue)
        self.assertTrue(mapped["reopened"])

    def test_reopened_flag_false_for_clean_flow(self):
        issue = make_issue(
            status="Done", created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-05T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-05T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        mapped = _map_issue(issue)
        self.assertFalse(mapped["reopened"])

    def test_created_at_preserved(self):
        issue = make_issue(status="To Do", created="2024-03-15T08:00:00Z")
        mapped = _map_issue(issue)
        self.assertEqual(mapped["created_at"], "2024-03-15T08:00:00Z")

    def test_last_done_not_first_done_for_resolved_at(self):
        """When issue is reopened and re-done, resolved_at = last DONE transition."""
        issue = make_issue(
            status="Done", created="2024-01-01T00:00:00Z",
            resolutiondate=None,
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-03T00:00:00Z", "from": "In Progress", "to": "Done"},
                {"date": "2024-01-04T00:00:00Z", "from": "Done",        "to": "In Progress"},
                {"date": "2024-01-08T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        mapped = _map_issue(issue)
        # resolved_at must be last Done, not first
        self.assertEqual(mapped["resolved_at"], "2024-01-08T00:00:00Z")

    def test_cycle_time_from_last_started_before_done(self):
        """started_at = last In Progress transition BEFORE last Done."""
        issue = make_issue(
            status="Done", created="2024-01-01T00:00:00Z",
            resolutiondate="2024-01-10T00:00:00Z",
            transitions=[
                {"date": "2024-01-02T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-04T00:00:00Z", "from": "In Progress", "to": "To Do"},
                {"date": "2024-01-06T00:00:00Z", "from": "To Do",       "to": "In Progress"},
                {"date": "2024-01-10T00:00:00Z", "from": "In Progress", "to": "Done"},
            ],
        )
        mapped = _map_issue(issue)
        self.assertEqual(mapped["started_at"], "2024-01-06T00:00:00Z")


if __name__ == "__main__":
    unittest.main(verbosity=2)
