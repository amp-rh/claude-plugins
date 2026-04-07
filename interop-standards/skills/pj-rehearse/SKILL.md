---
name: pj-rehearse
description: Interact with OpenShift CI rehearsal jobs in GitHub PRs using pj-rehearse commands. Use when triggering, aborting, or debugging rehearsal jobs on openshift/release PRs.
---

# pj-rehearse: OpenShift CI Rehearsals

Commands for managing CI rehearsal jobs on PRs in the openshift/release repository.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `/pj-rehearse <job-name>` | Trigger specific rehearsal job |
| `/abort-pj-rehearse` | Abort all rehearsal jobs |

## ⚠️ Critical Rule

**NEVER run `/pj-rehearse` without a job name!**

```bash
# ❌ WRONG - triggers ALL jobs, wastes CI resources
/pj-rehearse

# ✅ CORRECT - trigger specific job only
/pj-rehearse periodic-ci-<org>-<repo>-<branch>-<job-name>
```

This mistake can waste 4+ hours of shared CI resources.

## Workflow: Trigger Rehearsal

### 1. Find Available Jobs

After pushing changes, wait for the `openshift-ci-robot` to post a `REHEARSALNOTIFIER` comment listing affected jobs.

**Or query via gh CLI:**

```bash
gh pr view <PR> --repo openshift/release --json statusCheckRollup \
  | jq -r '.statusCheckRollup[].context' | grep rehearse
```

### 2. Identify Job Name

Job names follow this pattern:

```
<type>-ci-<org>-<repo>-<branch>-<test-name>
```

| Component | Example |
|-----------|---------|
| type | `periodic`, `pull`, `release` |
| org | `RedHatQE`, `openshift` |
| repo | `interop-testing`, `release` |
| branch | `master`, `main` |
| test-name | `ibm-fusion-access-cnv-ocp4.21-lp-interop-cr` |

**Example full name:**
```
periodic-ci-RedHatQE-interop-testing-master-ibm-fusion-access-cnv-ocp4.21-lp-interop-cr-ibm-fusion-access-cnv-cr-ocp421
```

### 3. Post Comment

Add a comment to the PR with the command:

```
/pj-rehearse periodic-ci-RedHatQE-interop-testing-master-ibm-fusion-access-cnv-ocp4.21-lp-interop-cr-ibm-fusion-access-cnv-cr-ocp421
```

**Via gh CLI:**

```bash
gh pr comment <PR> --repo openshift/release \
  --body "/pj-rehearse <full-job-name>"
```

## Recovery: Accidentally Triggered All Jobs

If you ran `/pj-rehearse` without a job name:

1. **Wait 10 minutes** for jobs to start
2. **Abort all jobs:**
   ```
   /abort-pj-rehearse
   ```
3. **Wait 10 more minutes** for abort to propagate
4. **Trigger only the specific job needed**

## Debugging Rehearsal Failures

### Check Job Status

```bash
gh pr checks <PR> --repo openshift/release
```

### Access Build Logs

1. Click failing check in PR → opens Prow
2. Click "Build log" link
3. Look for the `[failed]` step

### Common Failure Categories

| Category | Transient | Action |
|----------|-----------|--------|
| Infrastructure flake | ✅ Yes | Retry with `/pj-rehearse <job>` |
| Missing env var | ❌ No | Fix config, push, retry |
| Image pull failure | ⚠️ Sometimes | Check registry, retry |
| Script bug | ❌ No | Fix script, push, retry |
| Timeout | ⚠️ Sometimes | Check logs, may need timeout increase |

### Re-run After Fix

After pushing a fix:

```bash
# Wait for CI to pick up new commit, OR manually trigger
/pj-rehearse <job-name>
```

## REHEARSALNOTIFIER Comment

After pushing changes that affect job configs, `openshift-ci-robot` posts a comment like:

```markdown
The following Prow jobs would be affected by this change:

| Job | Repo | Type | Reason |
|-----|------|------|--------|
| periodic-ci-org-repo-branch-test | org/repo | periodic | new config |
```

Parse this table to find job names to rehearse.

## Automation: Trigger via Script

```bash
PR_NUMBER=72017
JOB_NAME="periodic-ci-RedHatQE-interop-testing-master-ibm-fusion-access-cnv-ocp4.21-lp-interop-cr-ibm-fusion-access-cnv-cr-ocp421"

gh pr comment "${PR_NUMBER}" --repo openshift/release \
  --body "/pj-rehearse ${JOB_NAME}"
```

## Monitoring Rehearsal Progress

### Check Status

```bash
gh pr checks <PR> --repo openshift/release --watch
```

### List Recent Comments

```bash
gh pr view <PR> --repo openshift/release --comments | tail -50
```

## Anti-Patterns

| ❌ Don't | ✅ Do |
|----------|-------|
| Run `/pj-rehearse` without job name | Always specify full job name |
| Trigger multiple jobs simultaneously | Run one at a time for easier debugging |
| Ignore REHEARSALNOTIFIER comment | Use it to find affected job names |
| Retry repeatedly without investigating | Check logs, understand failure first |

## Related

| Resource | Purpose |
|----------|---------|
| [CI Operator docs](https://docs.ci.openshift.org/) | Official documentation |
| @../openshift-release-ci/SKILL.md | Config changes & generation |
| prow-build-logs (external, not yet created) | Fetching and analyzing build logs |
