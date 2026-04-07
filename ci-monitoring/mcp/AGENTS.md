---
type: directory
parent: @../AGENTS.md
status: active
tags: [mcp, ci-monitoring]
---

# MCP Servers

Three Model Context Protocol servers provide programmatic access to CI monitoring data.

| Server | Purpose | Path |
|--------|---------|------|
| **sippy** | OpenShift CI job health, pass rates, failing jobs | @sippy/AGENTS.md |
| **watcher** | Combined Sippy + Jira triage surface | @watcher/AGENTS.md |
| **loki** | Observatorium log queries, AWS quota analysis | @loki/AGENTS.md |

Each server is a standalone Python package with its own `pyproject.toml` and `Dockerfile`.

## Quick Start

```bash
cd mcp/<server> && pip install -e .
```

Or build containers:

```bash
cd mcp/<server> && podman build -t <server>-mcp:latest .
```
