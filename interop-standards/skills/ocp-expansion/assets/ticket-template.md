# {{ TICKET_KEY }}: {{ PRODUCT }} OCP {{ TARGET_VERSION }} {{ TYPE }} Expansion

**Jira**: [{{ TICKET_KEY }}](https://issues.redhat.com/browse/{{ TICKET_KEY }})
**Product**: {{ PRODUCT_FULL_NAME }}
**Type**: {{ TYPE_DESCRIPTION }}
**Epic**: {{ EPIC_KEY }}
**Status**: New
**Assignee**: {{ ASSIGNEE_NAME }} ({{ ASSIGNEE_EMAIL }})

## Source → Target

| Item | Value |
|------|-------|
| Source config | `ci-operator/config/{{ ORG }}/{{ REPO }}/{{ SOURCE_FILENAME }}` |
| Target config | `ci-operator/config/{{ ORG }}/{{ REPO }}/{{ TARGET_FILENAME }}` |
| Branch name | `{{ GIT_BRANCH_NAME }}` |
| Repo | `openshift/release` (fork: `{{ FORK_REPO }}`) |

## Version Changes ({{ SOURCE_VERSION }} → {{ TARGET_VERSION }})

Apply these substitutions to the copied config:

| Field | Old Value | New Value |
|-------|-----------|-----------|
| `releases.latest.candidate.version` | `"{{ SOURCE_OCP }}"` | `"{{ TARGET_OCP }}"` |
| `env.OCP_VERSION` | `"{{ SOURCE_OCP }}"` | `"{{ TARGET_OCP }}"` |
| `env.FIREWATCH_DEFAULT_JIRA_ADDITIONAL_LABELS` | `"{{ SOURCE_LABELS }}"` | `"{{ TARGET_LABELS }}"` |

Do not manually edit `zz_generated_metadata` — `make update` regenerates it from the filename.

## Firewatch Configuration

| Field | Value |
|-------|-------|
| FIREWATCH_DEFAULT_JIRA_ASSIGNEE | `{{ FIREWATCH_ASSIGNEE }}` |
| FIREWATCH_DEFAULT_JIRA_PROJECT | `{{ FIREWATCH_PROJECT }}` |

Verify assignee against [LP Interop - Product QE Contacts](https://docs.google.com/spreadsheets/d/1CBVMbqUsMabSfb-EZ7szijdyC1iH4fKau9rfoW2HTEY/edit?gid=0#gid=0) before submitting.

## Source Config ({{ SOURCE_VERSION }})

```yaml
{{ SOURCE_CONFIG_YAML }}
```

## Checklist

- [ ] Copy source config to target path
- [ ] Update OCP version in all relevant fields
- [ ] Update Jira labels
- [ ] Verify FIREWATCH_DEFAULT_JIRA_ASSIGNEE from contacts spreadsheet
- [ ] Check `.config.prowgen` for job name entries (update if needed)
- [ ] Run `make update` to generate periodics YAML
- [ ] Create PR to `openshift/release`
- [ ] Run rehearsal jobs and add link to PR body
- [ ] Request review
- [ ] Update tracking spreadsheet with PR link
- [ ] Transition Jira ticket
