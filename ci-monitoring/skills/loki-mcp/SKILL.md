---
name: loki-mcp
description: Use the Loki MCP server to query CI logs from Observatorium for AWS resource analysis and failure investigation.
---

# Loki MCP Server

Guide for using the Loki MCP server to query CI logs from the dptp Observatorium/Loki instance.

## Quick Reference

| Task | Tool | Key Parameters |
|------|------|----------------|
| Raw LogQL query | `loki_query` | query, limit |
| Query with time range | `loki_query_range` | query, start, end, limit |
| List labels | `loki_labels` | (none) |
| Get label values | `loki_label_values` | label |
| AWS quota errors | `loki_aws_quota_errors` | job_filter, mpiit_scope, limit |
| VPC limit errors | `loki_vpc_limit_errors` | job_filter, limit |
| Orphaned VPCs | `loki_orphaned_vpcs` | job_filter, limit |
| Node availability | `loki_node_availability` | job_filter, limit |
| IPI install failures | `loki_ipi_install_failures` | job_filter, limit |
| MPIIT failures | `loki_mpiit_failures` | error_pattern, limit |

## Server Setup

```bash
cd mcp/loki && podman build -t loki-mcp:latest .
```

**Required environment variables:**
- `LOKI_CLIENT_ID` — OAuth client ID
- `LOKI_CLIENT_SECRET` — OAuth client secret

After starting, test with `loki_labels` to verify connection.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Authentication error | Verify LOKI_CLIENT_ID/SECRET are set |
| Connection timeout | Loki can be slow; try smaller queries first |
| No results | Check job filter; use `loki_labels` to see available labels |
| 401 Unauthorized | Token may be expired; restart server |

## Tool Details

### loki_query

Execute an instant LogQL query.

```
Parameters:
  - query (required): LogQL query string
  - limit (optional): Max entries, default 100

Returns: Simplified entries with timestamp, job, line
```

**Example**:
```
loki_query(
    query='{job=~".*lp-interop.*"} |~ "error"',
    limit=50
)
```

### loki_query_range

Execute LogQL query over a time range.

```
Parameters:
  - query (required): LogQL query string
  - start (optional): Start time (-24h, -7d, or RFC3339)
  - end (optional): End time (default: now)
  - limit (optional): Max entries, default 100

Returns: Simplified entries with timestamp, job, line
```

**Example**:
```
loki_query_range(
    query='{job=~".*"} |~ "VpcLimitExceeded"',
    start="-7d",
    limit=100
)
```

### loki_labels

List all available labels in Loki.

```
Parameters: (none)

Returns: List of label names (e.g., ["job", "namespace", "pod"])
```

### loki_label_values

Get values for a specific label.

```
Parameters:
  - label (required): Label name

Returns: List of values
```

**Example**:
```
loki_label_values(label="job")
# Returns list of all job names
```

### loki_aws_quota_errors

Find AWS quota/limit exceeded errors.

```
Parameters:
  - job_filter (optional): Regex to filter jobs
  - mpiit_scope (optional): If true, filter to MPIIT jobs
  - limit (optional): Max entries, default 50

Returns: Log entries matching AWS quota error patterns
```

**Example**:
```
loki_aws_quota_errors(mpiit_scope=True, limit=100)
```

Matches: VpcLimitExceeded, InstanceLimitExceeded, ServiceQuotaExceededException, InsufficientInstanceCapacity, and more.

### loki_vpc_limit_errors

Find VPC-specific limit errors.

```
Parameters:
  - job_filter (optional): Regex to filter jobs
  - limit (optional): Max entries, default 50

Returns: Log entries matching VPC limit patterns
```

Matches: VpcLimitExceeded, VpcEndpointLimitExceeded, SubnetLimitExceeded, SecurityGroupLimitExceeded, etc.

### loki_orphaned_vpcs

Find deprovision failures that may leave orphaned VPCs.

```
Parameters:
  - job_filter (optional): Regex to filter jobs
  - limit (optional): Max entries, default 50

Returns: Log entries from deprovision jobs with failure patterns
```

Matches: "failed to delete vpc", "DependencyViolation", cleanup failures.

### loki_node_availability

Find node availability issues.

```
Parameters:
  - job_filter (optional): Regex to filter jobs
  - limit (optional): Max entries, default 50

Returns: Log entries matching node capacity issues
```

Matches: InsufficientInstanceCapacity, "minimum worker replica count not met", etc.

### loki_ipi_install_failures

Find IPI installer failures related to VPC/network.

```
Parameters:
  - job_filter (optional): Regex to filter jobs
  - limit (optional): Max entries, default 50

Returns: Log entries from ipi-install jobs with errors
```

### loki_mpiit_failures

Find all failures in MPIIT-scoped jobs.

```
Parameters:
  - error_pattern (optional): Specific error to find
  - limit (optional): Max entries, default 50

Returns: Error logs from lp-interop, rosa-hypershift, konflux, interop-opp jobs
```

**Example**:
```
loki_mpiit_failures(error_pattern="VpcLimitExceeded")
```

## LogQL Syntax Reference

### Stream Selectors

```logql
{job="exact-match"}           # Exact match
{job=~".*pattern.*"}          # Regex match
{job!="exclude-this"}         # Not equal
{job!~"exclude.*pattern"}     # Regex not match
```

### Line Filters

```logql
|= "contains"                 # Contains (case-sensitive)
|~ "regex.*pattern"           # Regex match
!= "not-contains"             # Does not contain
!~ "not.*regex"               # Regex not match
```

### Combining Filters

```logql
{job=~".*interop.*"} 
  |= "error" 
  |~ "VpcLimit|SubnetLimit"
  != "warning"
```

### Time Ranges (for loki_query_range)

| Format | Example | Description |
|--------|---------|-------------|
| Relative | `-24h` | Last 24 hours |
| Relative | `-7d` | Last 7 days |
| RFC3339 | `2026-01-01T00:00:00Z` | Specific timestamp |
| Unix epoch | `1735689600` | Seconds since epoch |

## Common Workflows

### AWS Quota Triage

```
1. loki_aws_quota_errors(mpiit_scope=True) → Find quota hits
2. loki_orphaned_vpcs() → Check for cleanup failures
3. loki_node_availability() → Check capacity issues
4. Sippy: sippy_get_failing_jobs() → Correlate with job status
```

### Investigate Specific Job

```
1. loki_query(query='{job=~".*specific-job-name.*"} |= "error"')
2. Review errors, look for patterns
3. Check related jobs with same error
```

### Historical Analysis (7 days)

```
1. loki_query_range(
     query='{job=~".*"} |~ "VpcLimitExceeded"',
     start="-7d"
   )
2. Group by day/job to find trends
```

## MPIIT Job Patterns

| Pattern | Job Type |
|---------|----------|
| `lp-interop` | Layered Product Interop |
| `lp-rosa-hypershift` | ROSA Hypershift Interop |
| `interop-opp` | Interop OPP |
| `konflux` | Konflux CI |

## AWS Error Pattern Reference

| Error | AWS Resource | Action |
|-------|--------------|--------|
| VpcLimitExceeded | VPCs | Request quota increase |
| SecurityGroupLimitExceeded | Security Groups | Cleanup or quota increase |
| InsufficientInstanceCapacity | EC2 | Try different AZ/instance type |
| AddressLimitExceeded | Elastic IPs | Release unused EIPs |
| VolumeLimitExceeded | EBS | Cleanup volumes |

## Related

- @../../mcp/loki/AGENTS.md — Server documentation
- @../../runbooks/aws-quota-analysis.md — AWS quota analysis runbook
