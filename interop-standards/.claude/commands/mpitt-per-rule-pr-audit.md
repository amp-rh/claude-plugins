# mpitt per-rule PR audit

Run a full mpitt **per-rule** audit on the current openshift/release branch: Phase 0 (rebase, `make update`, scoped diff), batched `Task(subagent_type="mpitt-single-rule-reviewer", ...)` waves, merged violations JSON or table, validation against Lessons Learned, then **stop** unless the user asks to apply fixes in the same turn.

## Instructions for the agent

1. Read and follow `skills/mpitt-per-rule-audit/SKILL.md` in this plugin end to end.
2. Assume repository root is the workspace `openshift-release` unless the user specifies another path.
3. Do **not** skip Phase 0. If the worktree is not clean, stop and tell the user to commit or stash.
4. After Phase 0, build the applicable `ruleId` list from the skill’s rule catalog and in-scope files (`ci-operator/step-registry/**/*-commands.sh`, `ci-operator/config/**/*.yaml`, `M|A|R` only). Detect `set_options_form` for shell tasks.
5. For each applicable batch, invoke `Task(subagent_type="mpitt-single-rule-reviewer", prompt=...)` with **all** required prompt fields from `agents/mpitt-single-rule-reviewer.md` in this plugin and verbatim rule text per task. Use **waves of 4–8** parallel tasks.
6. Aggregate results: dedupe `(file, line, ruleId)`, validate against mpitt-pr-review Lessons Learned and guard rails, output one markdown table or JSON list of violations. Flag likely false positives per the skill.
7. Do **not** implement fixes unless the user explicitly asks in this turn to proceed with fixes (then follow the skill’s implementation section: per-file `mpitt-step-reviewer` / `mpitt-expansion-reviewer` or direct edits, then `make update` and git as needed).
