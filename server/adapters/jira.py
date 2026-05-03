"""Jira adapter — wraps existing fetch_jira from ingestion.py.

Data is already in canonical format; normalize() is identity.
"""

from server.adapters.base import Adapter
from server.ingestion import fetch_jira


class JiraAdapter(Adapter):
    source = "jira"

    def __init__(self, base_url: str, email: str, api_token: str, jql: str):
        self.base_url  = base_url.rstrip("/")
        self.email     = email
        self.api_token = api_token
        self.jql       = jql

    def fetch(self) -> list:
        return fetch_jira(self.base_url, self.email, self.api_token, self.jql)

    def normalize(self, raw_issues: list) -> list:
        # Already canonical — pass through unchanged
        return raw_issues
