---
name: mpitt-per-rule-audit
description: Batched per-rule Task audits for mpitt (openshift/release). Spawns waves of mpitt-single-rule-reviewer tasks, merges violations JSON, validates, then optional fixes via the main agent or mpitt-step-reviewer / mpitt-expansion-reviewer.
---

# mpitt per-rule audit (orchestrator)

## When to use

Use this skill when you want **atomic receipts** (one `ruleId` per subagent) and a **merged violations report** before touching code.

Use **[mpitt-pr-review](../mpitt-pr-review/SKILL.md)** iterative self-fix when you want **per-file all-rules** scan+fix loops (`mpitt-step-reviewer`) without splitting by rule.

## Sources of truth

Same as mpitt-pr-review:

- **Synced rule**: `.cursor/rules/mpex-best-practices.mdc` in the checkout
- **Wiki**: https://edttjredhat.github.io/RHP-Wiki/Confluence/MPEXIENG/Test+Infrastructure/Best+Practises/Section0.html
- **Review extensions, expansion bullets, guard rails**: [mpitt-pr-review/SKILL.md](../mpitt-pr-review/SKILL.md) (Review-Specific Extensions, OCP Expansion CI Config Rules, Lessons Learned)

Extend the **rule ID table** below with verbatim rule text as your team stabilizes IDs; optional long form: `reference.md` in this folder.

## Rule catalog (stub)

Grow this table; `ruleId` strings must stay stable for merged reports.

| ruleId | Applicability | Notes |
|--------|---------------|--------|
| `bash-01` … `bash-10` | shell | MPEX Bash section in `mpex-best-practices.mdc` |
| `ci-step-01` … `ci-step-07` | shell and/or yaml | Step semantics vs job/env YAML per row in mpitt-pr-review applicability table |
| `mpitt-ext-01` … | shell | Review-Specific Extensions in mpitt-pr-review |
| `exp-01` … | yaml | OCP Expansion CI Config Rules |

Shell paths: `ci-operator/step-registry/**/*-commands.sh`. Config paths: `ci-operator/config/**/*.yaml`. Do not dispatch a rule against a file type it cannot judge (see [Applicability filter](../mpitt-pr-review/SKILL.md#applicability-filter-mandatory) in mpitt-pr-review).

## Phase 0 (mandatory)

Do **not** skip. If the worktree is not clean, stop and tell the user.

1. **Rebase** the PR branch onto current `main` (fork sync workflow as in mpitt-pr-review).
2. **`make update`** so generated metadata and jobs match the tree (CI Operator PRs).
3. **`git diff main...HEAD`** (or `--name-status`) for scope.
4. **In-scope filter**: from name-status, keep `M`, `A`, `R` only (not `D`). Keep paths under `ci-operator/step-registry/**/*-commands.sh` and `ci-operator/config/**/*.yaml` per [§4 in mpitt-pr-review Phase 0](../mpitt-pr-review/SKILL.md#phase-0-pre-flight-rebase-make-update-diff-scope-set-options).
5. **Set-options convention** for step scripts: detect once (e.g. first in-scope `*-commands.sh`), pass as `set_options_form` in every shell task. See [§5 in mpitt-pr-review](../mpitt-pr-review/SKILL.md#5-set-options-convention-detection-step-scripts).

## Task template

Use `Task(subagent_type="mpitt-single-rule-reviewer", prompt=...)` with **all** fields the agent requires:

- `repo_root`, `files[]` (full paths for this rule only), `ruleId`, **verbatim `RULE_TEXT`**, `artifact_type` (`shell` | `yaml`), and for shell tasks `set_options_form`.

Embed the diff context (`main...HEAD`) so the subagent can prefer touched hunks.

**Waves:** run **4 to 8** parallel tasks per wave; each task in a wave must use a **distinct** `ruleId`. Continue waves until every applicable `(ruleId × file cohort)` batch is done.

Example prompt skeleton (adapt paths and rule text):

```
repo_root: <absolute path>
files:
  - <path1>
  - <path2>
ruleId: <RULE_ID>
artifact_type: shell
set_options_form: <verbatim line from repo>
rule text (verbatim):
<paste rule text>

Diff for preference: git diff main...HEAD
Read only the listed files. Return the JSON schema from `../../agents/mpitt-single-rule-reviewer.md` in this plugin only.
```

For YAML-only tasks, omit `set_options_form` and set `artifact_type: yaml`.

## Merge and validation

1. Parse each returned JSON object. Collect `violations[]` with their `ruleId`.
2. **Dedupe** on `(file, line, ruleId)` (and snippet if needed to disambiguate).
3. **Triage** against [Lessons Learned](../mpitt-pr-review/SKILL.md#lessons-learned) and [Guard Rails](../mpitt-pr-review/SKILL.md#guard-rails) in mpitt-pr-review. Drop false positives and convention mismatches (e.g. do not “fix” `set` away from detected repo form).
4. Produce one **markdown table** or single JSON array for the user before optional fixes.

## Implementation (after validation)

Validated fixes are **per file**, not per rule:

- Dispatch **`mpitt-step-reviewer`** (step scripts) or **`mpitt-expansion-reviewer`** (config YAML) in fix mode, **or** apply edits in the main agent.
- The orchestrator runs **`make update`** when configs change, then **git** add/commit/push. Subagents do not run git or `make update`.

## Cursor command

Entry point for the full orchestrated audit from the Command Palette: **`../../commands/mpitt-per-rule-pr-audit.md`** (relative to this skill file; mirrored under `.claude/commands/mpitt-per-rule-pr-audit.md` for Claude Code)

That command instructs the main agent to load this skill end-to-end, run Phase 0, batch Tasks, merge and validate, print the report, and **ask before applying fixes** unless the user opts in.
