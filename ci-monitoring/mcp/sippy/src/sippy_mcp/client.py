"""Sippy API client."""

import fnmatch
import os
from collections.abc import Callable
from typing import Any

import httpx

SIPPY_BASE_URL = "https://sippy.dptools.openshift.org"


class SippyClient:
    """Client for the Sippy CI monitoring API."""

    def __init__(self, base_url: str | None = None, timeout: float = 30.0):
        self.base_url = base_url or os.environ.get("SIPPY_URL", SIPPY_BASE_URL)
        self.client = httpx.Client(timeout=timeout)

    def get_releases(self) -> dict[str, Any]:
        """Get available releases with metadata."""
        resp = self.client.get(f"{self.base_url}/api/releases")
        resp.raise_for_status()
        return resp.json()

    def get_jobs(
        self,
        release: str,
        *,
        filter_func: Callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get jobs for a release with optional filtering."""
        params = {"release": release}
        resp = self.client.get(f"{self.base_url}/api/jobs", params=params)
        resp.raise_for_status()
        jobs = resp.json()
        if filter_func:
            jobs = [j for j in jobs if filter_func(j)]
        return jobs

    def get_health(self, release: str) -> dict[str, Any]:
        """Get release health indicators."""
        params = {"release": release}
        resp = self.client.get(f"{self.base_url}/api/health", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_tests(
        self,
        release: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get test results for a release."""
        params = {"release": release, "limit": limit}
        resp = self.client.get(f"{self.base_url}/api/tests", params=params)
        resp.raise_for_status()
        return resp.json()

    def search_jobs(
        self,
        release: str,
        *,
        name_contains: str | None = None,
        variant_contains: str | None = None,
        min_pass_percentage: float | None = None,
        max_pass_percentage: float | None = None,
    ) -> list[dict[str, Any]]:
        """Search jobs with flexible filters."""
        jobs = self.get_jobs(release)

        results = []
        for job in jobs:
            # Name filter
            if name_contains and name_contains.lower() not in job.get("name", "").lower():
                continue

            # Variant filter
            if variant_contains:
                variants = job.get("variants", [])
                if not any(variant_contains.lower() in v.lower() for v in variants):
                    continue

            # Pass percentage filters
            pass_pct = job.get("current_pass_percentage", 0)
            if min_pass_percentage is not None and pass_pct < min_pass_percentage:
                continue
            if max_pass_percentage is not None and pass_pct > max_pass_percentage:
                continue

            results.append(job)

        return results

    def get_hypershift_jobs(self, release: str) -> list[dict[str, Any]]:
        """Get HCP/Hypershift jobs for a release."""
        return self.search_jobs(
            release,
            variant_contains="Installer:hypershift",
        )

    def get_failing_jobs(
        self,
        release: str,
        *,
        max_pass_percentage: float = 90.0,
    ) -> list[dict[str, Any]]:
        """Get jobs below a pass percentage threshold."""
        return self.search_jobs(
            release,
            max_pass_percentage=max_pass_percentage,
        )

    def get_interop_jobs(
        self,
        release: str,
        *,
        patterns: list[str] | None = None,
        max_pass_percentage: float | None = None,
    ) -> list[dict[str, Any]]:
        """Get interop jobs matching glob patterns.

        Args:
            release: Release version (e.g., '4.19')
            patterns: Glob patterns to match job names (default: *interop*, *opp*, *lp-*)
            max_pass_percentage: Optional filter for failing jobs
        """
        if patterns is None:
            patterns = ["*interop*", "*opp*", "*lp-*"]

        jobs = self.get_jobs(release)
        results = []

        for job in jobs:
            job_name = job.get("name", "")

            matches_pattern = any(
                fnmatch.fnmatch(job_name.lower(), pattern.lower())
                for pattern in patterns
            )
            if not matches_pattern:
                continue

            if max_pass_percentage is not None:
                pass_pct = job.get("current_pass_percentage", 0)
                if pass_pct > max_pass_percentage:
                    continue

            results.append(job)

        return results

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
