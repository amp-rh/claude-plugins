# Orchestrate

Create and run an async task orchestrator that breaks down complex tasks into subagent invocations with proper context.

## Quick Reference

| Mode | Command | Writes |
|------|---------|--------|
| **Read-only** (default) | `/orchestrate <task>` | ❌ Blocked, returned as drafts |
| **Write-enabled** | `/orchestrate --allow-writes <task>` | ✅ Allowed, but drafts shown first |

## Usage

```
/orchestrate <task description>
/orchestrate --allow-writes <task description>
```

## Safety Mode (Default)

By default, the orchestrator operates in **read-only mode**:

- ✅ **Allowed**: Read, Glob, Search, List, Get operations
- ❌ **Blocked**: Write, Update, Create, Delete, Transition operations
- 📝 **Drafts**: Any intended writes are returned as drafts for approval

### Read-Only Tool Patterns

| MCP Server | Allowed (Read) | Blocked (Write) |
|------------|----------------|-----------------|
| **Jira** | `jira_search`, `jira_get_issue`, `jira_get_transitions` | `jira_update_issue`, `jira_create_issue`, `jira_transition_issue`, `jira_add_comment` |
| **GitHub** | `get_*`, `list_*`, `search_*`, `pull_request_read` | `create_*`, `update_*`, `merge_*`, `push_*`, `issue_write` |
| **Local** | `Read`, `Glob`, `Grep`, `LS` | `Write`, `StrReplace`, `Delete`, `Shell` (write commands) |

### Write Mode

To enable writes, explicitly add `--allow-writes`:
```
/orchestrate --allow-writes update all ticket statuses
```

Even with writes enabled, the orchestrator will:
1. Show a draft of all intended changes
2. Wait for your approval before executing
3. Execute only approved changes

## What This Command Does

1. **Analyzes the task** and breaks it into discrete subtasks
2. **Gathers workspace context** (ACTIVE.md, relevant AGENTS.md files)
3. **Creates subagent prompts** with safety constraints
4. **Submits tasks asynchronously** using the task runner
5. **Reports task IDs** for tracking
6. **Aggregates results** and drafts any writes for approval

## Context Injection

Each subagent receives:
- The specific subtask prompt
- **Safety constraints** (read-only unless --allow-writes)
- Relevant workspace context (paths, conventions)
- MCP tool access (Jira, GitHub, etc.)
- Output format requirements (JSON for structured data)

## Instructions

When the user invokes `/orchestrate`:

### Step 1: Analyze the Task

Break the user's request into discrete, parallelizable subtasks. For example:

**User**: "Update all sprint tickets with their PR status"

**Subtasks**:
1. List all sprint tickets
2. For each ticket, fetch PR status
3. Analyze which need updates
4. Generate update report

### Step 2: Gather Context

Read relevant context files:
```bash
# Current session context
cat /home/amp/cursor_agent/ACTIVE.md

# Sprint context (if relevant)
cat /home/amp/cursor_agent/sprint/AGENTS.md
```

Extract key information:
- Current focus items
- Cross-cutting concerns
- Relevant ticket/PR references

### Step 3: Generate Subagent Prompts

For each subtask, create a prompt that includes the **safety constraints**:

```markdown
## Task
<specific subtask>

## CRITICAL: Safety Constraints

You are operating in READ-ONLY mode. You MUST follow these rules:

### Allowed Tools (Read Operations)
- Jira: jira-jira_search, jira-jira_get_issue, jira-jira_get_transitions, jira-jira_get_project_issues
- GitHub: github-get_*, github-list_*, github-search_*, github-pull_request_read
- Local: Read, Glob, Grep, LS, SemanticSearch

### BLOCKED Tools (Write Operations) - DO NOT USE
- Jira: jira-jira_update_issue, jira-jira_create_issue, jira-jira_transition_issue, jira-jira_add_comment, jira-jira_add_worklog
- GitHub: github-create_*, github-update_*, github-merge_*, github-push_*, github-issue_write, github-pull_request_review_write
- Local: Write, StrReplace, Delete, Shell (for write commands)

### If You Need to Write
If your task requires a write operation:
1. DO NOT execute the write
2. Instead, return a draft in your output:

```json
{
  "success": true,
  "data": { ... read results ... },
  "pending_writes": [
    {
      "tool": "jira-jira_update_issue",
      "target": "INTEROP-8496",
      "action": "transition to Done",
      "draft": { "issue_key": "INTEROP-8496", "fields": {"status": "Done"} }
    }
  ]
}
```

The orchestrator will collect these drafts and present them for human approval.

## Context
- Workspace: /home/amp/cursor_agent
- Current sprint: <from ACTIVE.md>
- Relevant tickets: <if applicable>

## Output Format
Return JSON with structure:
{
  "success": boolean,
  "data": <result>,
  "pending_writes": [],  // Any writes that need approval
  "errors": []
}
```

### For --allow-writes Mode

If the orchestrator was invoked with `--allow-writes`, modify the safety section:

```markdown
## Safety Mode: WRITES ENABLED

You may use write tools, but you MUST:
1. Return a draft of ALL writes you intend to make
2. Wait for the aggregation phase
3. The human will approve before execution

Still prefer read operations when possible. Only write when necessary for the task.
```

### Step 4: Submit Tasks

Use the task runner to submit each subtask:

```bash
TASK_RUNNER="/home/amp/cursor_agent/skills/agentic-workflows/scripts/task-runner"

# Submit each subtask
$TASK_RUNNER submit "<subagent prompt 1>"
$TASK_RUNNER submit "<subagent prompt 2>"
# etc.
```

### Step 5: Report Status

Return a summary:

```markdown
## Orchestration Started

**Task**: <original task>
**Subtasks**: <count>

| # | Subtask | Task ID | Status |
|---|---------|---------|--------|
| 1 | List sprint tickets | abc123 | submitted |
| 2 | Fetch PR status | def456 | submitted |
| 3 | Analyze updates | ghi789 | submitted |

**Check progress**: 
- `task list` - see all tasks
- `task result <id>` - get specific result

**When all complete**, ask me to aggregate the results.
```

## Example Orchestrations

### Example 1: Sprint Status Report (Read-Only)

**User**: `/orchestrate generate a sprint status report`

**Mode**: Read-only (default)

**Subtasks**:
1. Fetch all sprint tickets from Jira (read)
2. Fetch PR status for each ticket (read)
3. Identify blocked items (analysis)
4. Generate summary (no writes needed)

**Result**: Report with no pending writes.

### Example 2: Sync Tickets with PRs (Writes Needed)

**User**: `/orchestrate sync INTEROP tickets with their GitHub PRs`

**Mode**: Read-only (default) — writes become drafts

**Subtasks**:
1. List INTEROP tickets assigned to me (read)
2. For each, find linked PRs (read)
3. Compare status (ticket vs PR) (analysis)
4. **Draft updates for mismatches** (pending writes)

**Result**:
```
## Sync Analysis

| Ticket | Status | PR Status | Action Needed |
|--------|--------|-----------|---------------|
| INTEROP-8612 | In Progress | merged | Transition to Done |
| INTEROP-8613 | New | open | No action |

## ⚠️ Pending Writes (1)

| Target | Action |
|--------|--------|
| INTEROP-8612 | Transition to Done |

Reply "approve all" to execute.
```

### Example 3: Explicit Write Mode

**User**: `/orchestrate --allow-writes update all merged PR tickets to Done`

**Mode**: Writes enabled, but still drafts first

**Flow**:
1. Find tickets with merged PRs (read)
2. Generate transition drafts (draft)
3. Present drafts for approval
4. Execute approved writes

### Example 4: PR Review Batch (Read-Only)

**User**: `/orchestrate review all open PRs in openshift/release for my tickets`

**Subtasks**:
1. List my open PRs (read)
2. For each PR, get diff and CI status (read)
3. Analyze each for issues (analysis)
4. Compile review notes (no writes)

**Result**: Review notes, no pending writes.

## Aggregating Results

When user asks to aggregate, collect all task results:

```bash
TASK_RUNNER="/home/amp/cursor_agent/skills/agentic-workflows/scripts/task-runner"

# Get all results
$TASK_RUNNER result <id1>
$TASK_RUNNER result <id2>
# etc.
```

Then synthesize into a cohesive response.

### Handling Pending Writes

If any subagent returned `pending_writes`, present them for approval:

```markdown
## Aggregated Results

<summary of read data>

---

## ⚠️ Pending Writes (Require Approval)

The following write operations were requested but NOT executed:

| # | Target | Action | Tool |
|---|--------|--------|------|
| 1 | INTEROP-8496 | Transition to Done | jira-jira_transition_issue |
| 2 | INTEROP-8612 | Add comment: "PR merged" | jira-jira_add_comment |

### Draft Details

**Write 1: INTEROP-8496**
```json
{
  "issue_key": "INTEROP-8496",
  "transition_id": "31",
  "comment": "All PRs merged, closing ticket"
}
```

**Write 2: INTEROP-8612**
```json
{
  "issue_key": "INTEROP-8612",
  "comment": "PR #72017 merged on Dec 19"
}
```

---

**To approve**: Reply with "approve all" or "approve 1" / "approve 2"
**To modify**: Reply with changes, e.g., "modify 2: change comment to ..."
**To cancel**: Reply with "cancel" or "cancel 2"
```

### Executing Approved Writes

Once approved, submit write tasks:

```bash
$TASK_RUNNER submit "Execute this APPROVED write:
Tool: jira-jira_transition_issue
Parameters: {\"issue_key\": \"INTEROP-8496\", \"transition_id\": \"31\"}

You have EXPLICIT APPROVAL to execute this write. Do it now and return the result."
```

## MCP Server Activation

Before submitting subtasks, analyze which MCP servers are needed:

### Analysis Pattern

| Subtask Type | Required Servers | Toolsets |
|--------------|------------------|----------|
| Jira queries | jira | (all) |
| GitHub PR checks | github | repos, pull_requests |
| Code browsing | github | repos |
| Sprint sync | jira + github | all |
| Documentation | docs | (all) |
| Local file ops | (none) | - |

### Activation Steps

1. Verify MCP servers configured in client
2. Identify required servers for subtasks
3. Include server status in subtask context if needed
4. Remind user to reload Cursor if MCP configuration changed

### Server State in Prompts

When generating subagent prompts, include MCP context:

```markdown
## MCP Server Status
- jira: ✅ running
- github: ✅ running (toolsets: repos, pull_requests)

Available tools: jira_search, jira_get_issue, github-list_pull_requests, ...
```

## Context Files Reference

| Context | Path | What It Contains |
|---------|------|------------------|
| Session | `/home/amp/cursor_agent/ACTIVE.md` | Today's focus, cross-cutting concerns |
| Sprint | `/home/amp/cursor_agent/sprint/AGENTS.md` | Current tickets, PRs |
| PRs | `/home/amp/cursor_agent/sprint/prs/AGENTS.md` | PR tracking |
| Jira patterns | `/home/amp/cursor_agent/contexts/domain/jira.md` | Jira conventions |
| Metrics | `/home/amp/cursor_agent/contexts/domain/metrics.md` | Quality metrics |
| MCP servers | `/home/amp/cursor_agent/mcp/AGENTS.md` | Server configs and profiles |

## Task Runner Location

```
/home/amp/cursor_agent/skills/agentic-workflows/scripts/task-runner
```
