"""Tests for product-tool adapters.

Only Jira and Linear are supported sources.
"""

import pytest

from server.adapters.base import CANONICAL_STARTED, CANONICAL_DONE


def _items(histories):
    """Flatten all items from a changelog histories list."""
    return [item for h in histories for item in h.get("items", [])]


def _statuses(histories):
    """Return list of (fromString, toString) tuples from changelog."""
    return [(i["fromString"], i["toString"]) for i in _items(histories)]


class TestLinearAdapter:

    def _make_adapter(self):
        from server.adapters.linear import LinearAdapter
        return LinearAdapter(api_key="test-key", team_id="team-1")

    def _issue(self, *, state_type="backlog", state_name="Backlog",
               created="2024-01-01T00:00:00Z", completed=None, canceled=None,
               history_nodes=None):
        return {
            "id": "issue-1",
            "identifier": "ENG-1",
            "createdAt": created,
            "completedAt": completed,
            "canceledAt": canceled,
            "state": {"name": state_name, "type": state_type},
            "history": {"nodes": history_nodes or []},
        }

    def test_empty_returns_empty(self):
        adapter = self._make_adapter()
        assert adapter.normalize([]) == []

    def test_backlog_issue(self):
        adapter = self._make_adapter()
        issue = self._issue(state_type="backlog", state_name="Backlog")
        result = adapter.normalize([issue])[0]

        assert result["fields"]["status"]["name"] == "Backlog"
        assert result["fields"]["resolutiondate"] is None
        assert result["changelog"]["histories"] == []

    def test_started_no_history_synthesises(self):
        adapter = self._make_adapter()
        issue = self._issue(
            state_type="started",
            state_name="In Progress",
            created="2024-03-01T10:00:00Z",
        )
        result = adapter.normalize([issue])[0]

        assert result["fields"]["status"]["name"] == CANONICAL_STARTED
        histories = result["changelog"]["histories"]
        assert len(histories) == 1
        assert histories[0]["items"][0]["toString"] == CANONICAL_STARTED

    def test_completed_no_history_synthesises(self):
        adapter = self._make_adapter()
        issue = self._issue(
            state_type="completed",
            state_name="Done",
            created="2024-03-01T10:00:00Z",
            completed="2024-03-10T15:00:00Z",
        )
        result = adapter.normalize([issue])[0]

        assert result["fields"]["status"]["name"] == CANONICAL_DONE
        assert result["fields"]["resolutiondate"] == "2024-03-10T15:00:00Z"
        statuses = _statuses(result["changelog"]["histories"])
        assert ("backlog", CANONICAL_STARTED) in statuses
        assert (CANONICAL_STARTED, CANONICAL_DONE) in statuses

    def test_cancelled_treated_as_done(self):
        adapter = self._make_adapter()
        issue = self._issue(
            state_type="cancelled",
            state_name="Cancelled",
            canceled="2024-03-05T12:00:00Z",
        )
        result = adapter.normalize([issue])[0]
        assert result["fields"]["status"]["name"] == CANONICAL_DONE
        assert result["fields"]["resolutiondate"] == "2024-03-05T12:00:00Z"

    def test_history_nodes_build_changelog(self):
        adapter = self._make_adapter()
        history_nodes = [
            {
                "createdAt": "2024-03-05T08:00:00Z",
                "fromState": {"name": "Backlog", "type": "backlog"},
                "toState": {"name": "In Progress", "type": "started"},
            },
            {
                "createdAt": "2024-03-10T16:00:00Z",
                "fromState": {"name": "In Progress", "type": "started"},
                "toState": {"name": "Done", "type": "completed"},
            },
        ]
        issue = self._issue(
            state_type="completed",
            completed="2024-03-10T16:00:00Z",
            history_nodes=history_nodes,
        )
        result = adapter.normalize([issue])[0]
        statuses = _statuses(result["changelog"]["histories"])
        assert any(to == CANONICAL_STARTED for _, to in statuses), statuses
        assert any(to == CANONICAL_DONE for _, to in statuses), statuses

    def test_history_node_missing_state_skipped(self):
        adapter = self._make_adapter()
        history_nodes = [
            {"createdAt": "2024-03-05T08:00:00Z", "fromState": None, "toState": None},
        ]
        issue = self._issue(history_nodes=history_nodes)
        result = adapter.normalize([issue])[0]
        assert result["changelog"]["histories"] == []

    def test_unknown_state_type_uses_name(self):
        adapter = self._make_adapter()
        issue = self._issue(state_type="triage", state_name="Triage")
        result = adapter.normalize([issue])[0]
        assert result["fields"]["status"]["name"] == "Triage"


class TestBuildAdapter:

    def test_jira_adapter(self):
        from server.adapters.base import build_adapter
        from server.adapters.jira import JiraAdapter
        adapter = build_adapter("jira", {
            "base_url": "https://jira.example.com",
            "email": "user@example.com",
            "api_token": "tok",
            "jql": "project=X",
        })
        assert isinstance(adapter, JiraAdapter)

    def test_linear_adapter(self):
        from server.adapters.base import build_adapter
        from server.adapters.linear import LinearAdapter
        adapter = build_adapter("linear", {"api_key": "k", "team_id": "t"})
        assert isinstance(adapter, LinearAdapter)

    @pytest.mark.parametrize("source", ["asana", "clickup", "notion"])
    def test_unsupported_source_raises(self, source):
        from server.adapters.base import build_adapter
        with pytest.raises(ValueError, match="Supported: jira, linear"):
            build_adapter(source, {})

    def test_source_is_case_insensitive(self):
        from server.adapters.base import build_adapter
        from server.adapters.linear import LinearAdapter
        adapter = build_adapter("LINEAR", {"api_key": "k", "team_id": "t"})
        assert isinstance(adapter, LinearAdapter)
