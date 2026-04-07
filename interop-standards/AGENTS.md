# Interop Standards Plugin

Codified interop testing standards for OpenShift CI: expansion workflows, PR review enforcement, rule auditing, and best practices documentation.

## Quick Navigation

| Resource | Path | Purpose |
|----------|------|---------|
| Cursor manifest | `.cursor-plugin/plugin.json` | Plugin registration |
| Claude entry | `.claude/CLAUDE.md` | Claude Code context |
| Expansion workflow | `skills/ocp-expansion/workflow/workflow.yaml` | Declarative 3-phase pipeline |
| PR review skill | `skills/mpitt-pr-review/SKILL.md` | Enforcement entry point |

## Skills

| Skill | Path | When to use |
|-------|------|-------------|
| OCP Expansion | `skills/ocp-expansion/SKILL.md` | Running N to N+1 expansions in openshift/release |
| openshift-release CI | `skills/openshift-release-ci/SKILL.md` | Contributing to openshift/release (configs, step registry, validation) |
| pj-rehearse | `skills/pj-rehearse/SKILL.md` | Running and debugging rehearsal jobs |
| mpitt PR Review | `skills/mpitt-pr-review/SKILL.md` | Reviewing PRs against mpitt best practices |
| mpitt Per-Rule Audit | `skills/mpitt-per-rule-audit/SKILL.md` | Batch auditing repo against individual rules |

## Agents

| Agent | Path | Role |
|-------|------|------|
| Step Reviewer | `agents/mpitt-step-reviewer.md` | Single shell script review |
| Expansion Reviewer | `agents/mpitt-expansion-reviewer.md` | Single YAML config review |
| Single Rule Reviewer | `agents/mpitt-single-rule-reviewer.md` | One-rule audit across listed files |

## Commands

| Command | Path |
|---------|------|
| Per-Rule PR Audit | `commands/mpitt-per-rule-pr-audit.md` |

## Documentation

Reference docs under `docs/`:
- `openshift-release.md` - CI patterns and config conventions
- `metrics.md` - Quality KPIs for interop testing
- `expansion-guide.md` - Expansion process guide
- `naming-conventions.md` - Naming rules for configs and jobs

## Architecture

```
mpitt-per-rule-pr-audit (command)
  └── mpitt-per-rule-audit (skill / orchestrator)
        └── [waves of] mpitt-single-rule-reviewer (subagent)
              └── violations.json (merged output)

mpitt-pr-review (skill)
  ├── checks/check_expansion.py (deterministic pre-check)
  ├── checks/check_step_scripts.py (deterministic pre-check)
  ├── mpitt-step-reviewer (subagent per script)
  └── mpitt-expansion-reviewer (subagent per config)

ocp-expansion (skill)
  └── workflow.yaml (3-phase)
        ├── repo-setup.yaml (subagent)
        ├── product-expander.yaml (subagent, parallel per product)
        └── pr-lifecycle.yaml (subagent, parallel per product)
```

## External Dependencies

- `agentic-workflows` skill: Parallel subagent execution for `ocp-expansion`
- `github-mcp` skill: PR operations for `ocp-expansion`
- GitHub MCP server: PR review comment posting for `mpitt-pr-review`
