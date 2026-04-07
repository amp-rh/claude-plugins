---
type: resource
parent: @../AGENTS.md
status: active
tags: [mcp, loki, ci-logs, aws-analysis]
---

# Loki MCP Server

MCP server for querying Grafana Loki CI logs, with pre-built queries for AWS resource analysis.

**Parent**: @../AGENTS.md

## Quick Start

```bash
podman build -t loki-mcp:latest .
```

**Required environment variables:**
- `LOKI_CLIENT_ID` — OAuth client ID
- `LOKI_CLIENT_SECRET` — OAuth client secret

## Available Tools

### Core Query Tools

| Tool | Description |
|------|-------------|
| `loki_query` | Execute raw LogQL query |
| `loki_query_range` | Execute LogQL with time range |
| `loki_labels` | List available labels |
| `loki_label_values` | Get values for a label |

### Pre-built AWS Analysis Tools

| Tool | Description |
|------|-------------|
| `loki_aws_quota_errors` | Find AWS quota/limit exceeded errors |
| `loki_vpc_limit_errors` | Find VPC-specific limit errors |
| `loki_orphaned_vpcs` | Find deprovision failures (potential orphans) |
| `loki_node_availability` | Find node availability issues |
| `loki_ipi_install_failures` | Find IPI install VPC/network failures |
| `loki_mpiit_failures` | Find failures in MPIIT-scoped jobs |

## Authentication

This server uses OAuth2 client credentials flow to authenticate with Red Hat SSO:

1. **Get credentials**: Request LOKI_CLIENT_ID and LOKI_CLIENT_SECRET from Test Platform team
2. **Set environment variables** or pass to container

The token is automatically refreshed when expired.

## Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python package configuration |
| `src/loki_mcp/client.py` | Loki API client with OAuth2 |
| `src/loki_mcp/server.py` | MCP server implementation |
| `src/loki_mcp/queries.py` | Pre-built LogQL query templates |
| `Dockerfile` | Container build file |

## Development

```bash
# Install locally for development
pip install -e .

# Run directly (needs credentials in env)
export LOKI_CLIENT_ID=xxx
export LOKI_CLIENT_SECRET=xxx
loki-mcp
```

## LogQL Examples

### Find VPC Limit Errors
```logql
{job=~".*(lp-interop|konflux).*"} |~ "VpcLimitExceeded"
```

### Find Deprovision Failures
```logql
{job=~".*deprovision.*"} |~ "failed|error" |~ "vpc|VPC"
```

### Find All AWS Errors in MPIIT Jobs
```logql
{job=~".*(lp-interop|lp-rosa-hypershift|interop-opp|konflux).*"} 
  |~ "LimitExceeded|QuotaExceeded|InsufficientCapacity"
```

## Related

- @../AGENTS.md — MCP server management
- @../../skills/loki-mcp/SKILL.md — Usage guide
- @../../projects/hcp-opp-watcher/resources/aws-quota-failures/ — AWS error patterns
