# CI Monitoring Plugin

MCP-based CI monitoring infrastructure for OpenShift interop testing. This plugin bundles MCP servers, agent skills, and operational runbooks for both Cursor and Claude Code.

## Quick Navigation

| Resource | Path | Purpose |
|----------|------|---------|
| Cursor manifest | `.cursor-plugin/plugin.json` | Plugin registration |
| Claude entry | `.claude/CLAUDE.md` | Claude Code context |
| Sippy MCP | `mcp/sippy/AGENTS.md` | CI job health monitoring |
| Watcher MCP | `mcp/watcher/AGENTS.md` | Combined triage surface |
| Loki MCP | `mcp/loki/AGENTS.md` | Log queries and investigation |

## Skills

| Skill | Path | When to use |
|-------|------|-------------|
| ROSA HCP Triage | `skills/rosa-hcp-triage/SKILL.md` | Wednesday ROSA HCP triage rotation |
| Watcher Spreadsheet | `skills/watcher-spreadsheet/SKILL.md` | Reading watcher status spreadsheet |
| Sippy MCP Usage | `skills/sippy-mcp/SKILL.md` | Querying Sippy for job health |
| Loki MCP Usage | `skills/loki-mcp/SKILL.md` | Running LogQL queries |
| Watcher MCP Usage | `skills/watcher-mcp/SKILL.md` | Daily triage with combined tools |

## Agents

| Agent | Path | Role |
|-------|------|------|
| Sippy Interop Jobs | `agents/sippy-interop-jobs.md` | Query job status across releases |
| Spreadsheet Updater | `agents/spreadsheet-updater.md` | Gated spreadsheet updates |

## Commands

| Command | Path |
|---------|------|
| Analyze Prow Logs | `commands/analyze-prow-logs.md` |
| Orchestrate | `commands/orchestrate.md` |

## Rules

| Rule | Path | Scope |
|------|------|-------|
| MCP Tool Expansion | `rules/mcp-tool-expansion.mdc` | Conditional: `mcp/**/*.py` |
| Subagent Authoring | `rules/subagent-authoring.mdc` | Always apply |

## Runbooks

Operational procedures under `runbooks/`:
- `daily-triage.md` - Daily monitoring workflow
- `failure-classification.md` - Failure classification guide
- `retrigger-protocol.md` - Job retrigger procedures
- `aws-cleanup.md` - AWS resource cleanup
- `aws-quota-analysis.md` - Quota investigation with Loki

## Architecture

The plugin integrates three MCP servers that provide data to agent-driven triage workflows:

```
Sippy API ──> [Sippy MCP] ──┐
                             ├──> [Watcher MCP] ──> Agent Skills ──> Triage Reports
Jira API  ──> [Jira Client] ─┘                       │
                                                      ├── rosa-hcp-triage (orchestrator)
Loki API  ──> [Loki MCP] ────────────────────────────┘   ├── per-lp-triage (subagent)
                                                          ├── jira-ops (subagent)
                                                          └── spreadsheet-updater (agent)
```

## External Dependencies

- `firefox-browser` skill (not bundled): Required by `spreadsheet-updater` for authenticated Google Sheets sessions
- 1Password CLI (`op`): Used by `jira-ops` for Jira PAT retrieval
