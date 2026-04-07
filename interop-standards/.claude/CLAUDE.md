# CLAUDE.md

This directory is an interop testing standards plugin providing codified CI standards, expansion workflows, and automated PR review for OpenShift CI.

## Repository Structure

- `skills/ocp-expansion/` - Declarative OCP expansion workflow with YAML subagent specs
- `skills/openshift-release-ci/` - openshift/release contribution guide
- `skills/pj-rehearse/` - Rehearsal job best practices
- `skills/mpitt-pr-review/` - PR review enforcement with Python linters and staged comments
- `skills/mpitt-per-rule-audit/` - Batched per-rule auditing orchestrator
- `agents/` - Cursor agent definitions (step-reviewer, expansion-reviewer, single-rule-reviewer)
- `.claude/agents/` - Claude Code agent definitions
- `commands/` - Slash commands for audit workflows
- `docs/` - Domain context docs (openshift-release patterns, quality metrics, naming conventions)

## Sub-Agents

Claude-format agent definitions live in `.claude/agents/`:

- `mpitt_step_reviewer.md` - Reviews step-registry shell scripts against mpitt rules
- `mpitt_expansion_reviewer.md` - Reviews CI config YAML against expansion standards
- `mpitt_single_rule_reviewer.md` - Audits files against one specific rule

## Key Workflows

### Expansion (skills/ocp-expansion/)
Three-phase YAML workflow for N to N+1 expansions: repo setup, parallel product expansion, parallel PR lifecycle.

### PR Review (skills/mpitt-pr-review/)
Deterministic Python pre-checks followed by agent-driven review with staged GitHub comments and approval gates.

### Per-Rule Audit (skills/mpitt-per-rule-audit/)
Orchestrates waves of single-rule reviewer subagents, merges violations JSON, optional fix dispatch.
