# AWS Quota Analysis Runbook

Step-by-step guide for analyzing AWS quota failures using Loki MCP tools.

→ **Skill**: @../../../../skills/loki-mcp/SKILL.md

## Summary

Query CI logs using the Loki MCP server to diagnose AWS quota failures.

**When to use:**
- VPC/EC2 quota errors appearing in job logs
- Investigating failed cluster provisioning
- Looking for orphaned resources after failed cleanup
- Analyzing AWS capacity issues

**Key tools:**
- `loki_aws_quota_errors` — All AWS quota/limit errors
- `loki_vpc_limit_errors` — VPC-specific limit errors
- `loki_orphaned_vpcs` — Deprovision failures (potential orphans)
- `loki_node_availability` — Node capacity issues

## Quick Triage Flow

```
VpcLimitExceeded found?
├── Yes → Check which account → Request quota increase OR cleanup orphans
└── No
    │
    InsufficientInstanceCapacity found?
    ├── Yes → Try different instance type or AZ → Retrigger job
    └── No
        │
        Deprovision failures found?
        ├── Yes → Check AWS console → Manual cleanup → File JIRA
        └── No → Other root cause (check Sippy for job details)
```

## Escalation Thresholds

| Condition | Action |
|-----------|--------|
| >5 VpcLimitExceeded in 24h | Escalate to Test Platform |
| >10 deprovision failures | Check for systematic cleanup issue |
| Same error >3 times for same job | File bug on job configuration |
| Capacity issues in multiple AZs | May be region-wide, switch region |

**Channel**: `#forum-ocp-testplatform`

## Related

- @aws-cleanup.md — Manual cleanup procedures
- @daily-triage.md — Daily triage workflow
- @../aws-quota-failures/error-patterns.md — Error pattern catalog
