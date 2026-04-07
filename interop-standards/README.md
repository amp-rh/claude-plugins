# Interop Standards Plugin

Codified interop testing standards for OpenShift CI, packaged as agent-enforceable skills, automated PR review, and declarative expansion workflows. Compatible with both Cursor and Claude Code.

## Components

### Skills

| Skill | Purpose |
|-------|---------|
| `ocp-expansion` | OCP N to N+1 expansion workflow: FIPS + Component Readiness pipelines, parallel product execution, 3-phase YAML workflow with subagent specs |
| `openshift-release-ci` | General openshift/release contribution guide: config vs generated jobs, `make update`, validation, step registry patterns |
| `pj-rehearse` | Rehearsal job best practices: naming, abort/recovery, debugging |
| `mpitt-pr-review` | PR review against mpitt/MPEX best practices with deterministic Python pre-checks and staged GitHub review comments |
| `mpitt-per-rule-audit` | Batched per-rule auditing: dispatches waves of single-rule reviewer subagents, merges violations JSON |

### Agents

| Agent | Purpose |
|-------|---------|
| `mpitt-step-reviewer` | Reviews a single step-registry `*-commands.sh` against shell and mpitt rules |
| `mpitt-expansion-reviewer` | Reviews a single `ci-operator/config/**/*.yaml` against expansion standards |
| `mpitt-single-rule-reviewer` | Audits all files against one specific rule, returns violations JSON |

### Commands

| Command | Purpose |
|---------|---------|
| `mpitt-per-rule-pr-audit` | Run the full per-rule audit workflow on an openshift/release checkout |

### Documentation

| Doc | Purpose |
|-----|---------|
| `openshift-release.md` | CI patterns: config vs jobs, metadata, clone layout, LP-Interop naming for CR dashboard |
| `metrics.md` | Interop team quality KPIs and operational metrics |
| `expansion-guide.md` | Step-by-step expansion process documentation |
| `naming-conventions.md` | Naming rules for CI configs, jobs, and test scenarios |

## Expansion Workflow

The `ocp-expansion` skill includes a declarative 3-phase workflow:

```
Phase 1: repo-setup (clone, fork, fetch upstream)
    |
Phase 2: product-expander (parallel per product)
    |-- Product A: FIPS config + CR config + make update + commit
    |-- Product B: FIPS config + CR config + make update + commit
    |-- ...
    |
Phase 3: pr-lifecycle (parallel per product)
    |-- Open PR + rehearsal + Jira transition
```

Workflow definitions live in `skills/ocp-expansion/workflow/`.

## PR Review Enforcement

The `mpitt-pr-review` skill provides:

- Deterministic Python linters (`checks/check_expansion.py`, `checks/check_step_scripts.py`) for pre-flight validation
- Staged GitHub review comments with approval gates
- Delegation to specialist subagents for step scripts and expansion configs
- Self-fix convergence loops

## Platform Compatibility

### Cursor

`.cursor-plugin/plugin.json` registers agents, skills, commands, and rules.

### Claude Code

`.claude/` provides agent definitions with YAML frontmatter, mirrored commands, and WebFetch permissions.

## External Dependencies

- `agentic-workflows` skill (not bundled): Used by `ocp-expansion` for parallel subagent execution
- `github-mcp` skill (not bundled): Used by `ocp-expansion` for PR operations
- GitHub MCP server: Required for PR review comment posting

## License

Apache-2.0
