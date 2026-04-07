"""Jira REST API client."""

from typing import Any

import httpx


class JiraClient:
    """Minimal Jira REST client for watcher workflows."""

    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        self._user_cache: dict[str, Any] | None = None

    def search_issues(
        self,
        jql: str,
        fields: list[str] | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Search issues using JQL.

        Args:
            jql: JQL query string
            fields: List of fields to return (default: key, summary, status, assignee, labels)
            max_results: Maximum number of results
        """
        if fields is None:
            fields = ["key", "summary", "status", "assignee", "labels", "created", "updated"]

        params = {
            "jql": jql,
            "fields": ",".join(fields),
            "maxResults": max_results,
        }
        resp = self.client.get(f"{self.base_url}/rest/api/2/search", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("issues", [])

    def get_issue(
        self,
        issue_key: str,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get single issue by key."""
        params = {}
        if fields:
            params["fields"] = ",".join(fields)

        resp = self.client.get(f"{self.base_url}/rest/api/2/issue/{issue_key}", params=params)
        resp.raise_for_status()
        return resp.json()

    def assign_issue(self, issue_key: str, account_id: str) -> bool:
        """Assign issue to user by account ID.

        Args:
            issue_key: Issue key (e.g., 'LPINTEROP-123')
            account_id: User's account ID (from get_myself)
        """
        # Red Hat Jira uses 'name' instead of 'accountId' for assignment
        payload = {"name": account_id}
        resp = self.client.put(
            f"{self.base_url}/rest/api/2/issue/{issue_key}/assignee",
            json=payload,
        )
        resp.raise_for_status()
        return True

    def add_comment(self, issue_key: str, comment: str) -> dict[str, Any]:
        """Add comment to issue."""
        payload = {"body": comment}
        resp = self.client.post(
            f"{self.base_url}/rest/api/2/issue/{issue_key}/comment",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def update_labels(
        self,
        issue_key: str,
        add: list[str] | None = None,
        remove: list[str] | None = None,
    ) -> bool:
        """Update issue labels.

        Args:
            issue_key: Issue key
            add: Labels to add
            remove: Labels to remove
        """
        update_ops = []
        if add:
            for label in add:
                update_ops.append({"add": label})
        if remove:
            for label in remove:
                update_ops.append({"remove": label})

        if not update_ops:
            return True

        payload = {"update": {"labels": update_ops}}
        resp = self.client.put(
            f"{self.base_url}/rest/api/2/issue/{issue_key}",
            json=payload,
        )
        resp.raise_for_status()
        return True

    def get_myself(self) -> dict[str, Any]:
        """Get current authenticated user."""
        if self._user_cache is not None:
            return self._user_cache

        resp = self.client.get(f"{self.base_url}/rest/api/2/myself")
        resp.raise_for_status()
        self._user_cache = resp.json()
        return self._user_cache

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
