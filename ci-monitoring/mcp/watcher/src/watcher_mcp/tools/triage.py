"""Triage tools for watcher workflows."""

from typing import Any

from ..clients.jira import JiraClient
from sippy_mcp.client import SippyClient
from ..config import WatcherConfig


def extract_job_short_name(job_name: str) -> str:
    """Extract short name from full job name for ticket matching.

    Example: 'periodic-ci-openshift-interop-tests-main-opp-aws-4.19' -> 'opp-aws'
    """
    # Remove common prefixes
    name = job_name
    for prefix in ["periodic-ci-", "release-openshift-", "openshift-interop-tests-"]:
        name = name.replace(prefix, "")

    # Extract the meaningful part (platform-variant)
    parts = name.split("-")
    # Look for common platform identifiers
    platforms = ["aws", "gcp", "azure", "rosa", "hypershift", "opp", "lp"]
    meaningful_parts = []
    for part in parts:
        if part.lower() in platforms or any(p in part.lower() for p in platforms):
            meaningful_parts.append(part)
        elif meaningful_parts:  # Already found platform, include variant
            meaningful_parts.append(part)

    return "-".join(meaningful_parts[:3]) if meaningful_parts else name[:30]


async def watcher_daily_triage(
    sippy: SippyClient,
    jira: JiraClient,
    config: WatcherConfig,
    *,
    release: str,
    max_pass_percentage: float = 90.0,
    include_tickets: bool = True,
) -> dict[str, Any]:
    """Get today's failing interop jobs with related Jira tickets.

    Args:
        sippy: Sippy client instance
        jira: Jira client instance
        config: Watcher configuration
        release: Release version (e.g., '4.19')
        max_pass_percentage: Threshold for failing jobs (default: 90%)
        include_tickets: Whether to search for related tickets

    Returns:
        {
            "release": "4.20",
            "failing_jobs": [
                {
                    "name": "periodic-ci-...",
                    "pass_percentage": 75.0,
                    "related_tickets": ["LPINTEROP-1234"],
                    "variants": ["Platform:aws", ...],
                }
            ],
            "unassigned_ticket_count": 3,
            "summary": "5 failing jobs, 3 with tickets, 3 unassigned tickets"
        }
    """
    # Get failing interop jobs
    failing_jobs = sippy.get_interop_jobs(
        release,
        patterns=config.interop_patterns,
        max_pass_percentage=max_pass_percentage,
    )

    # Process each job
    job_results = []
    jobs_with_tickets = 0

    for job in failing_jobs:
        job_name = job.get("name", "")
        job_data = {
            "name": job_name,
            "pass_percentage": job.get("current_pass_percentage", 0),
            "previous_pass_percentage": job.get("previous_pass_percentage"),
            "variants": job.get("variants", []),
            "related_tickets": [],
        }

        # Search for related tickets if enabled
        if include_tickets and jira.token:
            short_name = extract_job_short_name(job_name)
            # Search for tickets mentioning this job
            jql = f'project = {config.jira_project} AND (summary ~ "{short_name}" OR description ~ "{job_name}")'
            try:
                tickets = jira.search_issues(jql, max_results=5)
                job_data["related_tickets"] = [t["key"] for t in tickets]
                if tickets:
                    jobs_with_tickets += 1
            except Exception:
                # Jira search failed, continue without tickets
                pass

        job_results.append(job_data)

    # Count unassigned tickets
    unassigned_count = 0
    if include_tickets and jira.token:
        labels_jql = " OR ".join(f'labels = "{label}"' for label in config.jira_labels)
        jql = f"project = {config.jira_project} AND assignee IS EMPTY AND ({labels_jql})"
        try:
            unassigned = jira.search_issues(jql, max_results=100)
            unassigned_count = len(unassigned)
        except Exception:
            pass

    # Build summary
    total_jobs = len(job_results)
    summary_parts = [f"{total_jobs} failing interop jobs"]
    if include_tickets:
        summary_parts.append(f"{jobs_with_tickets} with existing tickets")
        summary_parts.append(f"{unassigned_count} unassigned tickets")

    return {
        "release": release,
        "max_pass_percentage": max_pass_percentage,
        "failing_jobs": job_results,
        "jobs_with_tickets": jobs_with_tickets,
        "unassigned_ticket_count": unassigned_count,
        "summary": ", ".join(summary_parts),
    }
