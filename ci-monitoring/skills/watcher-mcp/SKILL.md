# Watcher MCP Skill

Agent-facing guide for using the watcher-mcp server for HCP/OPP triage workflows.

## Quick Reference

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `watcher_daily_triage` | Get failing jobs + related tickets | Start of triage session |
| `watcher_unassigned_tickets` | List unassigned tickets | Find work to pick up |
| `watcher_self_assign` | Claim a ticket | Taking ownership |
| `watcher_ticket_details` | Get full ticket info | Before investigating |

## Common Workflows

### Daily Triage Start

```
1. Call watcher_daily_triage(release="4.20")
2. Review failing_jobs list
3. Check which jobs have related_tickets
4. Note unassigned_ticket_count
```

### Picking Up Work

```
1. Call watcher_unassigned_tickets()
2. Review ticket list
3. Call watcher_ticket_details(issue_key="LPINTEROP-XXX") for context
4. Call watcher_self_assign(issue_key="LPINTEROP-XXX") to claim
```

### Handoff Preparation

```
1. Call watcher_daily_triage(release="4.20") for current state
2. Note any tickets you worked on
3. Check watcher_unassigned_tickets() for remaining work
4. Document in handoff notes
```

## Tool Parameters

### watcher_daily_triage

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `release` | string | Yes | - | Release version (e.g., '4.19', '4.20') |
| `max_pass_percentage` | number | No | 90 | Threshold for "failing" jobs |
| `include_tickets` | boolean | No | true | Search for related Jira tickets |

**Example:**

```json
{
  "release": "4.20",
  "max_pass_percentage": 85,
  "include_tickets": true
}
```

### watcher_unassigned_tickets

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `labels` | array | No | config | Labels to filter by |
| `created_after` | string | No | - | Date filter (e.g., '-7d') |
| `max_results` | integer | No | 50 | Max tickets to return |

**Example:**

```json
{
  "labels": ["4.20-lp", "opp-aws-lp"],
  "created_after": "-3d"
}
```

### watcher_self_assign

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `issue_key` | string | Yes | - | Jira issue key |
| `add_watcher_label` | boolean | No | true | Add 'watcher' label |
| `comment` | string | No | - | Comment to add |

**Example:**

```json
{
  "issue_key": "LPINTEROP-123",
  "add_watcher_label": true,
  "comment": "Picking up for triage"
}
```

### watcher_ticket_details

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `issue_key` | string | Yes | - | Jira issue key |

## Interpreting Results

### Triage Output

```json
{
  "release": "4.20",
  "failing_jobs": [...],       // Jobs below pass threshold
  "jobs_with_tickets": 3,      // Jobs that already have tickets
  "unassigned_ticket_count": 5, // Tickets needing assignment
  "summary": "..."             // Human-readable summary
}
```

**Key indicators:**
- High `unassigned_ticket_count` → work to pick up
- Jobs without `related_tickets` → may need new tickets filed
- Low `pass_percentage` → severity indicator

### Ticket List Output

```json
{
  "tickets": [...],
  "total": 5,
  "jql": "..."  // JQL used (useful for manual verification)
}
```

## Prerequisites

1. **Jira token** must be configured (`JIRA_PERSONAL_TOKEN` environment variable)
2. **Server running** and configured in MCP client
3. **Reload Cursor** after starting server

## Building

```bash
cd mcp/watcher && podman build -t watcher-mcp:latest .
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tools not visible | Reload Cursor window |
| Jira errors | Check server logs for auth issues |
| No jobs returned | Verify release version exists |
| Empty ticket list | Check label filters match config |

## Related

- @../../mcp/watcher/AGENTS.md — Server documentation
- @../sippy-mcp/SKILL.md — Sippy MCP (CI jobs only)
