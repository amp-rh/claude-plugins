---
name: reflect
description: "Use when a session is ending or when reviewing all agents, skills, commands, and tool calls used in the current conversation for accuracy and efficiency improvements"
user-invocable: true
---

# Session Reflection

Comprehensive review of all agent, skill, and command usage in the current session.

## Workflow

### Phase 1: Session Inventory

Scan the full conversation above and catalog every:

- **Agent launch**: name, prompt summary, token/tool stats if visible, result quality
- **Skill invocation**: name, purpose, whether it was followed correctly
- **Command execution**: command name, arguments, outcome
- **Significant tool sequences**: repeated failed searches, redundant reads, verbose outputs

For each item record: name, purpose, inputs, outputs, tools used, token count if visible.

### Phase 2: Launch Session Reflector Agent

Dispatch the `session-reflector` agent via the Agent tool. Pass the full inventory as the prompt.

The reflector scores each item on 8 axes (1-5) and identifies improvements. It MUST find at least one improvement per item — even for perfect scores.

Wait for the reflector to return its structured report before proceeding.

### Phase 3: Categorize Improvements

Based on the reflector's report, categorize each improvement target:

| Path Pattern | Category | Action |
|---|---|---|
| `~/.claude/skills/*` | User-editable | Direct edit |
| `~/.claude/agents/*` | User-editable | Direct edit |
| `~/.claude/commands/*` | User-editable | Direct edit |
| `.claude/skills/*` (project) | Project-editable | Direct edit |
| `~/.claude/plugins/cache/*` | Marketplace (read-only) | GitHub issue |
| `${CLAUDE_PLUGIN_ROOT}/*` | This plugin | GitHub issue |
| No file / behavioral | Behavioral | Log to memory |

### Phase 4: Launch Improvement Implementer Agent

Dispatch the `improvement-implementer` agent with the categorized report. The implementer:

- Applies direct edits to user-owned files
- Files GitHub issues on `amp-rh/claude-code` for marketplace/read-only files
- Logs behavioral improvements to memory

Wait for the implementer to return before proceeding.

### Phase 5: Summary Report

Present to the user:

```
## Session Reflection Summary
- Items reviewed: N
- Improvements applied: N (list files edited)
- GitHub issues filed: N (list URLs)
- Behavioral recommendations: N

### Scores Overview
| Item | Accuracy | Efficiency | Approach | Tools | Prompt | Errors | Missed | Format |
|------|----------|-----------|----------|-------|--------|--------|--------|--------|
| ...  | ...      | ...       | ...      | ...   | ...    | ...    | ...    | ...    |
```

### Phase 6: Complete

Report done. Claude may now stop.
