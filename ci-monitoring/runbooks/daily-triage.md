# Daily Triage Runbook

Step-by-step workflow for daily HCP/OPP watcher duties.

## Prerequisites

- Access to Sippy and Prow dashboards
- Jira access with LPINTEROP project permissions
- Slack access to team channels

## Daily Workflow

### Step 0: Activate MCP Servers (Agents Only)

**⚠️ Required before starting triage.** Agents must activate the watcher MCP servers to access Sippy and Jira programmatically:

```bash
./mcp/profiles/activate-watcher.sh
```

Then reload Cursor window (`Cmd/Ctrl+Shift+P` → `Developer: Reload Window`).

This provides:
- `sippy_get_jobs`, `sippy_get_failing_jobs`, `sippy_get_hypershift_jobs` — CI job data
- `jira_search`, `jira_get_issue`, `jira_update_issue` — Ticket management

→ See @../../../skills/sippy-mcp/SKILL.md for full tool reference.

### Step 1: Check Sippy for New Job Results

**For agents:** Use `sippy_get_jobs(release="4.19")` and `sippy_get_failing_jobs(release="4.19")`.

**For humans:**
1. Open [Sippy](https://sippy.dptools.openshift.org/)
2. Filter to OPP/HCP jobs
3. Note any new completions since last check
4. Record pass/fail status

**Trigger days:**
- **Monday**: OPP AWS (OCP 4.19, 4.20)
- **Wednesday**: ROSA HCP

### Step 2: Review Prow for Failed Job Logs

For each failed job:
1. Open [Prow](https://prow.ci.openshift.org/)
2. Find the failed job
3. Review the logs to identify:
   - Which step failed
   - Error messages
   - Timestamps
4. Save relevant log excerpts for ticket updates

### Step 3: Check Kanban Boards for Unassigned Tickets

1. Open AWS IPI Kanban board
2. Open ROSA HCP Kanban board
3. Look for tickets with no assignee
4. Self-assign any unassigned tickets for your rotation

### Step 4: Classify Failures

For each failure, determine root cause:

| Classification | Owner | Next Step |
|---------------|-------|-----------|
| **Infrastructure/Interop** | MPIIT | Retrigger + track |
| **Product Bug** | PQE Team | Engage stakeholder |
| **Transient/Flaky** | MPIIT | Retrigger with label |

See @failure-classification.md for detailed decision tree.

### Step 5: Retrigger Transient Failures

For infra/transient failures:
1. Manually retrigger the job
2. Add `retrigger` label to Jira ticket
3. Add comment explaining retrigger reason

See @retrigger-protocol.md for detailed steps.

### Step 6: Engage PQE Teams for Product Bugs

For confirmed product issues:
1. Update Jira ticket with findings
2. Add relevant log excerpts
3. Ping responsible PQE team in Slack
4. Link Slack thread to ticket

See @../slack-channels.md for channel reference.

### Step 7: Update Tracking Spreadsheet

1. Open Test Tracker Spreadsheet
2. Update run status for today's jobs
3. Add notes for any special circumstances

## End of Day Checklist

- [ ] All new failures triaged
- [ ] Retriggers completed for transient failures
- [ ] PQE teams pinged for product bugs
- [ ] Tracking spreadsheet updated
- [ ] Daily log entry created

## Related

- @failure-classification.md — Classification decision tree
- @retrigger-protocol.md — Retrigger steps
- @../dashboards.md — Dashboard links
- @../slack-channels.md — Communication channels
