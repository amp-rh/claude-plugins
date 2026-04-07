---
type: resource
parent: @../AGENTS.md
status: active
tags: [mcp, watcher, sippy, jira, hcp, opp]
---

# Watcher MCP Server

**Parent**: @../AGENTS.md

Unified MCP server for HCP/OPP Watcher triage workflows. Combines Sippy CI job monitoring with Jira ticket management in domain-specific tools.

## Quick Start

```bash
podman build -t watcher-mcp:latest mcp/watcher/
```

## Available Tools

| Tool | Description |
|------|-------------|
| `watcher_daily_triage` | Get failing interop jobs with related Jira tickets |
| `watcher_unassigned_tickets` | Get unassigned LPINTEROP tickets for watcher period |
| `watcher_self_assign` | Self-assign ticket and add watcher label |
| `watcher_ticket_details` | Get full ticket details with description and comments |

## Tool Details

### `watcher_daily_triage`

Get today's failing interop jobs with related Jira tickets.

**Parameters:**
- `release` (required): Release version (e.g., '4.19', '4.20')
- `max_pass_percentage`: Threshold for failing jobs (default: 90%)
- `include_tickets`: Whether to search for related Jira tickets (default: true)

**Returns:**
```json
{
  "release": "4.20",
  "failing_jobs": [
    {
      "name": "periodic-ci-openshift-interop-tests-main-opp-aws-4.20",
      "pass_percentage": 75.0,
      "related_tickets": ["LPINTEROP-1234"],
      "variants": ["Platform:aws", "Installer:opp"]
    }
  ],
  "jobs_with_tickets": 3,
  "unassigned_ticket_count": 5,
  "summary": "8 failing interop jobs, 3 with existing tickets, 5 unassigned tickets"
}
```

### `watcher_unassigned_tickets`

Get unassigned LPINTEROP tickets for current watcher period.

**Parameters:**
- `labels`: Specific labels to filter by (default: configured labels)
- `created_after`: Only tickets created after this date (e.g., '-7d')
- `max_results`: Maximum tickets to return (default: 50)

**Returns:**
```json
{
  "tickets": [
    {
      "key": "LPINTEROP-123",
      "summary": "Job failure: opp-aws-4.20",
      "status": "Open",
      "labels": ["4.20-lp", "opp-aws-lp"],
      "created": "2026-01-05T10:30:00.000Z",
      "priority": "Major"
    }
  ],
  "total": 5,
  "jql": "project = LPINTEROP AND ..."
}
```

### `watcher_self_assign`

Self-assign a ticket to the current user.

**Parameters:**
- `issue_key` (required): Jira issue key (e.g., 'LPINTEROP-123')
- `add_watcher_label`: Whether to add 'watcher' label (default: true)
- `comment`: Optional comment to add after assignment

**Returns:**
```json
{
  "issue_key": "LPINTEROP-123",
  "assigned_to": "John Doe",
  "label_added": true,
  "comment_added": false
}
```

### `watcher_ticket_details`

Get detailed information about a specific ticket.

**Parameters:**
- `issue_key` (required): Jira issue key (e.g., 'LPINTEROP-123')

**Returns:**
```json
{
  "key": "LPINTEROP-123",
  "summary": "Job failure: opp-aws-4.20",
  "description": "Full description text...",
  "status": "Open",
  "assignee": null,
  "labels": ["4.20-lp"],
  "priority": "Major",
  "created": "2026-01-05T10:30:00.000Z",
  "updated": "2026-01-06T14:00:00.000Z",
  "comment_count": 3,
  "last_comment": "Latest comment preview..."
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JIRA_PERSONAL_TOKEN` | Jira API token (required for ticket features) | - |
| `JIRA_URL` | Jira base URL | `https://issues.redhat.com` |
| `JIRA_PROJECT` | Default project | `LPINTEROP` |
| `SIPPY_URL` | Sippy API URL | `https://sippy.dptools.openshift.org` |
| `WATCHER_CONFIG_PATH` | Custom config file path | - |

### Config File (`config/default.yaml`)

```yaml
jira:
  url: https://issues.redhat.com
  project: LPINTEROP
  labels:
    - 4.19-lp
    - 4.20-lp
    - opp-aws-lp
    - rosa-hcp-lp

sippy:
  url: https://sippy.dptools.openshift.org
  releases:
    - "4.19"
    - "4.20"

job_patterns:
  interop:
    - "*interop*"
    - "*opp*"
    - "*lp-*"
  hcp:
    - "*hypershift*"
    - "*rosa-hcp*"
```

## Architecture

```
watcher-mcp/
├── config/
│   └── default.yaml         # Default configuration
└── src/watcher_mcp/
    ├── server.py            # MCP server entry point
    ├── config.py            # Config loading
    ├── clients/
    │   └── jira.py          # Jira REST client
    └── tools/
        ├── registry.py      # Tool definitions and dispatch
        ├── triage.py        # watcher_daily_triage
        └── tickets.py       # watcher_unassigned_tickets, watcher_self_assign
```

SippyClient is imported from the `sippy-mcp` package (shared dependency).

## Development

### Local Testing

```bash
podman build -t watcher-mcp:latest mcp/watcher/

podman run --rm -it \
  -e JIRA_PERSONAL_TOKEN="$JIRA_PERSONAL_TOKEN" \
  watcher-mcp:latest
```

### Adding New Tools

1. Implement function in `tools/triage.py` or `tools/tickets.py`
2. Add Tool definition to `TOOLS` list in `tools/registry.py`
3. Add dispatch case in `call_tool()` function
4. Update this documentation

## Related

- @../sippy/AGENTS.md — Standalone Sippy MCP server
- @../../skills/watcher-mcp/SKILL.md — Agent usage guide
