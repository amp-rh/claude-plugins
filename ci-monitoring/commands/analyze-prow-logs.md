# Analyze Prow Logs

Fetch and analyze build logs from a Prow CI job or rehearsal run.

## Instructions

1. **Get the job URL** from the user's input or find the latest rehearsal for an active PR:
   - Use the Prow job link from PR comments or Slack notifications
   - Format: `https://prow.ci.openshift.org/view/gs/test-platform-results/logs/<job-name>/<run-id>`

2. **Fetch the build log** from the Prow artifacts URL:
   - Navigate to the job URL and locate the artifacts link
   - Download `build-log.txt` for each failed step from the GCS artifacts bucket

3. **For each failed step**, analyze the build-log.txt:
   - Identify the root cause (infrastructure, test code, product bug)
   - Note any actionable errors or stack traces
   - Check if it's a known flake vs new failure

4. **Cross-reference with Loki** using the `loki_mcp` tools for broader pattern matching:
   - Use `loki_query` to search for the same error across other jobs
   - Use `loki_aws_quota_errors` or `loki_mpiit_failures` for common failure categories

5. **Provide a summary** including:
   - Overall job result (passed/failed/partial)
   - List of failed steps with brief root cause
   - Recommended next actions (retry, fix code, file bug)

## Reference

- @../skills/loki-mcp/SKILL.md
- @../runbooks/failure-classification.md
