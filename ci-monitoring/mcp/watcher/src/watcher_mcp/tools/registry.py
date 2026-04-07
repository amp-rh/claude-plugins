"""Tool registration and dispatch for watcher-mcp."""

from typing import Any

from mcp.types import Tool

from ..clients.jira import JiraClient
from sippy_mcp.client import SippyClient
from ..config import WatcherConfig
from .tickets import watcher_self_assign, watcher_ticket_details, watcher_unassigned_tickets
from .triage import watcher_daily_triage

# Tool definitions
TOOLS: list[Tool] = [
    Tool(
        name="watcher_daily_triage",
        description="Get today's failing interop jobs with related Jira tickets. Combines Sippy job data with LPINTEROP ticket search for watcher triage.",
        inputSchema={
            "type": "object",
            "properties": {
                "release": {
                    "type": "string",
                    "description": "Release version (e.g., '4.19', '4.20')",
                },
                "max_pass_percentage": {
                    "type": "number",
                    "description": "Threshold for failing jobs (default: 90%)",
                    "default": 90.0,
                },
                "include_tickets": {
                    "type": "boolean",
                    "description": "Whether to search for related Jira tickets (default: true)",
                    "default": True,
                },
            },
            "required": ["release"],
        },
    ),
    Tool(
        name="watcher_unassigned_tickets",
        description="Get unassigned LPINTEROP tickets for current watcher period. Filters by configured labels (4.19-lp, 4.20-lp, opp-aws-lp, rosa-hcp-lp).",
        inputSchema={
            "type": "object",
            "properties": {
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific labels to filter by (default: use configured labels)",
                },
                "created_after": {
                    "type": "string",
                    "description": "Only tickets created after this date (e.g., '-7d', '2026-01-01')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of tickets to return (default: 50)",
                    "default": 50,
                },
            },
        },
    ),
    Tool(
        name="watcher_self_assign",
        description="Self-assign a ticket to the current user and optionally add 'watcher' label. For watcher taking ownership of a ticket.",
        inputSchema={
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "Jira issue key (e.g., 'LPINTEROP-123')",
                },
                "add_watcher_label": {
                    "type": "boolean",
                    "description": "Whether to add 'watcher' label (default: true)",
                    "default": True,
                },
                "comment": {
                    "type": "string",
                    "description": "Optional comment to add after assignment",
                },
            },
            "required": ["issue_key"],
        },
    ),
    Tool(
        name="watcher_ticket_details",
        description="Get detailed information about a specific LPINTEROP ticket including description and recent comments.",
        inputSchema={
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "Jira issue key (e.g., 'LPINTEROP-123')",
                },
            },
            "required": ["issue_key"],
        },
    ),
]


async def call_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    sippy: SippyClient,
    jira: JiraClient,
    config: WatcherConfig,
) -> dict[str, Any]:
    """Dispatch tool call to appropriate handler.

    Args:
        name: Tool name
        arguments: Tool arguments
        sippy: Sippy client instance
        jira: Jira client instance
        config: Watcher configuration

    Returns:
        Tool result as dictionary
    """
    if name == "watcher_daily_triage":
        return await watcher_daily_triage(
            sippy,
            jira,
            config,
            release=arguments["release"],
            max_pass_percentage=arguments.get("max_pass_percentage", 90.0),
            include_tickets=arguments.get("include_tickets", True),
        )

    elif name == "watcher_unassigned_tickets":
        return await watcher_unassigned_tickets(
            jira,
            config,
            labels=arguments.get("labels"),
            created_after=arguments.get("created_after"),
            max_results=arguments.get("max_results", 50),
        )

    elif name == "watcher_self_assign":
        return await watcher_self_assign(
            jira,
            config,
            issue_key=arguments["issue_key"],
            add_watcher_label=arguments.get("add_watcher_label", True),
            comment=arguments.get("comment"),
        )

    elif name == "watcher_ticket_details":
        return await watcher_ticket_details(
            jira,
            config,
            issue_key=arguments["issue_key"],
        )

    else:
        raise ValueError(f"Unknown tool: {name}")
