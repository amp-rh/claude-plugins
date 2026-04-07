---
name: rosa-hcp-triage
description: Orchestrator for ROSA HCP layered product interop triage. Reads the tracking spreadsheet, batch-checks Sippy, dispatches per-LP subagents, finds/files Jira tickets, and generates an HTML report for spreadsheet updates. Use on ROSA HCP triage days (Wednesdays) or when the user requests ROSA HCP triage.
---

> **Configuration**: The spreadsheet ID used throughout this skill defaults to the MPIIT watcher sheet. Override by setting `WATCHER_SPREADSHEET_ID` in your environment.

# ROSA HCP Triage — Orchestrator

## Invocation

Inputs:
- `SHEET_TAB` — spreadsheet tab to triage, e.g. `ROSA HCP 4.20` (ask if not provided)
- `--dry-run` — if set, complete all read steps and present all drafts but perform no writes

Workspace context (resolve before starting):
- `ROTATION_DIR` — read the project `AGENTS.md` "Current Rotation" link to find the active rotation directory (e.g. `rotations/2026-02-16`)
- `TODAY` — today's date in `YYYY-MM-DD` format
- `SCRATCHPAD` — `.scratchpad/triage/<TODAY>` (create if missing, with `results/` subdirectory)

## Subagents

This skill dispatches work to specialized subagents. Each is self-contained and can run independently.

| Subagent | Skill File | Purpose |
|----------|-----------|---------|
| Per-LP Triage | [per-lp-triage.md](per-lp-triage.md) | Analyze one LP job: Prow build logs, classify failure, assess retrigger |
| Jira Ops | [jira-ops.md](jira-ops.md) | Search for tickets by build ID, file new INTEROP tickets for untracked failures |

## Phase 1: Discovery

### 1a. Read the Spreadsheet

The source of truth for which jobs to triage is the tracking spreadsheet:
```
https://docs.google.com/spreadsheets/d/10TLPgFV0qCqa-NVc6agvYRGp19_MK2F-vk-ubEP1Y_Y
```

See `../watcher-spreadsheet/reference.md` for sheet GIDs, column layouts, and known row assignments.

Use the `firefox-browser` skill to open the spreadsheet. Verify auth first:
```javascript
async () => {
  var id = '10TLPgFV0qCqa-NVc6agvYRGp19_MK2F-vk-ubEP1Y_Y';
  var url = 'https://docs.google.com/spreadsheets/d/' + id + '/gviz/tq?tqx=out:csv&sheet=' + encodeURIComponent('<SHEET_TAB>') + '&range=A1:A1';
  var r = await fetch(url, { credentials: 'include' });
  var text = await r.text();
  if (r.status !== 200 || text.includes('Sign in')) return 'AUTH FAILED: status=' + r.status;
  return 'AUTH OK: ' + text.slice(0, 80);
}
```

Then read the full tab data. **Always read the date row (row 8) and header row (row 10) to discover current column positions** — date columns shift right as new test runs are added:
```javascript
async () => {
  var id = '10TLPgFV0qCqa-NVc6agvYRGp19_MK2F-vk-ubEP1Y_Y';
  var sheet = encodeURIComponent('<SHEET_TAB>');
  var base = 'https://docs.google.com/spreadsheets/d/' + id + '/gviz/tq?tqx=out:csv&sheet=' + sheet;
  var r1 = await fetch(base + '&range=A8:AH8', { credentials: 'include' });
  var dates = await r1.text();
  var r2 = await fetch(base + '&range=A10:AH10', { credentials: 'include' });
  var headers = await r2.text();
  var r3 = await fetch(base + '&range=A11:AH20', { credentials: 'include' });
  var data = await r3.text();
  return { dates: dates, headers: headers, data: data };
}
```

From the response, extract:
- The list of LP products (column A, skip "Not Tested" rows)
- The latest test date and its column positions (Status column, Jira column)
- The Comments column (immediately after the last Jira column)
- Current cell values for Status, Jira, and Comments
- The OCP release (from tab name, e.g. `ROSA HCP 4.20` → `4.20`)

### 1b. Sippy — Batch Pass Rates

Navigate to the Sippy Jobs view filtered by `-rosa-hypershift`:

```
https://sippy.dptools.openshift.org/sippy-ng/jobs/<RELEASE>?filters={"items":[{"columnField":"name","operatorValue":"contains","value":"rosa-hypershift"}]}&sortField=current_pass_percentage&sort=asc
```

Extract via `evaluate_script`:
```js
Array.from(document.querySelectorAll('[role="row"]')).slice(1).map(row => {
  const cells = Array.from(row.querySelectorAll('[role="gridcell"],[role="cell"]'));
  return cells.map(c => c.innerText?.trim()).filter(Boolean);
}).filter(r => r.length > 0)
```

**Categorizing results:**
- **LP test jobs** (triage these): Match pattern `*-lp-rosa-hypershift-*`.
- **Trigger jobs**: Match `*_trigger-rosa-hypershift-*`. Always pass. Skip.
- **Watcher bot jobs**: Match `*-lp-watcher-bot-message-*`. Always pass. Skip.
- Jobs with **0 current runs** are inactive — skip.
- A low pass % may be a **false negative** if tests pass but cleanup fails. Flag for the subagent to confirm.

### 1c. Write Dispatch File

Write `<SCRATCHPAD>/dispatch.md` with context for subagents:

```markdown
# Triage Dispatch: <TODAY>

SHEET_TAB: <SHEET_TAB>
RELEASE: <RELEASE>
ROTATION_DIR: <ROTATION_DIR>
DRY_RUN: <true|false>

## Sippy Summary

| LP Product | Row | Slug | Prow Job | Pass % | Runs |
|-----------|-----|------|----------|--------|------|
| Dev-Spaces | 12 | dev-spaces | `<full job name>` | <X>% | <N> |
| ... | ... | ... | ... | ... | ... |

## Jobs to Triage

- [ ] Dev-Spaces
- [ ] RHSSO
- [ ] NFD
- [ ] Pipelines v1.21
- [ ] Logging
```

## Phase 2: Per-LP Analysis (subagents)

For each LP job, dispatch the **per-LP triage subagent** ([per-lp-triage.md](per-lp-triage.md)):

```
/rosa-hcp-triage-lp --lp="Dev-Spaces" --dispatch=<SCRATCHPAD>/dispatch.md
```

Each subagent writes its result to `<SCRATCHPAD>/results/<LP_SLUG>.md`.

Subagents are independent and can run in parallel. Wait for all to complete before Phase 3.

## Phase 3: Consolidation

### 3a. Find Existing Jira Tickets

Dispatch the **Jira ops subagent** ([jira-ops.md](jira-ops.md)) to search for tickets by build ID.

**Critical**: Do NOT trust the spreadsheet's existing Jira column for the current test date — it may reference tickets from a previous run. Always search by the **build ID** from the current Prow run to find the correct Firewatch tickets.

The subagent searches `text ~ "<BUILD_ID>"` for each build and returns the matching tickets. It also identifies **ticket gaps** — failures (pre-phase or post-phase) with no corresponding ticket.

### 3b. Group by Root Cause

Multiple LP jobs often share the same root cause. Group results by error signature.

### 3c. Match Against Known Patterns

Read `references/failure-patterns.md`. If a subagent found a new failure pattern, collect it for the RC catalog update.

### 3d. File Tickets for Untracked Failures

**Every pre-phase and post-phase failure must have a tracking ticket.** Firewatch only files tickets when test phases complete, so these gaps are common:

- **Pre-phase failures**: Cluster never provisioned, Firewatch never ran → no ticket
- **Post-phase failures**: Firewatch may file a "passed" ticket (if tests passed) but the infra failure itself is untracked

For each untracked failure, dispatch the **Jira ops subagent** to file an INTEROP ticket. If multiple LPs share the same root cause, file one ticket covering all of them.

**Not in `--dry-run` mode**: File tickets via Jira REST API. Record the new ticket keys for the HTML report.

**In `--dry-run` mode**: Include the draft tickets in the HTML report but don't file them.

### 3e. Update RC Catalog

If new failure patterns were found, append entries to `references/failure-patterns.md`.

**RC codes are internal only.** Never include RC codes in Jira tickets, spreadsheet comments, Slack pings, or any external artifact. Use plain-language failure descriptions instead.

### 3f. Generate HTML Report

Generate a click-to-copy HTML report at `<SCRATCHPAD>/spreadsheet-updates.html` and open it in the user's default browser via `xdg-open`.

The report contains:

1. **Status cells** — one row per LP, with the cell address and value to paste
2. **Jira cells** — Firewatch ticket + any new INTEROP ticket, combined (e.g. `CSPIT-3058; INTEROP-8875`)
3. **Comments cells** — triage note to append (plain-language, no RC codes, include ticket references)
4. **Filed/draft tickets** — full ticket details with links for filed tickets, full descriptions for drafts
5. **Other tabs summary** — status of OPP 4.21, FIPS, etc.

Each value cell is clickable to copy to clipboard. Ticket description blocks are also clickable to copy.

Open the report:
```bash
xdg-open "<SCRATCHPAD>/spreadsheet-updates.html"
```

### 3g. Write Daily Log

Write triage results to `<ROTATION_DIR>/daily/<TODAY>.md`:

```markdown
# Daily Triage: <TODAY>

**Watcher**: <name>
**Platform**: ROSA HCP (<SHEET_TAB>)

## Sippy Summary

| LP Product | Prow Job | Pass % | Runs | Status |
|-----------|----------|--------|------|--------|
| <LP1> | `<job1>` | <X>% | <N> | <Pass/Fail/...> |
...

## Per-LP Triage

### <LP_PRODUCT>

| Field | Value |
|-------|-------|
| Job | `<FULL_PROW_JOB_NAME>` |
| Build | [<BUILD_ID>](<PROW_URL>) |
| Pass % | <current>% (<N> runs) |
| JUnit | <X>/<Y> passed |
| Failed step | `<step-name>` (<phase>) |
| Classification | <type> |
| Firewatch | <CSPIT ticket or "none"> |
| Infra ticket | <INTEROP ticket or "none"> |
| Action | <retrigger / engage PQE / file ticket> |

<Repeat for each LP job>
```

## LP-to-Job Mapping Tables

### ROSA HCP 4.20

Trigger job (not triaged): `periodic-ci-rhpit-interop-tests-main-weekly_trigger-rosa-hypershift-layered-product-interop-420`

| Row | LP Product | Slug | Prow Job |
|-----|-----------|------|----------|
| 11 | MTC | _(skip)_ | _(not onboarded)_ |
| 12 | Dev-Spaces | dev-spaces | `periodic-ci-redhat-developer-devspaces-interop-tests-main-devspaces-ocp4.20-lp-rosa-hypershift-devspaces-aws-rosa-hypershift` |
| 13 | RHSSO | rhsso | `periodic-ci-rhbk-sso-test-main-rhsso-product-ocp4.20-lp-rosa-hypershift-rhsso-aws-rosa-hypershift` |
| 14 | Service Mesh | _(skip)_ | _(not onboarded)_ |
| 15 | NFD | nfd | `periodic-ci-openshift-cluster-nfd-operator-release-4.20-ocp4.20-lp-rosa-hypershift-nfd-e2e-master-aws-rosa-hypershift` |
| 16 | Pipelines v1.21 | pipelines | `periodic-ci-openshift-pipelines-release-tests-release-v1.21-openshift-pipelines-ocp4.20-lp-rosa-hypershift-openshift-pipelines-aws-rosa-hypershift` |
| 17 | Logging | logging | `periodic-ci-openshift-logging-extended-logging-tests-interop-main-openshift-logging-hypershift-4.20-lp-rosa-hypershift-openshift-logging-aws-rosa-hypershift` |

All LP jobs share the Sippy filter pattern `-rosa-hypershift` on release `4.20`.

## Additional Resources

- Per-LP triage subagent: [per-lp-triage.md](per-lp-triage.md)
- Jira operations subagent: [jira-ops.md](jira-ops.md)
- Known failure patterns (internal RC catalog): [references/failure-patterns.md](references/failure-patterns.md)
- Spreadsheet reference: `../watcher-spreadsheet/reference.md`
- Firefox browser control: `firefox-browser` skill
- 1Password secret access: `onepassword-vault` skill
