# CI Monitoring Plugin

MCP-based CI monitoring infrastructure for OpenShift interop job health, agent-driven triage workflows, and watcher rotation automation. Compatible with both Cursor and Claude Code.

## Components

### MCP Servers

Three Model Context Protocol servers provide programmatic access to CI monitoring data:

| Server | Purpose | Entry point |
|--------|---------|-------------|
| **sippy** | OpenShift CI job health, pass rates, failing jobs, hypershift filtering | `mcp/sippy/` |
| **watcher** | Combined Sippy + Jira triage surface with daily triage tool | `mcp/watcher/` |
| **loki** | Observatorium log queries (LogQL), AWS quota analysis, failure investigation | `mcp/loki/` |

Each server is a standalone Python package with its own `pyproject.toml` and `Dockerfile`.

### Skills

| Skill | Purpose |
|-------|---------|
| `rosa-hcp-triage` | Full ROSA HCP triage orchestrator: spreadsheet read, Sippy batch, parallel per-LP subagents, Jira ops, HTML report |
| `watcher-spreadsheet` | Google Sheets integration via gviz CSV API for watcher status tracking |
| `sippy-mcp` | Agent usage guide for Sippy MCP tools |
| `loki-mcp` | Agent usage guide for Loki MCP tools |
| `watcher-mcp` | Agent usage guide for Watcher MCP tools |

### Agents

| Agent | Purpose |
|-------|---------|
| `sippy-interop-jobs` | Query Sippy REST API for interop job status across releases |
| `spreadsheet-updater` | Dedicated agent for watcher spreadsheet updates with draft/approve gates |

### Commands

| Command | Purpose |
|---------|---------|
| `analyze-prow-logs` | Fetch and analyze Prow build logs for failure classification |
| `orchestrate` | Multi-step workflow orchestration with MCP server activation |

### Runbooks

Operational procedures for watcher rotation duties:

- `daily-triage.md` - Daily monitoring workflow
- `failure-classification.md` - How to classify CI failures
- `retrigger-protocol.md` - When and how to retrigger jobs
- `aws-cleanup.md` - AWS resource cleanup procedures
- `aws-quota-analysis.md` - AWS quota investigation using Loki

## Setup

### MCP Servers

Each server can be installed locally or run as a container:

```bash
# Local install (any server)
cd mcp/sippy && pip install -e .
sippy-mcp  # starts stdio MCP server

# Container
cd mcp/sippy && docker build -t sippy-mcp .
```

### Environment Variables

| Variable | Server | Purpose |
|----------|--------|---------|
| `SIPPY_URL` | sippy, watcher | Sippy API base URL |
| `JIRA_URL` | watcher | Jira instance URL |
| `JIRA_PERSONAL_TOKEN` | watcher | Jira API bearer token |
| `LOKI_CLIENT_ID` | loki | OAuth client ID for Observatorium |
| `LOKI_CLIENT_SECRET` | loki | OAuth client secret for Observatorium |
| `WATCHER_SPREADSHEET_ID` | skills | Google Sheets spreadsheet ID |

## Platform Compatibility

### Cursor

The `.cursor-plugin/plugin.json` manifest registers agents, skills, commands, and rules with Cursor's plugin system.

### Claude Code

The `.claude/` directory provides Claude Code compatibility:
- `CLAUDE.md` - Project context and navigation
- `settings.json` - WebFetch domain permissions
- `agents/` - Sub-agent definitions with YAML frontmatter

## License

Apache-2.0
