# Watcher Spreadsheet Reference

**Spreadsheet ID**: `10TLPgFV0qCqa-NVc6agvYRGp19_MK2F-vk-ubEP1Y_Y`

## Sheet Tabs

| Tab Name | GID | Platform |
|----------|-----|----------|
| ROSA HCP 4.20 | 1273894295 | ROSA HCP on AWS |
| OPP 4.21 | _(discover via URL)_ | OpenShift Platform Plus AWS |
| OCP 4.21 FIPS monthly aws-ipi | _(discover via URL)_ | OCP FIPS monthly |
| Useful links+URL_calc | _(reference only)_ | Pre-built Sippy/Prow URLs |

To discover a GID: click the tab in the browser and read `#gid=NNNN` from the URL.

## ROSA HCP 4.20 — Column Layout

Row 8 has test dates. Row 10 has column type headers (`Status`, `Jira`). Columns repeat per test date in pairs:

| Offset | Content |
|--------|---------|
| +0 | Status (`Pass`/`Fail`/`Not Tested`/`Blocked`) |
| +1 | Jira ticket (e.g. `CSPIT-NNNN`, `LPINTEROP-NNNN`) |

### Known Row Assignments (ROSA HCP 4.20)

| Row | LP / Product |
|-----|-------------|
| 11 | MTC _(not onboarded — always "Not Tested")_ |
| 12 | Dev-Spaces |
| 13 | RHSSO |
| 14 | Service Mesh _(not onboarded — always "Not Tested")_ |
| 15 | NFD |
| 16 | OpenShift Pipelines v1.21 |
| 17 | OpenShift-Logging |

### Known Column Assignments (ROSA HCP 4.20)

| Column | Content |
|--------|---------|
| Z | Status (11-Feb-26) |
| AA | Jira (11-Feb-26) |
| AB | Status (18-Feb-26) |
| AC | Jira (18-Feb-26) |
| AD | Comments (free text, append-only) |
| AE | Pass Rate (TEMP) |

### How to Discover New Date Columns

Read row 8 (dates) and row 10 (headers) together. Date columns appear in pairs (Status, Jira). New date pairs are appended to the right, before the Comments column. The Comments column shifts right when new dates are added. Always verify by reading the header row before writing.

```
gviz/tq?tqx=out:csv&sheet=ROSA+HCP+4.20&range=Z10:AH10
```

## OPP 4.21 — Layout

Trigger job: `rhpit-interop-tests-main-weekly_trigger-opp-interop-jobs-trigger`
Test schedule: Mondays (OPP AWS), date column = Sunday before the Monday run.

### Known Row Assignments (OPP 4.21)

| Row | LP / Product |
|-----|-------------|
| 11 | stolostron-policy-collection-main-ocp4.20-interop-opp-aws |
| 12 | stolostron-policy-collection-main-ocp4.21-interop-opp-aws |
| 13 | stolostron-policy-collection-main-ocp4.21-interop-opp-vsphere |
| 14 | OPP TOTAL RESULTS (formula row) |

### Known Column Assignments (OPP 4.21)

| Column | Content |
|--------|---------|
| R | Status (15-Feb-26) |
| S | Jira (15-Feb-26) |
| T | Status (22-Feb-26) |
| U | Jira (22-Feb-26) |

Always verify by reading row 8 (dates) and row 10 (headers) before writing.

## OCP 4.21 FIPS monthly aws-ipi — Layout

Monthly test. Dates are roughly the first Monday of each month.

### Known Row Assignments (OCP 4.21 FIPS)

| Row | LP / Product |
|-----|-------------|
| 11 | ACS (stackrox) |
| 12 | CNV |
| 13 | Gitops v1.19 |
| 14 | MTA 8.0 |
| 15 | OADP 1.5 |
| 16 | ODF |
| 17 | OpenShift Pipelines v1.21 |
| 18 | Quay 3.14 |
| 19 | Serverless |
| 20 | Service Mesh (OSSM) |

### Known Column Assignments (OCP 4.21 FIPS)

| Column | Content |
|--------|---------|
| B | FIPS compliant? |
| C | Status (02-Feb-26) |
| D | Jira (02-Feb-26) |
| E | Status (02-Mar-26) |
| F | Jira (02-Mar-26) |
| K | Comments |
| L | Pass Rate (TEMP) |

## Reading Cell Values

Use the gviz CSV API from an authenticated browser session (requires `credentials: 'include'`):

```javascript
async () => {
  var id = '10TLPgFV0qCqa-NVc6agvYRGp19_MK2F-vk-ubEP1Y_Y';
  var sheet = encodeURIComponent('ROSA HCP 4.20');
  var range = 'AB12:AC17';
  var url = 'https://docs.google.com/spreadsheets/d/' + id + '/gviz/tq?tqx=out:csv&sheet=' + sheet + '&range=' + range;
  var r = await fetch(url, { credentials: 'include' });
  return await r.text();
}
```

## Writing Cell Values

Programmatic writes to Google Sheets are not currently supported:
- **Google Sheets API v4**: Disabled for the GNOME Online Accounts OAuth project (44438659992). Cannot be enabled by the user.
- **DOM keyboard events**: Google Sheets checks `isTrusted` on `KeyboardEvent` — dispatched events are rejected.
- **GVFS mount**: Read-only for Google Sheets (`.gsheet` shortcuts, not editable files).

**Current workflow**: The triage skill outputs a markdown table of proposed changes. The watcher copies these into the spreadsheet manually via the browser UI.

## Output Format for Proposed Changes

When triage is complete, output proposed spreadsheet changes as a markdown table:

```markdown
| Product | Status (<date>) | Jira | Comment (append) |
|---------|-----------------|------|------------------|
| Dev-Spaces | Fail | [CSPIT-NNNN](https://issues.redhat.com/browse/CSPIT-NNNN) | <date> - <RC code>: <summary>. <test result>. |
```

## Kanban Board Labels

Tickets must have the correct labels to appear on the Kanban boards.

### ROSA HCP Board

| Label | Required | Purpose |
|-------|----------|---------|
| `rosa-hcp-lp` | Yes | INTEROP board filter |
| `rosa-hypershift-lp` | Yes | Shared Firewatch/CSPIT board filter |
| `<RELEASE>-lp` (e.g. `4.20-lp`) | Yes | Version filter |
| `infra-failure` | If infra | Classification |

### OPP AWS Board

| Label | Required | Purpose |
|-------|----------|---------|
| `opp-lp` | Yes | OPP board filter |
| `opp-aws-lp` | Yes | Platform filter |
| `self-managed-lp` | If applicable | Self-managed filter |
| `<RELEASE>-lp` (e.g. `4.20-lp`, `4.21-lp`) | Yes | Version filter(s) |
| `infra-failure` | If infra | Classification |

### Firewatch Labels (CSPIT project, auto-filed)

Firewatch adds these automatically — do not manually add to INTEROP tickets:
- `firewatch` — auto-filed marker
- `<full-prow-job-name>` — job name as label
- `<product>-lp` — per-product label (e.g. `devspaces-lp`, `rhsso-lp`)
- `success` / `failure` — result label

## Active Root Causes (as of 2026-02-25)

| RC | Description | Affects |
|----|-------------|---------|
| RC-HCP-1 | ROSA CLI rejects `--version release:latest` (new 2/18) | All ROSA HCP runs |
| RC-HCP-2 | VPC CloudFormation `DELETE_FAILED` post-cleanup (2/10–2/17) | All LP jobs on ROSA HCP |
| RC-HCP-3 | Route 53 `DeleteHostedZone` / `HostedZoneNotEmpty` in rosa-teardown (2/10–present) | Dev-Spaces, RHSSO, NFD, Logging on ROSA HCP 4.20 |
| RC-HCP-4 | `VpcLimitExceeded` in rosa-setup — **RESOLVED 2/25** (clusters provision again) | Pipelines on ROSA HCP 4.20 |
| RC-HCP-5 | `gpu-scheduling-webhook` no endpoints in build cluster (new 2/25) | Pipelines on ROSA HCP 4.20 |
| RC-1 | AWS `AuthFailure` (aws-cspi-qe vault creds) — resolved 2/15 | OPP AWS |
| RC-2 | `c5n.metal` capacity — monitoring | OPP AWS |
| RC-3 | CNV OLM operator stuck unpacking — CNV-78505 | OPP AWS |
| RC-4 | CI pod scheduling failure (`acs-latest` 4.21) | OPP AWS |
