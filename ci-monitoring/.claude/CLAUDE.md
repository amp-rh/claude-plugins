# CLAUDE.md

This directory is a CI monitoring plugin providing MCP servers, agent definitions, and operational skills for OpenShift interop CI triage.

## Repository Structure

- `mcp/sippy/` - Sippy MCP server (CI job health, pass rates, failing jobs)
- `mcp/watcher/` - Watcher MCP server (combined Sippy + Jira triage surface)
- `mcp/loki/` - Loki MCP server (Observatorium log queries, AWS quota analysis)
- `skills/` - Agent skills for triage workflows and MCP usage
- `agents/` - Cursor agent definitions
- `.claude/agents/` - Claude Code agent definitions
- `commands/` - Slash commands for Prow log analysis and workflow orchestration
- `rules/` - Cursor rules for MCP expansion and subagent delegation
- `runbooks/` - Operational procedures for watcher rotation duties

## MCP Servers

Each server under `mcp/` is a standalone Python package installable via `pip install -e .` with a console script entry point. Servers communicate over stdio using the Model Context Protocol.

| Server | Install | Run |
|--------|---------|-----|
| Sippy | `cd mcp/sippy && pip install -e .` | `sippy-mcp` |
| Watcher | `cd mcp/watcher && pip install -e .` | `watcher-mcp` |
| Loki | `cd mcp/loki && pip install -e .` | `loki-mcp` |

## Sub-Agents

Claude-format agent definitions live in `.claude/agents/`:

- `sippy-interop-jobs.md` - Queries Sippy REST API for interop job status
- `spreadsheet-updater.md` - Manages watcher spreadsheet updates with approval gates

## Key Skills

- `skills/rosa-hcp-triage/SKILL.md` - Full ROSA HCP triage orchestrator
- `skills/watcher-spreadsheet/SKILL.md` - Google Sheets integration for status tracking

## Runbooks

Operational procedures under `runbooks/` cover daily triage, failure classification, retriggering, and AWS cleanup.
