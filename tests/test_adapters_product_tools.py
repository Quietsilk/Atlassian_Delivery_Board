"""Tests for Linear, Asana, and ClickUp adapters.

Covers: empty dataset, single issue, completed issue, no history,
invalid/unknown status, partial lifecycle.

All HTTP calls are monkey-patched so no real network traffic is made.
"""

import pytest
from server.adapters.base import CANONICAL_STARTED, CANONICAL_DONE


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _items(histories):
    """Flatten all items from a changelog histories list."""
    return [item for h in histories for item in h.get("items", [])]


def _statuses(histories):
    """Return list of (fromString, toString) tuples from changelog."""
    return [(i["fromString"], i["toString"]) for i in _items(histories)]


# ─────────────────────────────────────────────────────────────────────────────
# Linear adapter tests
# ─────────────────────────────────────────────────────────────────────────────

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

    # --- normalize() on empty list -------------------------------------------

    def test_empty_returns_empty(self):
        adapter = self._make_adapter()
        assert adapter.normalize([]) == []

    # --- single backlog issue -------------------------------------------------

    def test_backlog_issue(self):
        adapter = self._make_adapter()
        issue   = self._issue(state_type="backlog", state_name="Backlog")
        result  = adapter.normalize([issue])[0]

        assert result["fields"]["status"]["name"] == "Backlog"
        assert result["fields"]["resolutiondate"] is None
        assert result["changelog"]["histories"] == []

    # --- started issue (no history — synthesise) ------------------------------

    def test_started_no_history_synthesises(self):
        adapter = self._make_adapter()
        issue   = self._issue(state_type="started", state_name="In Progress",
                              created="2024-03-01T10:00:00Z")
        result  = adapter.normalize([issue])[0]

        assert result["fields"]["status"]["name"] == CANONICAL_STARTED
        histories = result["changelog"]["histories"]
        assert len(histories) == 1
        assert histories[0]["items"][0]["toString"] == CANONICAL_STARTED

    # --- completed issue (no history — synthesise) ----------------------------

    def test_completed_no_history_synthesises(self):
        adapter = self._make_adapter()
        issue   = self._issue(state_type="completed", state_name="Done",
                              created="2024-03-01T10:00:00Z",
                              completed="2024-03-10T15:00:00Z")
        result  = adapter.normalize([issue])[0]

        assert result["fields"]["status"]["name"] == CANONICAL_DONE
        assert result["fields"]["resolutiondate"] == "2024-03-10T15:00:00Z"
        statuses = _statuses(result["changelog"]["histories"])
        assert ("backlog", CANONICAL_STARTED) in statuses
        assert (CANONICAL_STARTED, CANONICAL_DONE) in statuses

    # --- cancelled treated as done -------------------------------------------

    def test_cancelled_treated_as_done(self):
        adapter = self._make_adapter()
        issue   = self._issue(state_type="cancelled", state_name="Cancelled",
                              canceled="2024-03-05T12:00:00Z")
        result  = adapter.normalize([issue])[0]
        assert result["fields"]["status"]["name"] == CANONICAL_DONE
        assert result["fields"]["resolutiondate"] == "2024-03-05T12:00:00Z"

    # --- real history nodes are used when present ----------------------------

    def test_history_nodes_build_changelog(self):
        adapter = self._make_adapter()
        history_nodes = [
            {
                "createdAt": "2024-03-05T08:00:00Z",
                "fromState": {"name": "Backlog",     "type": "backlog"},
                "toState":   {"name": "In Progress", "type": "started"},
            },
            {
                "createdAt": "2024-03-10T16:00:00Z",
                "fromState": {"name": "In Progress", "type": "started"},
                "toState":   {"name": "Done",        "type": "completed"},
            },
        ]
        issue  = self._issue(state_type="completed", completed="2024-03-10T16:00:00Z",
                             history_nodes=history_nodes)
        result = adapter.normalize([issue])[0]
        statuses = _statuses(result["changelog"]["histories"])
        # Linear uses state.name for unmapped types (backlog type → "Backlog")
        assert any(to == CANONICAL_STARTED for _, to in statuses), statuses
        assert any(to == CANONICAL_DONE   for _, to in statuses), statuses

    # --- history node with missing fromState/toState is skipped --------------

    def test_history_node_missing_state_skipped(self):
        adapter = self._make_adapter()
        history_nodes = [
            {"createdAt": "2024-03-05T08:00:00Z", "fromState": None, "toState": None},
        ]
        issue  = self._issue(history_nodes=history_nodes)
        result = adapter.normalize([issue])[0]
        # No usable history → fallback synthesise (backlog → no transitions)
        assert result["changelog"]["histories"] == []

    # --- unknown state type falls back to state name -------------------------

    def test_unknown_state_type_uses_name(self):
        adapter = self._make_adapter()
        issue   = self._issue(state_type="triage", state_name="Triage")
        result  = adapter.normalize([issue])[0]
        assert result["fields"]["status"]["name"] == "Triage"


# ─────────────────────────────────────────────────────────────────────────────
# Asana adapter tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAsanaAdapter:

    def _make_adapter(self):
        from server.adapters.asana import AsanaAdapter
        return AsanaAdapter(access_token="test-token", project_gid="proj-1")

    def _task(self, *, completed=False, completed_at=None,
              created_at="2024-01-15T00:00:00.000Z", stories=None):
        return {
            "gid": "task-1",
            "name": "Test Task",
            "created_at": created_at,
            "completed": completed,
            "completed_at": completed_at,
            "_stories": stories or [],
        }

    def _story(self, text, created="2024-02-01T10:00:00.000Z"):
        return {"type": "system", "text": text, "created_at": created}

    # --- empty ---------------------------------------------------------------

    def test_empty_returns_empty(self):
        from server.adapters.asana import AsanaAdapter
        adapter = AsanaAdapter(access_token="x", project_gid="y")
        assert adapter.normalize([]) == []

    # --- incomplete task with no stories ------------------------------------

    def test_incomplete_no_stories(self):
        adapter = self._make_adapter()
        task    = self._task()
        result  = adapter.normalize([task])[0]
        assert result["fields"]["status"]["name"] == "backlog"
        assert result["changelog"]["histories"] == []

    # --- completed task with no stories → fallback lifecycle -----------------

    def test_completed_no_stories_synthesises(self):
        adapter = self._make_adapter()
        task    = self._task(completed=True, completed_at="2024-02-10T12:00:00.000Z")
        result  = adapter.normalize([task])[0]
        assert result["fields"]["status"]["name"] == CANONICAL_DONE
        statuses = _statuses(result["changelog"]["histories"])
        assert ("backlog", CANONICAL_STARTED) in statuses
        assert (CANONICAL_STARTED, CANONICAL_DONE) in statuses

    # --- "in progress" story detected ----------------------------------------

    def test_in_progress_story_detected(self):
        adapter = self._make_adapter()
        stories = [self._story("marked as in progress", "2024-01-20T09:00:00.000Z")]
        task    = self._task(stories=stories)
        result  = adapter.normalize([task])[0]
        statuses = _statuses(result["changelog"]["histories"])
        assert ("backlog", CANONICAL_STARTED) in statuses

    # --- "marked complete" story detected ------------------------------------

    def test_completed_story_detected(self):
        adapter = self._make_adapter()
        stories = [
            self._story("marked as in progress", "2024-01-20T09:00:00.000Z"),
            self._story("marked complete",        "2024-02-05T14:00:00.000Z"),
        ]
        task   = self._task(completed=True, completed_at="2024-02-05T14:00:00.000Z",
                            stories=stories)
        result = adapter.normalize([task])[0]
        statuses = _statuses(result["changelog"]["histories"])
        assert (CANONICAL_STARTED, CANONICAL_DONE) in statuses

    # --- non-system stories are ignored --------------------------------------

    def test_non_system_story_ignored(self):
        adapter = self._make_adapter()
        stories = [{"type": "comment", "text": "in progress with this", "created_at": "2024-01-20T09:00:00.000Z"}]
        task    = self._task(stories=stories)
        result  = adapter.normalize([task])[0]
        # Comment story should be ignored
        assert result["changelog"]["histories"] == []

    # --- story without created_at is skipped ---------------------------------

    def test_story_missing_created_at_skipped(self):
        adapter = self._make_adapter()
        stories = [{"type": "system", "text": "in progress", "created_at": None}]
        task    = self._task(stories=stories)
        result  = adapter.normalize([task])[0]
        assert result["changelog"]["histories"] == []

    # --- partial lifecycle: completed but no created_at ----------------------

    def test_completed_without_created_at(self):
        adapter = self._make_adapter()
        task    = self._task(completed=True, completed_at="2024-02-10T12:00:00.000Z",
                             created_at=None)
        result  = adapter.normalize([task])[0]
        # Without created_at, only the done transition is synthesised
        histories = result["changelog"]["histories"]
        assert len(histories) == 1
        assert histories[0]["items"][0]["toString"] == CANONICAL_DONE


# ─────────────────────────────────────────────────────────────────────────────
# ClickUp adapter tests
# ─────────────────────────────────────────────────────────────────────────────

class TestClickUpAdapter:

    def _make_adapter(self):
        from server.adapters.clickup import ClickUpAdapter
        return ClickUpAdapter(api_key="test-key", list_id="list-1")

    def _task(self, *, status="open", date_created="1704067200000",
              date_done=None, history=None):
        return {
            "id": "task-1",
            "name": "Test Task",
            "status": {"status": status},
            "date_created": date_created,
            "date_done": date_done,
            "history": history,
        }

    # --- empty ---------------------------------------------------------------

    def test_empty_returns_empty(self):
        adapter = self._make_adapter()
        assert adapter.normalize([]) == []

    # --- open task (backlog) -------------------------------------------------

    def test_open_task_is_backlog(self):
        adapter = self._make_adapter()
        task    = self._task(status="open")
        result  = adapter.normalize([task])[0]
        # "open" doesn't match in_progress or done keywords → stays as "open"
        assert result["fields"]["status"]["name"] == "open"
        assert result["changelog"]["histories"] == []

    # --- in progress status --------------------------------------------------

    def test_in_progress_status_normalized(self):
        adapter = self._make_adapter()
        task    = self._task(status="in progress")
        result  = adapter.normalize([task])[0]
        assert result["fields"]["status"]["name"] == CANONICAL_STARTED
        # synthesised: backlog → in progress
        statuses = _statuses(result["changelog"]["histories"])
        assert ("backlog", CANONICAL_STARTED) in statuses

    # --- done task with date_done -------------------------------------------

    def test_done_task_synthesises_lifecycle(self):
        adapter = self._make_adapter()
        # date_done = 2024-02-10 in ms
        task   = self._task(status="complete", date_done="1707566400000")
        result = adapter.normalize([task])[0]
        assert result["fields"]["status"]["name"] == CANONICAL_DONE
        assert result["fields"]["resolutiondate"] is not None
        statuses = _statuses(result["changelog"]["histories"])
        assert (CANONICAL_STARTED, CANONICAL_DONE) in statuses

    # --- ms_to_iso edge cases ------------------------------------------------

    def test_zero_date_done_treated_as_none(self):
        adapter = self._make_adapter()
        task    = self._task(status="complete", date_done="0")
        result  = adapter.normalize([task])[0]
        assert result["fields"]["resolutiondate"] is None

    def test_null_date_done(self):
        adapter = self._make_adapter()
        task    = self._task(status="done", date_done=None)
        result  = adapter.normalize([task])[0]
        # done status keyword but no date → no resolution, empty lifecycle
        assert result["fields"]["resolutiondate"] is None

    # --- real history entries used when present ------------------------------

    def test_real_history_entries_preferred(self):
        adapter = self._make_adapter()
        history = [
            {
                "field": "status",
                "date": "1706745600000",   # ~2024-02-01
                "before": {"status": "open"},
                "after":  {"status": "in progress"},
            },
            {
                "field": "status",
                "date": "1707566400000",   # ~2024-02-10
                "before": {"status": "in progress"},
                "after":  {"status": "complete"},
            },
        ]
        task   = self._task(status="complete", date_done="1707566400000", history=history)
        result = adapter.normalize([task])[0]
        statuses = _statuses(result["changelog"]["histories"])
        assert ("open", CANONICAL_STARTED) in statuses
        assert (CANONICAL_STARTED, CANONICAL_DONE) in statuses

    # --- non-status history entries are ignored ------------------------------

    def test_non_status_history_ignored(self):
        adapter = self._make_adapter()
        history = [{"field": "name", "date": "1706745600000",
                    "before": {"name": "old"}, "after": {"name": "new"}}]
        task   = self._task(status="in progress", history=history)
        result = adapter.normalize([task])[0]
        # Non-status history entry → falls through to synthesise
        statuses = _statuses(result["changelog"]["histories"])
        assert ("backlog", CANONICAL_STARTED) in statuses

    # --- unknown status stays as-is -----------------------------------------

    def test_unknown_status_passes_through(self):
        adapter = self._make_adapter()
        task    = self._task(status="pending review")
        result  = adapter.normalize([task])[0]
        assert result["fields"]["status"]["name"] == "pending review"


# ─────────────────────────────────────────────────────────────────────────────
# build_adapter factory tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildAdapter:

    def test_jira_adapter(self):
        from server.adapters.base import build_adapter
        from server.adapters.jira import JiraAdapter
        a = build_adapter("jira", {
            "base_url": "https://jira.example.com",
            "email": "user@example.com",
            "api_token": "tok",
            "jql": "project=X",
        })
        assert isinstance(a, JiraAdapter)

    def test_linear_adapter(self):
        from server.adapters.base import build_adapter
        from server.adapters.linear import LinearAdapter
        a = build_adapter("linear", {"api_key": "k", "team_id": "t"})
        assert isinstance(a, LinearAdapter)

    def test_asana_adapter(self):
        from server.adapters.base import build_adapter
        from server.adapters.asana import AsanaAdapter
        a = build_adapter("asana", {"access_token": "tok", "project_gid": "gid"})
        assert isinstance(a, AsanaAdapter)

    def test_clickup_adapter(self):
        from server.adapters.base import build_adapter
        from server.adapters.clickup import ClickUpAdapter
        a = build_adapter("clickup", {"api_key": "k", "list_id": "lid"})
        assert isinstance(a, ClickUpAdapter)

    def test_unknown_source_raises(self):
        from server.adapters.base import build_adapter
        with pytest.raises(ValueError, match="Unknown source"):
            build_adapter("notion", {})

    def test_source_is_case_insensitive(self):
        from server.adapters.base import build_adapter
        from server.adapters.linear import LinearAdapter
        a = build_adapter("LINEAR", {"api_key": "k", "team_id": "t"})
        assert isinstance(a, LinearAdapter)
