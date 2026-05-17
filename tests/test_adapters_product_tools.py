"""Tests for product-tool adapters.

Only Jira and Linear are supported sources.
"""

import pytest
from unittest.mock import patch

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


class TestLinearAdapterFetch:
    """Tests for LinearAdapter.fetch() — pagination, filter_, retry integration."""

    def _make_adapter(self, filter_=None):
        from server.adapters.linear import LinearAdapter
        return LinearAdapter(api_key="test-key", team_id="team-1", filter_=filter_)

    def _node(self, issue_id="i1", identifier="T-1"):
        return {
            "id": issue_id, "identifier": identifier,
            "createdAt": "2024-01-01T00:00:00Z",
            "completedAt": None, "canceledAt": None,
            "state": {"name": "In Progress", "type": "started"},
            "history": {"nodes": []},
        }

    def _page(self, nodes, has_next=False, cursor=None):
        return {"data": {"issues": {
            "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
            "nodes": nodes,
        }}}

    def test_fetch_single_page_returns_nodes(self):
        adapter = self._make_adapter()
        response = self._page([self._node()], has_next=False)

        with patch("server.adapters.linear._http_post", return_value=response):
            result = adapter.fetch()

        assert len(result) == 1
        assert result[0]["id"] == "i1"

    def test_fetch_paginates_until_no_next_page(self):
        adapter = self._make_adapter()
        n1 = self._node("i1", "T-1")
        n2 = self._node("i2", "T-2")
        n3 = self._node("i3", "T-3")

        responses = [
            self._page([n1], has_next=True,  cursor="cur1"),
            self._page([n2], has_next=True,  cursor="cur2"),
            self._page([n3], has_next=False),
        ]
        idx = [0]

        def fake_post(url, headers, body):
            r = responses[idx[0]]
            idx[0] += 1
            return r

        with patch("server.adapters.linear._http_post", side_effect=fake_post):
            result = adapter.fetch()

        assert len(result) == 3
        assert [r["id"] for r in result] == ["i1", "i2", "i3"]

    def test_fetch_passes_cursor_on_subsequent_pages(self):
        adapter = self._make_adapter()
        captured_vars = []

        def fake_post(url, headers, body):
            captured_vars.append(body.get("variables", {}))
            if len(captured_vars) == 1:
                return self._page([self._node()], has_next=True, cursor="next-cur")
            return self._page([self._node("i2", "T-2")], has_next=False)

        with patch("server.adapters.linear._http_post", side_effect=fake_post):
            adapter.fetch()

        assert captured_vars[0].get("after") is None
        assert captured_vars[1].get("after") == "next-cur"

    def test_fetch_includes_filter_when_set(self):
        adapter = self._make_adapter(filter_={"priority": {"eq": 1}})
        captured = {}

        def fake_post(url, headers, body):
            captured["variables"] = body.get("variables", {})
            return self._page([self._node()], has_next=False)

        with patch("server.adapters.linear._http_post", side_effect=fake_post):
            adapter.fetch()

        assert "filter" in captured["variables"]
        assert captured["variables"]["filter"] == {"priority": {"eq": 1}}

    def test_fetch_omits_filter_when_not_set(self):
        adapter = self._make_adapter(filter_=None)
        captured = {}

        def fake_post(url, headers, body):
            captured["variables"] = body.get("variables", {})
            return self._page([], has_next=False)

        with patch("server.adapters.linear._http_post", side_effect=fake_post):
            adapter.fetch()

        assert "filter" not in captured["variables"]

    def test_fetch_empty_team_returns_empty_list(self):
        adapter = self._make_adapter()
        with patch("server.adapters.linear._http_post", return_value=self._page([])):
            result = adapter.fetch()
        assert result == []

    def test_fetch_uses_with_retry(self):
        """_with_retry is called; a single 500 error is retried and succeeds."""
        adapter = self._make_adapter()
        import urllib.error
        attempts = [0]

        def fake_post(url, headers, body):
            attempts[0] += 1
            if attempts[0] == 1:
                raise urllib.error.HTTPError("url", 500, "err", {}, None)
            return self._page([self._node()], has_next=False)

        with patch("server.adapters.linear._http_post", side_effect=fake_post), \
             patch("time.sleep"):
            result = adapter.fetch()

        assert len(result) == 1
        assert attempts[0] == 2


class TestLinearAdapterNormalizeEdgeCases:
    """Edge cases in _to_canonical not covered by the main normalize tests."""

    def _make_adapter(self):
        from server.adapters.linear import LinearAdapter
        return LinearAdapter(api_key="test-key", team_id="team-1")

    def _issue(self, *, state_type="backlog", state_name="Backlog",
               created="2024-01-01T00:00:00Z", completed=None, canceled=None,
               history_nodes=None):
        return {
            "id": "issue-1", "identifier": "ENG-1",
            "createdAt": created, "completedAt": completed, "canceledAt": canceled,
            "state": {"name": state_name, "type": state_type},
            "history": {"nodes": history_nodes or []},
        }

    def test_history_node_with_none_to_state_is_skipped(self):
        adapter = self._make_adapter()
        issue = self._issue(
            state_type="started", state_name="In Progress",
            history_nodes=[{
                "createdAt": "2024-03-05T08:00:00Z",
                "fromState": {"name": "Backlog", "type": "backlog"},
                "toState": None,
            }],
        )
        result = adapter.normalize([issue])[0]
        # Invalid node skipped → histories empty → synthesised lifecycle (1 entry)
        histories = result["changelog"]["histories"]
        assert len(histories) == 1
        assert histories[0]["items"][0]["toString"] == "in progress"

    def test_history_node_with_none_from_state_is_skipped(self):
        adapter = self._make_adapter()
        issue = self._issue(
            state_type="backlog", state_name="Backlog",
            history_nodes=[{
                "createdAt": "2024-03-05T08:00:00Z",
                "fromState": None,
                "toState": {"name": "Backlog", "type": "backlog"},
            }],
        )
        result = adapter.normalize([issue])[0]
        assert result["changelog"]["histories"] == []

    def test_both_completed_at_and_canceled_at_prefers_completed(self):
        adapter = self._make_adapter()
        issue = self._issue(
            state_type="completed",
            completed="2024-03-10T10:00:00Z",
            canceled="2024-03-12T10:00:00Z",
        )
        result = adapter.normalize([issue])[0]
        # completedAt takes precedence (it's first in `or`)
        assert result["fields"]["resolutiondate"] == "2024-03-10T10:00:00Z"

    def test_synthesise_done_without_created_at_skips_start_entry(self):
        adapter = self._make_adapter()
        issue = self._issue(
            state_type="completed",
            created=None,     # unusual but possible in some APIs
            completed="2024-03-10T10:00:00Z",
        )
        issue["createdAt"] = None
        result = adapter.normalize([issue])[0]
        # Without createdAt, synthesise only adds the Done transition
        histories = result["changelog"]["histories"]
        assert any(h["items"][0]["toString"] == "done" for h in histories)

    def test_normalize_multiple_issues(self):
        adapter = self._make_adapter()
        issues = [
            self._issue(state_type="backlog",   state_name="Backlog"),
            self._issue(state_type="started",   state_name="In Progress"),
            self._issue(state_type="completed", state_name="Done",
                        completed="2024-03-10T10:00:00Z"),
        ]
        result = adapter.normalize(issues)
        assert len(result) == 3
        assert result[0]["fields"]["status"]["name"] == "Backlog"
        assert result[1]["fields"]["status"]["name"] == "in progress"
        assert result[2]["fields"]["status"]["name"] == "done"


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
