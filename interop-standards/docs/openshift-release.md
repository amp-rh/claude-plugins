# openshift/release — CI Configuration Patterns

**Parent**: @AGENTS.md

Patterns for working with the [openshift/release](https://github.com/openshift/release) repository, which manages CI configurations for OpenShift projects.

## Full Skill Reference

For the complete guide on CI configuration, code generation, and rebase workflows:

→ **Skill**: @../skills/openshift-release-ci/SKILL.md

**Key points:**
- Config files are source of truth (`ci-operator/config/`)
- Job files are generated (`ci-operator/jobs/`) — **never edit directly**
- Run `make update` after config changes, commit both
- Use config-first rebase when job files have conflicts

## Quick Reference

| Directory | Type | Action |
|-----------|------|--------|
| `ci-operator/config/` | **Source** | ✅ Edit this |
| `ci-operator/jobs/` | **Generated** | ❌ Never edit manually |
| `ci-operator/step-registry/` | Source | ✅ Edit carefully |

## Common CI Failures

### `ci-operator-config-metadata`

| Cause | Fix |
|-------|-----|
| Job files edited manually | Run `make update`, commit regenerated files |
| Jobs not regenerated after config change | Run `make update`, commit regenerated files |
| Config/job mismatch after rebase | Use config-first rebase workflow (see skill) |

## Local Repository Setup

```bash
git clone https://github.com/openshift/release.git src/openshift-release
cd src/openshift-release
git remote rename origin upstream
git remote add origin https://github.com/<your-fork>/openshift-release.git
```

## LP-Interop Job Naming Convention

**Required for CR Dashboard integration:** Job names must include `-aws-` (or other platform identifier) in the variant portion so the `platform` parameter can be parsed.

**Pattern**: `<lpName>-ocp<version>-lp-interop-<variant>-aws-<platform>`

**Why**: The Component Readiness Dashboard needs the platform info to properly categorize results. Jobs without platform in the name (e.g., Quay, IBM Fusion) show missing `platform` column and can't be drilled down.

**Update (2026-01-14)**: Per MPEX Leadership feedback — Forrest (TFT/SHIP) creating ticket for frontend filtering to show only `<lpName>-lp-interop` components in CR Dashboard top-level view (source: team Slack, not bundled).

## Reference Links

- [openshift/release repo](https://github.com/openshift/release)
- [CI Operator docs](https://docs.ci.openshift.org/docs/architecture/ci-operator/)
- [Step Registry docs](https://docs.ci.openshift.org/docs/architecture/step-registry/)
- [Component Readiness Dashboard](https://sippy.dptools.openshift.org/sippy-ng/component_readiness/main?view=4.21-LP-Interop)

---

**Learned**: 2025-12-18 — Rebase workflow discovered when rebasing PR #72017 after dependency PRs merged.

See also: @../AGENTS.md for project-level context.
