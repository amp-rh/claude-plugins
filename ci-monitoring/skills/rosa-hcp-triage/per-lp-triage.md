---
name: rosa-hcp-triage-lp
description: Analyze a single ROSA HCP layered product Prow job. Extracts build logs from Prow Spyglass, classifies the failure, and writes a structured result file. Designed as a subagent dispatched by the rosa-hcp-triage orchestrator.
---

# Per-LP Triage Subagent

## Invocation

Inputs (from dispatch file):
- `LP_PRODUCT` — layered product name, e.g. `Dev-Spaces`
- `LP_SLUG` — filesystem-safe name, e.g. `dev-spaces`
- `PROW_JOB` — full Prow job name
- `RELEASE` — OCP release, e.g. `4.20`
- `PASS_PCT` — current Sippy pass %
- `RUN_COUNT` — current Sippy run count
- `DISPATCH_FILE` — path to the dispatch file
- `SCRATCHPAD` — scratchpad directory path

Output: `<SCRATCHPAD>/results/<LP_SLUG>.md`

This subagent does NOT search or file Jira tickets — that is handled by the `jira-ops` subagent.

## Step 1: Get Build Links from Prow

Navigate to the Prow job history:
```
https://prow.ci.openshift.org/?job=<PROW_JOB>
```

Extract the most recent build links (deduplicate):
```js
Array.from(new Set(
  Array.from(document.querySelectorAll('a'))
    .filter(a => a.href.includes('view/gs'))
    .map(a => a.href)
)).slice(0, 3)
```

Extract the **build ID** from each URL — it's the last path segment:
```
https://prow.ci.openshift.org/view/gs/test-platform-results/logs/<JOB_NAME>/<BUILD_ID>
```

## Step 2: Analyze Build via Spyglass

Navigate to the build URL. Extract all three Spyglass iframes in a single call:

```js
(() => {
  const iframes = document.querySelectorAll('iframe');
  const result = {};
  for (const iframe of iframes) {
    try {
      const body = iframe.contentDocument?.body;
      if (!body) continue;
      if (iframe.src?.includes('metadata'))
        result.metadata = body.innerText?.substring(0, 500);
      if (iframe.src?.includes('junit'))
        result.junit = body.innerText?.substring(0, 2000);
      if (iframe.src?.includes('buildlog')) {
        const text = body.innerText;
        result.has_deletehostedzone = text?.includes('DeleteHostedZone') || false;
        result.has_vpclimit = text?.includes('VpcLimitExceeded') || false;
        result.has_authfailure = text?.includes('AuthFailure') || text?.includes('InvalidAccessKeyId') || false;
        result.has_capacity = text?.includes('InsufficientInstanceCapacity') || false;
        result.buildlog_tail = text?.substring(text.length - 3000);
      }
    } catch(e) {}
  }
  return result;
})()
```

Wait 5 seconds after navigating for iframes to load. If iframes return empty, retry once.

**Fallback (no browser session):** Fetch the raw log from GCS:
```
https://storage.googleapis.com/test-platform-results/logs/<PROW_JOB>/<BUILD_ID>/build-log.txt
```

### What to Extract

From **metadata**: duration, start time, pass/fail status.

From **JUnit**: Pass/fail counts and which steps failed. Key patterns:
- `N/M Tests Failed` — if failures are only `post phase` and `rosa-teardown`, tests actually passed
- `N/M Tests Passed` — total test count

From **build log tail**: The exact error message. Search for these patterns:

| Pattern | Phase | Meaning |
|---------|-------|---------|
| `DeleteHostedZone`, `HostedZoneNotEmpty` | Post | Route 53 cleanup failure — tests likely passed |
| `VpcLimitExceeded` | Pre | AWS VPC quota exhausted — no cluster created |
| `AuthFailure`, `InvalidAccessKeyId` | Pre | AWS credential failure |
| `InsufficientInstanceCapacity` | Pre | EC2 capacity issue |
| `valid policy version` | Pre | ROSA CLI config issue |
| `DELETE_FAILED`, `StackDeleteComplete` | Post | VPC CloudFormation cleanup failure |
| `unpacking is not complete yet` | Test | OLM bundle issue |
| `rosa-teardown failed` + `send-results-to-reportportal succeeded` | Post | Tests passed, only teardown broken |

## Step 3: Classify Failure

Read `./references/failure-patterns.md` and match against known patterns.

**If match found**: Use the existing RC code and classification.

**If no match**: Classify using the decision tree:

| Phase | Cluster provisioned? | Classification |
|-------|---------------------|----------------|
| Pre | No — CI/config error | CI/Job Config |
| Pre | No — AWS auth/quota | Infrastructure |
| Test | Yes — product failed | Product Bug |
| Test | Yes — timeout | Transient |
| Post | Yes — cleanup failed | Infrastructure (cleanup) |

**False negatives**: When the post phase fails but JUnit shows tests passed, flag `false_negative: true`. Sippy 0% is misleading in this case.

If the pattern is new, set `NEW_RC: true` and propose the next `RC-HCP-N` code with a draft catalog entry.

## Step 4: Retrigger Assessment

- **CI/Job Config**: No — identical failure every run.
- **Infrastructure (creds/capacity)**: Only after the issue is confirmed resolved.
- **Infrastructure (cleanup)**: No — clean up zombie resources first.
- **Transient**: Yes — retrigger immediately.
- **Product Bug**: No — engage PQE team.

## Output Format

Write to `<SCRATCHPAD>/results/<LP_SLUG>.md`:

```markdown
# <LP_PRODUCT> Triage Result

## Summary

| Field | Value |
|-------|-------|
| LP Product | <LP_PRODUCT> |
| Prow Job | `<PROW_JOB>` |
| Release | <RELEASE> |
| Sippy Pass % | <PASS_PCT>% (<RUN_COUNT> runs) |

## Builds Analyzed

### Build <BUILD_ID>

| Field | Value |
|-------|-------|
| URL | <PROW_BUILD_URL> |
| Date | <date> |
| Duration | <total duration> |
| Failed Step | `<step-name>` (<phase>, <step duration>) |
| JUnit | <X>/<Y> passed |
| Error | `<one-line error>` |

## Classification

| Field | Value |
|-------|-------|
| RC Code | <RC-code or "NEW"> |
| NEW_RC | <true/false> |
| Classification | <type> |
| Root Cause | <explanation> |
| Error Signature | `<exact error line>` |
| False Negative | <true/false> |

## Retrigger

| Field | Value |
|-------|-------|
| Retrigger | <Yes/No> |
| Reason | <explanation> |
| Prerequisite | <what must happen first, or "none"> |

## New RC Catalog Entry

<"N/A" if NEW_RC is false, otherwise the full entry for failure-patterns.md>
```
