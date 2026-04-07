# Retrigger Protocol

Steps for manually retriggering failed jobs and tracking retriggers.

## When to Retrigger

Retrigger jobs when the failure is:
- **Transient**: Temporary infrastructure issue
- **Flaky**: Known intermittent test
- **Infrastructure**: CI/cluster provisioning problem

**Do NOT retrigger** if:
- Failure is clearly a product bug
- Same failure occurred on previous retrigger
- Root cause needs investigation first

## Retrigger Steps

### Step 1: Identify the Job

1. Go to [Prow](https://prow.ci.openshift.org/)
2. Find the failed job
3. Note the job name and run ID

### Step 2: Trigger the Rerun

**Option A: Via Prow UI**
1. Open the failed job
2. Click "Rerun" button
3. Confirm the retrigger

**Option B: Via `/retest` Comment**
1. Find the PR or commit that triggered the job
2. Add comment: `/retest <job-name>`

**Option C: Via `/pj-rehearse`** (for release repo PRs)
1. Add comment: `/pj-rehearse`
2. Wait for new rehearsal to start

### Step 3: Update Jira Ticket

1. Add the `retrigger` label to the ticket
2. Add a comment explaining the retrigger

**Comment Template:**
```
Retriggered job due to [transient infrastructure issue / known flaky test / cluster provisioning failure].

Previous run: [link to failed run]
New run: [link to retriggered run]

Reason: [brief explanation of why this is expected to pass on retry]
```

### Step 4: Monitor Rerun

1. Watch for new run to complete
2. If passes: Update ticket and close
3. If fails again: Escalate or investigate further

## Label Usage

| Label | When to Apply |
|-------|---------------|
| `retrigger` | Any job that was manually retriggered |
| `flaky-test` | Known intermittent test failure |
| `infra-failure` | Infrastructure/CI issue |
| `second-retrigger` | Second retry attempt |

## Retrigger Limits

- **First retrigger**: Always OK for transient issues
- **Second retrigger**: Only if different failure mode
- **Third retrigger**: Investigate root cause first

If a job fails 3+ times:
1. Stop retriggering
2. Investigate root cause
3. Create dedicated bug ticket if needed

## Related

- @failure-classification.md — When to retrigger
- @daily-triage.md — Full triage workflow
