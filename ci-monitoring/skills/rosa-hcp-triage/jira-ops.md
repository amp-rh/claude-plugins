---
name: rosa-hcp-jira-ops
description: Jira operations subagent for ROSA HCP triage. Searches for existing Firewatch tickets by build ID, identifies ticket gaps for untracked pre/post-phase failures, and files new INTEROP tickets. Designed as a subagent dispatched by the rosa-hcp-triage orchestrator.
---

# Jira Operations Subagent

## Authentication

Source your Jira PAT credentials (e.g., from a vault or .env file), then set `PAT` for the commands below:
```bash
PAT=$(op read "op://RH-Agents/Jira Personal Access Token/credential")
```

Base URL: `https://issues.redhat.com/rest/api/2`

## Operation 1: Find ALL Existing Tickets

**Before drafting any new tickets, search exhaustively.** Duplicate tickets waste time and clutter the Kanban board. Run all three searches below.

### 1a. Search by Build ID (finds Firewatch tickets for the current run)

```bash
curl -s -H "Authorization: Bearer $PAT" \
  "https://issues.redhat.com/rest/api/2/search?jql=text+~+%22<BUILD_ID>%22&fields=key,summary,status,labels"
```

This finds Firewatch tickets (CSPIT/LPINTEROP) which include the build ID in their description.

### 1b. Search by Job Name Label (finds open tickets from ANY run)

**This is the most important search.** Open LPINTEROP/CSPIT tickets from previous runs may still be tracking the same ongoing failure. Search by the full Prow job name as a label:

```bash
curl -s -H "Authorization: Bearer $PAT" \
  "https://issues.redhat.com/rest/api/2/search?jql=project+IN+(INTEROP,CSPIT,LPINTEROP)+AND+labels+%3D+%22<FULL_PROW_JOB_NAME>%22+AND+statusCategory+!%3D+Done&fields=key,summary,status,labels"
```

If this returns open tickets, **the failure is already tracked.** Do NOT file a duplicate. Instead:
- Add a comment to the existing ticket noting the new build ID and date
- Use the existing ticket key in the spreadsheet Jira cell

### 1c. Search by rosa-hypershift-lp label (finds all open ROSA HCP tickets)

```bash
curl -s -H "Authorization: Bearer $PAT" \
  "https://issues.redhat.com/rest/api/2/search?jql=project+IN+(INTEROP,CSPIT,LPINTEROP)+AND+labels+%3D+rosa-hypershift-lp+AND+statusCategory+!%3D+Done&fields=key,summary,status,labels"
```

This gives full visibility into what's already being tracked across all projects.

### Batch Search by Build ID

```bash
for BUILD_ID in <ID1> <ID2> <ID3> <ID4> <ID5>; do
  echo "=== Build $BUILD_ID ==="
  curl -s -H "Authorization: Bearer $PAT" \
    "https://issues.redhat.com/rest/api/2/search?jql=text+~+%22${BUILD_ID}%22&fields=key,summary,status"
  sleep 1
done
```

### Firewatch Ticket Patterns

- **CSPIT project**: Current Firewatch tickets. Summary contains "passed" or "failed".
- **LPINTEROP project**: Legacy Firewatch tickets. Still actively used — many are open with status "ACK". **Do not ignore these.**
- Both include the full Prow job name as a label, making label-based search reliable.

## Operation 2: Identify Ticket Gaps

After collecting per-LP triage results and Firewatch tickets, identify gaps:

| Scenario | Firewatch ticket? | Infra ticket needed? |
|----------|-------------------|---------------------|
| Tests passed, job passed | Yes ("passed", Closed) | No |
| Tests passed, post-phase failed | Yes ("passed", Closed) | **Yes** — teardown failure is untracked |
| Tests failed, job failed | Yes ("failed", Open) | Maybe — depends on root cause |
| Pre-phase failed, no tests ran | **No** — Firewatch never ran | **Yes** — infra failure is untracked |

**Every pre-phase and post-phase failure must have a tracking ticket.**

### Two Levels of Tickets

When multiple LP jobs share a root cause, file BOTH:

1. **One shared root cause ticket** — covers all affected LPs, describes the underlying issue and fix
2. **One per-LP ticket** — 1:1 with the Prow job, includes job-specific labels so it appears on the Kanban board filtered by that job

The per-LP tickets reference the shared ticket. This mirrors how Firewatch works (one ticket per job) and ensures each job's failure is visible on the Kanban board.

### Per-LP Ticket Labels

Each per-LP ticket must include ALL of these labels:

| Label | Example | Source |
|-------|---------|--------|
| `rosa-hcp-lp` | `rosa-hcp-lp` | INTEROP board filter |
| `rosa-hypershift-lp` | `rosa-hypershift-lp` | Shared board filter |
| `<RELEASE>-lp` | `4.20-lp` | Version from tab name |
| `<product>-lp` | `devspaces-lp` | Product label (see mapping below) |
| `<full-prow-job-name>` | `periodic-ci-redhat-developer-...` | Full Prow job name as label |
| `infra-failure` | `infra-failure` | Classification |

### Product Label Mapping (ROSA HCP 4.20)

| LP Product | Product Label |
|-----------|--------------|
| Dev-Spaces | `devspaces-lp` |
| RHSSO | `rhsso-lp` |
| NFD | `nfd-lp` |
| Pipelines v1.21 | `pipelines-lp` |
| Logging | `cluster-logging-lp` |

## Operation 3: File INTEROP Tickets

File new tickets for untracked failures. Use Jira wiki markup.

```bash
curl -s -X POST -H "Authorization: Bearer $PAT" -H "Content-Type: application/json" \
  "https://issues.redhat.com/rest/api/2/issue" \
  -d '<JSON_PAYLOAD>'
```

### Required Labels

Every INTEROP ticket must include labels that ensure visibility on Kanban boards. The labels depend on the platform and release.

**ROSA HCP tickets:**

| Label | Purpose |
|-------|---------|
| `rosa-hcp-lp` | INTEROP Kanban board filter |
| `rosa-hypershift-lp` | Shared Firewatch/CSPIT board filter |
| `4.20-lp` (or `4.19-lp`, etc.) | Version label — derived from the OCP release |
| `infra-failure` | Classification (for infra issues) |

**OPP AWS tickets:**

| Label | Purpose |
|-------|---------|
| `opp-lp` | OPP board filter |
| `opp-aws-lp` | Platform-specific filter |
| `4.20-lp` / `4.21-lp` | Version label(s) — include all affected versions |
| `infra-failure` | Classification (for infra issues) |

### Ticket Template (ROSA HCP, shared infra failure)

```json
{
  "fields": {
    "project": {"key": "INTEROP"},
    "issuetype": {"name": "Bug"},
    "priority": {"name": "Major"},
    "summary": "<PLAIN_LANGUAGE_SUMMARY>",
    "labels": ["rosa-hcp-lp", "rosa-hypershift-lp", "<RELEASE>-lp", "infra-failure"],
    "description": "<JIRA_WIKI_MARKUP>"
  }
}
```

Description structure:
```
h2. Summary

<Which jobs are affected, what the overall impact is>

|| LP Product || Prow Job || JUnit || Firewatch ||
| <LP1> | {{<job1>}} | <X>/<Y> passed | <CSPIT ticket> |
...

h2. Error

{code}
<exact error from build log>
{code}

h2. Details

* *Failed step*: {{<step-name>}} (<phase>, <duration>)
* *Example build*: [Build <BUILD_ID>|<PROW_URL>]
* *Root cause*: <plain-language explanation>
* *Classification*: <type>

h2. Fix Required

<numbered steps>

h2. Related

* Tracking spreadsheet: [<SHEET_TAB>|https://docs.google.com/spreadsheets/d/10TLPgFV0qCqa-NVc6agvYRGp19_MK2F-vk-ubEP1Y_Y]
* <links to related tickets>
```

### Ticket Template (single LP, pre-phase failure)

Same structure but for one LP. Include the note:
```
This issue was identified during manual watcher triage. Firewatch did not fire because the job failed in pre-phase before cluster creation.
```

### Important Constraints

- **RC codes are internal only.** Never include RC codes (e.g. RC-HCP-3) in ticket summaries or descriptions. Use plain-language failure descriptions.
- **Set priority appropriately.** Major for single-LP issues. Critical if the failure blocks all LP jobs or prevents any testing.

## Operation 4: Link Tickets

After filing, create issue links between related tickets. Use the Jira issue link API with **2-second delays** between calls to avoid rate limiting (429 errors).

```bash
curl -s -X POST -H "Authorization: Bearer $PAT" -H "Content-Type: application/json" \
  "https://issues.redhat.com/rest/api/2/issueLink" \
  -d '{"type":{"name":"<LINK_TYPE>"},"inwardIssue":{"key":"<KEY1>"},"outwardIssue":{"key":"<KEY2>"}}'
sleep 2
```

### Available Link Types

| Type Name | Inward | Outward | Use For |
|-----------|--------|---------|---------|
| `Causality` | "is caused by" | "causes" | Per-LP ticket → shared root cause |
| `Related` | "is related to" | "relates to" | INTEROP ↔ Firewatch CSPIT, INTEROP ↔ related existing tickets |
| `Blocks` | "is blocked by" | "blocks" | When one issue must be resolved before another |
| `Duplicate` | "is duplicated by" | "duplicates" | When tickets cover the same issue |

### Linking Strategy

For each triage run, create these links:

1. **Per-LP → shared root cause**: `Causality` link, per-LP ticket "is caused by" the shared ticket
2. **INTEROP ↔ Firewatch**: `Related` link, per-LP INTEROP ticket "is related to" its CSPIT Firewatch counterpart
3. **INTEROP ↔ existing tickets**: `Related` link to any pre-existing tickets found during search (e.g. tickets filed by other watchers)

## Output Format

Write to `<SCRATCHPAD>/jira-results.md`:

```markdown
# Jira Search Results

## Firewatch Tickets (found by build ID)

| LP Product | Build ID | Ticket | Summary | Status |
|-----------|----------|--------|---------|--------|
| <LP1> | <ID> | <KEY> | <summary> | <status> |
| <LP2> | <ID> | (none) | — | — |

## Ticket Gaps

| LP Product | Phase | Error | Needs Ticket |
|-----------|-------|-------|-------------|
| <LP1> | post | <error> | Yes — shared with LP2, LP3 |
| <LP2> | pre | <error> | Yes — standalone |

## Filed Tickets

| Ticket | Type | Summary | Covers |
|--------|------|---------|--------|
| INTEROP-NNNN | shared root cause | <summary> | <LP1>, <LP2>, <LP3> |
| INTEROP-NNNN | per-LP (Dev-Spaces) | <summary> | Dev-Spaces |
| INTEROP-NNNN | per-LP (Pipelines) | <summary> | Pipelines |

## Links Created

| From | Link Type | To | Reason |
|------|-----------|-----|--------|
| INTEROP-NNNN (per-LP) | is caused by | INTEROP-NNNN (root cause) | Causality |
| INTEROP-NNNN (per-LP) | is related to | CSPIT-NNNN (Firewatch) | Same LP job |
| INTEROP-NNNN (all) | is related to | INTEROP-NNNN (existing) | Pre-existing ticket |

## Jira Cell Values (for spreadsheet)

| LP Product | Cell | Value |
|-----------|------|-------|
| <LP1> | AC12 | CSPIT-NNNN; INTEROP-NNNN |
| <LP2> | AC13 | INTEROP-NNNN |
```
