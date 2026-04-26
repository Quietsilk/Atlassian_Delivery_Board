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
        self.assertEqual(m["reopenedCount"], 0)
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
    def test_single_completed_counted_in_reopened(self):
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
        self.assertEqual(m["reopenedCount"], 0)
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

    def test_reopened_only_among_done(self):
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
        self.assertEqual(m["reopenedCount"], 0)

    def test_reopened_counted_for_completed(self):
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
        self.assertEqual(m["reopenedCount"], 1)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
