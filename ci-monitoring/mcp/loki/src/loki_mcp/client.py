"""Loki API client with OAuth2 authentication."""

import os
import time
from typing import Any
from urllib.parse import urlencode

import httpx

# Observatorium Loki endpoint for dptp
LOKI_BASE_URL = "https://observatorium-mst.api.openshift.com/api/logs/v1/dptp/loki/api/v1"

# Red Hat SSO for OAuth2
SSO_TOKEN_URL = "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"


class LokiClient:
    """Client for querying Grafana Loki via Observatorium."""

    def __init__(
        self,
        base_url: str = LOKI_BASE_URL,
        timeout: float = 60.0,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.client_id = client_id or os.environ.get("LOKI_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("LOKI_CLIENT_SECRET")
        self.client = httpx.Client(timeout=timeout)
        self._token: str | None = None
        self._token_expiry: float = 0

    def _get_token(self) -> str:
        """Get or refresh OAuth2 access token."""
        # Check if we have a valid cached token
        if self._token and time.time() < self._token_expiry - 60:
            return self._token

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "LOKI_CLIENT_ID and LOKI_CLIENT_SECRET environment variables must be set."
            )

        # Request new token
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        resp = self.client.post(
            SSO_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()

        token_data = resp.json()
        self._token = token_data["access_token"]
        # Token expiry in seconds (usually 300 for RHSSO)
        self._token_expiry = time.time() + token_data.get("expires_in", 300)

        return self._token

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with auth token."""
        token = self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def query(
        self,
        query: str,
        *,
        limit: int = 100,
        direction: str = "backward",
    ) -> dict[str, Any]:
        """Execute an instant LogQL query.

        Args:
            query: LogQL query string
            limit: Maximum number of entries to return
            direction: Log order - "backward" (newest first) or "forward" (oldest first)

        Returns:
            Query result with status, data (streams/values), and stats
        """
        params = {
            "query": query,
            "limit": limit,
            "direction": direction,
        }

        resp = self.client.get(
            f"{self.base_url}/query",
            params=params,
            headers=self._get_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def query_range(
        self,
        query: str,
        *,
        start: str | None = None,
        end: str | None = None,
        limit: int = 100,
        step: str | None = None,
        direction: str = "backward",
    ) -> dict[str, Any]:
        """Execute a range LogQL query.

        Args:
            query: LogQL query string
            start: Start timestamp (RFC3339 or Unix epoch). Default: 1 hour ago
            end: End timestamp (RFC3339 or Unix epoch). Default: now
            limit: Maximum number of entries to return
            step: Query resolution step width (e.g., "5m")
            direction: Log order - "backward" (newest first) or "forward" (oldest first)

        Returns:
            Query result with status, data (matrix/streams/values), and stats
        """
        params: dict[str, Any] = {
            "query": query,
            "limit": limit,
            "direction": direction,
        }

        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if step:
            params["step"] = step

        resp = self.client.get(
            f"{self.base_url}/query_range",
            params=params,
            headers=self._get_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def labels(self, start: str | None = None, end: str | None = None) -> list[str]:
        """Get list of available labels.

        Args:
            start: Start timestamp for label search
            end: End timestamp for label search

        Returns:
            List of label names
        """
        params: dict[str, str] = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        resp = self.client.get(
            f"{self.base_url}/labels",
            params=params,
            headers=self._get_headers(),
        )
        resp.raise_for_status()
        result = resp.json()
        return result.get("data", [])

    def label_values(
        self,
        label: str,
        start: str | None = None,
        end: str | None = None,
    ) -> list[str]:
        """Get values for a specific label.

        Args:
            label: Label name
            start: Start timestamp for value search
            end: End timestamp for value search

        Returns:
            List of values for the label
        """
        params: dict[str, str] = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        resp = self.client.get(
            f"{self.base_url}/label/{label}/values",
            params=params,
            headers=self._get_headers(),
        )
        resp.raise_for_status()
        result = resp.json()
        return result.get("data", [])

    def series(
        self,
        match: list[str],
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict[str, str]]:
        """Find series matching label selectors.

        Args:
            match: List of series selectors (e.g., ['{job="foo"}'])
            start: Start timestamp
            end: End timestamp

        Returns:
            List of label sets for matching series
        """
        # Build query string with multiple match[] parameters
        params_list = [("match[]", m) for m in match]
        if start:
            params_list.append(("start", start))
        if end:
            params_list.append(("end", end))

        query_string = urlencode(params_list)

        resp = self.client.get(
            f"{self.base_url}/series?{query_string}",
            headers=self._get_headers(),
        )
        resp.raise_for_status()
        result = resp.json()
        return result.get("data", [])

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
