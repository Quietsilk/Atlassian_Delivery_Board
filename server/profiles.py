"""Validated server-side source profiles without client-visible credentials."""

import json
import re

from server.api import _parse_trello_lookback_days, _validate_jira_base_url


_PROFILE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_PROJECT_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
_MAX_JQL_LENGTH = 2048


def _required_text(value, field, *, maximum=256):
    text = str(value or "").strip()
    if not text or len(text) > maximum:
        raise ValueError(f"profile {field} is required and must be at most {maximum} characters")
    return text


def load_profiles(raw, jira_credentials, trello_credentials=None):
    try:
        items = json.loads(raw or "[]")
    except json.JSONDecodeError as error:
        raise ValueError("ADA_PROFILES must be valid JSON") from error
    if not isinstance(items, list):
        raise ValueError("ADA_PROFILES must be a JSON array")

    profiles = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each ADA_PROFILES item must be an object")
        profile_id = _required_text(item.get("id"), "id", maximum=64)
        if not _PROFILE_ID.fullmatch(profile_id) or profile_id in profiles:
            raise ValueError(f"invalid or duplicate profile id: {profile_id!r}")
        source = _required_text(item.get("source", "jira"), "source", maximum=16).lower()
        project_key = _required_text(
            item.get("project_key") or item.get("project"), "project_key", maximum=64
        )
        if not _PROJECT_KEY.fullmatch(project_key):
            raise ValueError(f"invalid project_key for profile {profile_id!r}")
        label = _required_text(item.get("label") or project_key, "label", maximum=80)
        methodology = str(item.get("methodology") or ("kanban" if source == "trello" else "scrum")).lower()
        if methodology not in ("scrum", "kanban"):
            raise ValueError(f"invalid methodology for profile {profile_id!r}")

        if source == "jira":
            jql = _required_text(item.get("jql"), "jql", maximum=_MAX_JQL_LENGTH)
            base_url = _validate_jira_base_url(jira_credentials.get("base_url", ""))
            email = _required_text(jira_credentials.get("email"), "JIRA_EMAIL", maximum=320)
            token = _required_text(jira_credentials.get("api_token"), "JIRA_API_TOKEN", maximum=4096)
            config = {"base_url": base_url, "email": email, "api_token": token, "jql": jql}
            issue_base_url = base_url
        elif source == "trello":
            trello_credentials = trello_credentials or {}
            api_key = _required_text(trello_credentials.get("api_key"), "TRELLO_API_KEY", maximum=256)
            token = _required_text(trello_credentials.get("token"), "TRELLO_TOKEN", maximum=4096)
            board_id = _required_text(item.get("board_id"), "board_id", maximum=128)
            config = {
                "api_key": api_key,
                "token": token,
                "board_id": board_id,
                "lists_in_progress": str(item.get("lists_in_progress") or "")[:1024],
                "lists_done": str(item.get("lists_done") or "")[:1024],
                "lookback_days": _parse_trello_lookback_days(item.get("lookback_days")),
            }
            issue_base_url = None
        else:
            raise ValueError(f"unsupported source for profile {profile_id!r}: {source!r}")

        profiles[profile_id] = {
            "id": profile_id,
            "label": label,
            "project_key": project_key,
            "source": source,
            "methodology": methodology,
            "issue_base_url": issue_base_url,
            "config": config,
        }
    return profiles


def public_profile(profile):
    return {
        "id": profile["id"],
        "label": profile["label"],
        "project": profile["project_key"],
        "source": profile["source"],
        "methodology": profile["methodology"],
        "issueBaseUrl": profile["issue_base_url"],
    }
