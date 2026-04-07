---
name: sippy-mcp
description: Use the Sippy MCP server to monitor CI job status, test results, and release health for OpenShift.
---

# Sippy MCP Server

Guide for using the Sippy MCP server to monitor CI job status.

## Quick Reference

| Task | Tool | Key Parameters |
|------|------|----------------|
| List releases | `sippy_get_releases` | (none) |
| Get jobs for release | `sippy_get_jobs` | release |
| Get release health | `sippy_get_health` | release |
| Get test results | `sippy_get_tests` | release, limit |
| Search jobs | `sippy_search_jobs` | release, name_contains, variant_contains, min/max_pass_percentage |
| Get HCP jobs | `sippy_get_hypershift_jobs` | release |
| Get failing jobs | `sippy_get_failing_jobs` | release, max_pass_percentage |

## Server Setup

```bash
cd mcp/sippy && podman build -t sippy-mcp:latest .
```

After starting, test with `sippy_get_releases` to verify connection.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Tools not appearing | Check MCP configuration |
| Connection refused | Verify container is running |

## Tool Details

### sippy_get_releases

Get all available OpenShift releases with metadata.

```
Returns: releases, GA dates, development start dates, capabilities
```

### sippy_get_jobs

Get all CI jobs for a specific release.

```
Parameters:
  - release (required): "4.19", "4.20", etc.

Returns: Array of jobs with pass rates, variants, run counts
```

### sippy_get_health

Get release health indicators (install success, bootstrap, infrastructure).

```
Parameters:
  - release (required): "4.19"

Returns: indicators with pass percentages and improvement trends
```

### sippy_get_tests

Get test results for a release.

```
Parameters:
  - release (required): "4.19"
  - limit (optional): Max results, default 100

Returns: Tests with pass/fail/flake rates, Jira components
```

### sippy_search_jobs

Flexible job search with multiple filters.

```
Parameters:
  - release (required): "4.19"
  - name_contains (optional): Filter by job name substring
  - variant_contains (optional): Filter by variant (e.g., "Platform:aws")
  - min_pass_percentage (optional): Minimum pass rate
  - max_pass_percentage (optional): Maximum pass rate

Returns: Filtered job list
```

### sippy_get_hypershift_jobs

Get ROSA HCP/Hypershift jobs (Installer:hypershift variant).

```
Parameters:
  - release (required): "4.19"

Returns: Jobs using Hypershift installer
```

### sippy_get_failing_jobs

Get jobs below a pass percentage threshold.

```
Parameters:
  - release (required): "4.19"
  - max_pass_percentage (optional): Threshold, default 90

Returns: Jobs with pass rate below threshold
```

## Common Workflows

### Check Current Release Health

```
1. sippy_get_releases → Get current releases
2. sippy_get_health(release="4.20") → Check overall health
3. sippy_get_failing_jobs(release="4.20") → Find problem jobs
```

### Monitor HCP Jobs (Wednesday Watcher)

```
1. sippy_get_hypershift_jobs(release="4.20") → Get all HCP jobs
2. Filter for jobs with pass_percentage < 100
3. Cross-reference with Jira for open bugs
```

### Find Jobs by Platform

```
sippy_search_jobs(
  release="4.19",
  variant_contains="Platform:aws"
)
```

### Find Jobs by Installer Type

```
sippy_search_jobs(
  release="4.19",
  variant_contains="Installer:agent"
)
```

## Variant Reference

| Variant | Example Values |
|---------|----------------|
| `Platform` | aws, azure, gcp, metal, vsphere, kubevirt |
| `Architecture` | amd64, arm64, multi |
| `Network` | ovn |
| `Topology` | ha, single, external, microshift, compact |
| `Installer` | ipi, upi, hypershift, agent |
| `JobTier` | blocking, informing, candidate |
| `FeatureSet` | default, techpreview |
| `Upgrade` | none, minor, micro |

## Related

- @../../mcp/sippy/AGENTS.md — Server documentation
- @../../mcp/sippy/api-discovery.md — Full API reference
