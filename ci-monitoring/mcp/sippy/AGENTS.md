---
type: resource
parent: @../AGENTS.md
status: active
tags: [mcp, sippy, ci-monitoring]
---

# Sippy MCP Server

MCP server for Sippy CI job monitoring.

**Parent**: @../AGENTS.md

## Quick Start

```bash
podman build -t sippy-mcp:latest .
```

## Available Tools

| Tool | Description |
|------|-------------|
| `sippy_get_releases` | List available OpenShift releases with metadata |
| `sippy_get_jobs` | Get all CI jobs for a release |
| `sippy_get_health` | Get release health indicators |
| `sippy_get_tests` | Get test results for a release |
| `sippy_search_jobs` | Search jobs with flexible filters |
| `sippy_get_hypershift_jobs` | Get ROSA HCP/Hypershift jobs |
| `sippy_get_failing_jobs` | Get jobs below pass threshold |

## Files

| File | Purpose |
|------|---------|
| `api-discovery.md` | Sippy API documentation |
| `pyproject.toml` | Python package configuration |
| `src/sippy_mcp/` | Package source code |
| `Dockerfile` | Container build file |

## Development

```bash
# Install locally for development
pip install -e .

# Run directly
sippy-mcp
```

## API Reference

See @api-discovery.md for full Sippy API documentation.

## Related

- @../AGENTS.md — MCP server management
- @../../skills/sippy-mcp/SKILL.md — Usage guide
