---
name: watcher-spreadsheet
description: Read from and propose updates to the HCP/OPP watcher testing status Google Spreadsheet using an authenticated Firefox session. Reads cell values via the gviz CSV API. Writes are not programmatic — the triage skill generates an HTML report with click-to-copy cells that the user applies manually.
---

> **Configuration**: The spreadsheet ID used throughout this skill defaults to the MPIIT watcher sheet. Override by setting `WATCHER_SPREADSHEET_ID` in your environment.

# Watcher Spreadsheet

**URL**: `https://docs.google.com/spreadsheets/d/10TLPgFV0qCqa-NVc6agvYRGp19_MK2F-vk-ubEP1Y_Y/edit`

Requires an authenticated Firefox session. Follow the `firefox-browser` skill first if no session is active.

## Auth Verification

Run immediately after launching Firefox, before any reads:

```javascript
async () => {
  var id = '10TLPgFV0qCqa-NVc6agvYRGp19_MK2F-vk-ubEP1Y_Y';
  var url = 'https://docs.google.com/spreadsheets/d/' + id + '/gviz/tq?tqx=out:csv&sheet=' + encodeURIComponent('ROSA HCP 4.20') + '&range=A1:A1';
  var r = await fetch(url, { credentials: 'include' });
  var text = await r.text();
  if (r.status !== 200 || text.includes('Sign in')) return 'AUTH FAILED: status=' + r.status;
  return 'AUTH OK: ' + text.slice(0, 80);
}
```

**If `AUTH FAILED`**: Re-run the cookie-scoring profile finder from the `firefox-browser` skill. If "Choose an account / Signed out" appears, tell the user to re-authenticate.

## Reading Cell Values

Use the `gviz/tq` CSV API from within the authenticated browser session. **Must use `credentials: 'include'`** — without it, the fetch returns a sign-in page.

```javascript
async () => {
  var id = '10TLPgFV0qCqa-NVc6agvYRGp19_MK2F-vk-ubEP1Y_Y';
  var sheet = encodeURIComponent('ROSA HCP 4.20');
  var range = 'AB12:AD17';
  var url = 'https://docs.google.com/spreadsheets/d/' + id + '/gviz/tq?tqx=out:csv&sheet=' + sheet + '&range=' + range;
  var r = await fetch(url, { credentials: 'include' });
  return await r.text();
}
```

### Discovering Column Positions

Date columns shift right as new test runs are added. **Always read the date row and header row before assuming column positions:**

```javascript
async () => {
  var id = '10TLPgFV0qCqa-NVc6agvYRGp19_MK2F-vk-ubEP1Y_Y';
  var sheet = encodeURIComponent('ROSA HCP 4.20');
  var base = 'https://docs.google.com/spreadsheets/d/' + id + '/gviz/tq?tqx=out:csv&sheet=' + sheet;
  var r1 = await fetch(base + '&range=A8:AH8', { credentials: 'include' });
  var dates = await r1.text();
  var r2 = await fetch(base + '&range=A10:AH10', { credentials: 'include' });
  var headers = await r2.text();
  return { dates: dates, headers: headers };
}
```

Date columns appear in pairs (Status, Jira). The Comments column follows immediately after the last Jira column. Count positions from column A to map CSV positions to column letters.

## Writing Cell Values

**Programmatic writes to Google Sheets are not supported** in this environment:
- **Google Sheets API v4**: Disabled for the GNOME Online Accounts OAuth project. Cannot be enabled.
- **DOM keyboard events**: Google Sheets checks `isTrusted` — dispatched events are rejected.
- **GVFS mount**: Read-only for Google Sheets files.

### HTML Report Workflow

The triage skill generates an HTML report with click-to-copy cells. The watcher:
1. Opens the HTML report in their default browser (`xdg-open`)
2. Clicks each cell value to copy to clipboard
3. Navigates to the cell in Google Sheets and pastes

See `../rosa-hcp-triage/SKILL.md` Phase 3f for the report generator.

## Column Types

| Column Type | Valid Values |
|-------------|-------------|
| Status | `Pass`, `Fail`, `Not Tested`, `Blocked` |
| Jira | Semicolon-separated ticket keys (e.g. `CSPIT-3058; INTEROP-8875`) |
| Comments | Free text, append-only. New entries start with date prefix: `MM/DD - <note>` |

## Additional Resources

- Sheet GIDs, column layout, and row mapping: [reference.md](reference.md)
- Browser session setup: `firefox-browser` skill
