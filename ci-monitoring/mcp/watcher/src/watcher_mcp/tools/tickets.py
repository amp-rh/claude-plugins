"""Ticket management tools for watcher workflows."""

from typing import Any

from ..clients.jira import JiraClient
from ..config import WatcherConfig


async def watcher_unassigned_tickets(
    jira: JiraClient,
    config: WatcherConfig,
    *,
    labels: list[str] | None = None,
    created_after: str | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """Get unassigned LPINTEROP tickets for current watcher period.

    Args:
        jira: Jira client instance
        config: Watcher configuration
        labels: Specific labels to filter by (default: use config labels)
        created_after: Only tickets created after this date (e.g., '-7d', '2026-01-01')
        max_results: Maximum number of tickets to return

    Returns:
        {
            "tickets": [
                {
                    "key": "LPINTEROP-123",
                    "summary": "Job failure: ...",
                    "labels": ["4.20-lp"],
                    "created": "2026-01-05T...",
                    "status": "Open"
                }
            ],
            "total": 5,
            "jql": "project = LPINTEROP AND ..."
        }
    """
    # Build label filter
    filter_labels = labels if labels else config.jira_labels
    labels_jql = " OR ".join(f'labels = "{label}"' for label in filter_labels)

    # Build JQL
    jql_parts = [
        f"project = {config.jira_project}",
        "assignee IS EMPTY",
        f"({labels_jql})",
    ]

    if created_after:
        jql_parts.append(f"created >= {created_after}")

    jql = " AND ".join(jql_parts)
    jql += " ORDER BY created DESC"

    # Execute search
    issues = jira.search_issues(
        jql,
        fields=["key", "summary", "status", "labels", "created", "priority"],
        max_results=max_results,
    )

    # Format results
    tickets = []
    for issue in issues:
        fields = issue.get("fields", {})
        tickets.append({
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "status": fields.get("status", {}).get("name"),
            "labels": fields.get("labels", []),
            "created": fields.get("created"),
            "priority": fields.get("priority", {}).get("name"),
        })

    return {
        "tickets": tickets,
        "total": len(tickets),
        "jql": jql,
    }


async def watcher_self_assign(
    jira: JiraClient,
    config: WatcherConfig,
    *,
    issue_key: str,
    add_watcher_label: bool = True,
    comment: str | None = None,
) -> dict[str, Any]:
    """Self-assign ticket and optionally add watcher label.

    Args:
        jira: Jira client instance
        config: Watcher configuration
        issue_key: Jira issue key (e.g., 'LPINTEROP-123')
        add_watcher_label: Whether to add 'watcher' label
        comment: Optional comment to add after assignment

    Returns:
        {
            "issue_key": "LPINTEROP-123",
            "assigned_to": "user@redhat.com",
            "label_added": true,
            "comment_added": true
        }
    """
    # Get current user
    myself = jira.get_myself()
    user_name = myself.get("name") or myself.get("key")
    user_display = myself.get("displayName", user_name)

    # Assign the issue
    jira.assign_issue(issue_key, user_name)

    result = {
        "issue_key": issue_key,
        "assigned_to": user_display,
        "label_added": False,
        "comment_added": False,
    }

    # Add watcher label if requested
    if add_watcher_label:
        try:
            jira.update_labels(issue_key, add=["watcher"])
            result["label_added"] = True
        except Exception:
            # Label update failed, continue
            pass

    # Add comment if provided
    if comment:
        try:
            jira.add_comment(issue_key, comment)
            result["comment_added"] = True
        except Exception:
            pass

    return result


async def watcher_ticket_details(
    jira: JiraClient,
    config: WatcherConfig,
    *,
    issue_key: str,
) -> dict[str, Any]:
    """Get detailed information about a specific ticket.

    Args:
        jira: Jira client instance
        config: Watcher configuration
        issue_key: Jira issue key (e.g., 'LPINTEROP-123')

    Returns:
        Full issue details including description, comments count, etc.
    """
    issue = jira.get_issue(
        issue_key,
        fields=["summary", "description", "status", "assignee", "labels", "created", "updated", "priority", "comment"],
    )

    fields = issue.get("fields", {})
    comments = fields.get("comment", {}).get("comments", [])

    return {
        "key": issue.get("key"),
        "summary": fields.get("summary"),
        "description": fields.get("description"),
        "status": fields.get("status", {}).get("name"),
        "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
        "labels": fields.get("labels", []),
        "priority": fields.get("priority", {}).get("name"),
        "created": fields.get("created"),
        "updated": fields.get("updated"),
        "comment_count": len(comments),
        "last_comment": comments[-1].get("body")[:200] if comments else None,
    }
