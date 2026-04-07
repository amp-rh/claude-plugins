---
name: mpitt-pr-review
description: Review GitHub pull requests against mpitt best practices (OpenShift LP QE shell scripting and CI config standards). Use when asked to review a PR in the RedHatQE org, openshift/release expansion PRs, or when the user mentions mpitt best practices. Drafts review comments one at a time, waits for approval, then posts to a pending GitHub review.
---

# mpitt PR Review Workflow

## Best Practices Source

Shell scripting and CI Operator rules come from the MPEX Integrity Engineering
Best Practices, synced into the project as an always-applied Cursor rule:

- **Synced rule file**: `.cursor/rules/mpex-best-practices.mdc` (alwaysApply, auto-injected)
- **Canonical source**: https://edttjredhat.github.io/RHP-Wiki/Confluence/MPEXIENG/Test+Infrastructure/Best+Practises/Section0.html
- **Sync command**: `bash .cursor/skills/sync-best-practices/scripts/sync.sh`

The synced rule covers: shell options (`set -euxo pipefail; shopt -s inherit_errexit`),
`PascalCase` functions, `camelCase`/`typeset` variables, `UPPER_CASE` env vars with
`__` sub-prefix separators, `true` as final statement, xtrace marker rules, secret
handling via `jq --rawfile`, idempotent resource creation, `oc wait` patterns,
resource counting via `jq`, and more.

**Note**: The canonical form is `set -euxo pipefail` but some repos (e.g., openshift/release) enforce a different form via pre-commit hooks (`set -eux -o pipefail`). The orchestrator must detect the repo convention before dispatching subagents and pass it as an override. See [Guard Rails](#guard-rails) and [Convergence Algorithm](#convergence-algorithm).

### Review-Specific Extensions

These rules extend the synced best practices for PR review context:

- SC2155: Never combine `typeset` with command substitution (`typeset var=$(cmd)`) — split into `typeset var=''` then `var=$(cmd)`
- `function` keyword and space before `()` — use `function FuncName ()` not `FuncName()` (enables `typeset` scoping)
- Trap handlers use subshell form `{( ... )}`
- No `>/dev/null` — with xtrace active, stdout suppression hides useful output
- No unused variables — dead assignments waste a subshell and trigger SC2034
- No `|| true` at end of pipelines — with `pipefail`, it suppresses ALL pipe stage failures
- No functions that wrap a single command with `if cmd; then return 0; else return 1; fi` — defeats `set -e`
- No unreachable code after `if/else return` (e.g. `true` after `if ... return; else return; fi`)
- Inline for-loop command substitution when variable is only used for iteration
- No redundant `oc get` after `oc wait` — if wait succeeded, resource is guaranteed to exist
- No redundant `oc get` after polling loop timeout — the loop already determined the outcome
- Step timeout arithmetic: `timeout >= sum(all oc wait --timeout values) + sum(polling loop maxWait) + buffer`
- Consistent label selectors — use `worker=` (empty value) since OCP worker labels have empty values
- Single-command steps — flag steps with 1-3 commands as merge candidates (container lifecycle overhead)

### Pre-flight: Deterministic Checks

Run these before manual review to catch deterministic violations automatically:

```bash
# For expansion PRs (CI config YAML):
python checks/check_expansion.py --pr <URL>

# For step registry PRs (shell scripts):
python checks/check_step_scripts.py --pr <URL>
```

Run these from `skills/mpitt-pr-review/` in this plugin (or pass the script paths relative to that directory).

`check_expansion.py` covers CI config rules programmatically (cli-base-image, test-name-length, FIPS field requirements, version-edit-completeness, cron disabling, CR required fields, URL consistency, prowgen job names, zz_generated_metadata). `check_step_scripts.py` covers shell scripting rules (set flags, typeset usage, SC2155, naming conventions, oc wait patterns, marker detection, heredoc style). Only proceed to manual review for items the scripts cannot catch (e.g., FIREWATCH_CONFIG JSON rule coverage, workflow step correctness, operator channel validity, semantic merge candidates).

### OCP Expansion CI Config Rules

When reviewing expansion PRs (new or modified `ci-operator/config/` YAML files), check for:

- **CLI base image preservation** — `base_images.cli.name` must NOT be bumped to match the target OCP version unless verified compatible. The `cli` image provides the `oc` binary copied into test containers; newer `oc` builds require GLIBC 2.32+ which older test container base images lack. The OCP version under test is controlled by `releases.latest.candidate.version`, not the CLI image. Keep `cli.name` at whatever version the source config used (e.g., `"4.14"`)
- **Combined FIPS/CR config** — FIPS and CR test entries belong in a single config file (the CR config), not separate files. Add FIPS as a second `tests[]` entry with `FIPS_ENABLED: "true"`, `FIREWATCH_CONFIG_FILE_PATH`, `FIREWATCH_FAIL_WITH_TEST_FAILURES: "true"`, and `FIREWATCH_DEFAULT_JIRA_PROJECT: LPINTEROP`. Delete standalone FIPS config files
- **CR variant detection** — `-cr` must NOT be in the config filename (and thus the variant). When FIPS and CR tests share a combined config file, `-cr` in the variant causes two problems: (1) the FIPS periodic job name contains `-cr-...-fips`, making it appear as a CR job in data collection, and (2) the CR periodic gets `-cr-cr` (once from variant, once from the `firewatch-ipi-aws-cr` workflow). Instead, prefix the CR test's `as:` field with `cr-` (e.g., `as: cr-acs-tests-aws`). The CR detection system parses the full Job Run Name (`periodic-ci-<org>-<repo>-<branch>-<variant>-<testName>`) and finds `-cr` in the test name portion. No rehearsal re-run is needed for filename renames
- **Never manually edit `zz_generated_metadata`** — `make update` regenerates it from the filename. Any manual edits get overwritten
- **Version edit completeness** — only these fields should change between versions: `releases.latest.candidate.version`, `env.OCP_VERSION`, `env.FIREWATCH_DEFAULT_JIRA_ADDITIONAL_LABELS`, and branch references in the filename. Fields like `USER_TAGS`, `BASE_DOMAIN`, `CLUSTER_PROFILE` stay unchanged
- **Cron disabling** — disabled periodic jobs use `cron: 0 23 31 2 *` (February 31st, never fires). When adding a 4.N+1 config, the corresponding 4.N non-FIPS cron should be disabled
- **Test name length** — `tests[].as` must not exceed 61 characters (K8s 63-char label limit minus 2-char hash suffix added by CI Operator)
- **FIREWATCH config differences** — FIPS jobs use `FIREWATCH_DEFAULT_JIRA_PROJECT: LPINTEROP` with `FIREWATCH_FAIL_WITH_TEST_FAILURES: "true"` and `FIREWATCH_CONFIG_FILE_PATH`; CR jobs use product-specific Jira projects (e.g., `ROX`, `GITOPSRVCE`) and typically omit these
- **Multi-test config extraction** — some products (e.g., Quay) combine non-FIPS + FIPS tests in a single source config. When creating expansions, extract only the relevant test entry

### Rehearsal Failure Triage

When expansion PR rehearsals fail, always verify the failure against the current (N-1) version before acking:

1. Fetch the rehearsal build log from GCS: `https://storage.googleapis.com/test-platform-results/pr-logs/pull/openshift_release/<PR>/<JOB>/<BUILD>/build-log.txt`
2. Check the existing N-1 periodic job history (fetch from `https://prow.ci.openshift.org/job-history/gs/test-platform-results/logs/<JOB_NAME>`)
3. Compare: if the N-1 job also fails consistently with the same error → product-side, safe to `/pj-rehearse ack`
4. If the N-1 job passes or fails differently → the expansion introduced the issue, fix the config

### Rehearsal Job Name Changes After Config Restructure

When a CI config file is renamed (e.g., combining FIPS and CR into a single file, changing the variant), the generated periodic job names change accordingly. The `pj-rehearse` plugin posts a REHEARSALNOTIFIER comment listing the currently affected jobs every time CI runs. Key rules:

- Always use the job names from the latest REHEARSALNOTIFIER comment, not cached/remembered names from previous pushes
- After a config file rename, old job names become invalid and `/pj-rehearse <old-name>` will return "not found to be affected"
- The `rehearsals-ack` label is removed when new commits are pushed; re-ack is required
- When combining configs (e.g., FIPS into CR file), the variant portion of the job name changes, producing entirely new job names for both test entries

**Delegate rehearsal triage to a subagent** when multiple PRs need analysis — each PR's logs are independent and can be analyzed in parallel via the Task tool.

## Modes

- **Third-party review:** Present items one at a time, draft GitHub comments, wait for approval, post via MCP.
- **Self-review:** When the user owns the PR, skip GitHub posting. Instead, verify findings, fix directly, commit, and push — always, without asking for confirmation. Then run the iterative self-fix convergence loop until a full round completes with zero fixes.
- **Iterative self-fix:** Automated convergence loop using delegated subagents. Each subagent scans a file for violations and fixes them via StrReplace — subagents perform NO git operations. The orchestrator handles all git add/commit/push. After each round, if any file had fixes, a full re-scan round begins. Convergence = one full round where ALL files scan clean. See [Iterative Self-Fix Mode](#iterative-self-fix-mode).
- **Per-rule audit (violations JSON):** One `Task` per applicable rule ID against in-scope changed files. Subagents return **only** structured violations (no fixes, no git, no `make update`). The orchestrator merges JSON, dedupes, validates against the doc and [Lessons Learned](#lessons-learned), then applies edits. See [Per-rule review subagent contract](#per-rule-review-subagent-contract).

**See also:** [mpitt-per-rule-audit](../mpitt-per-rule-audit/SKILL.md) for the dedicated orchestrator (batched Task waves to `mpitt-single-rule-reviewer`, rule catalog stub, merge/validate, optional fix dispatch, and the Command Palette command `mpitt-per-rule-pr-audit`).

## Per-rule review subagent contract

Use this contract when the orchestrator runs **one subagent task per rule ID** (atomic receipts) instead of file-scoped scan+fix. Subagents have no parent chat context: embed the **verbatim rule text** and **full paths** in every prompt. If `../../agents/mpitt-step-reviewer.md` or `../../agents/mpitt-expansion-reviewer.md` in this plugin are missing, use `Task(subagent_type="generalPurpose", ...)` with the same prompt body.

### Rule catalog (local path)

If you maintain a static `ruleId` → rule text table (markdown or JSON), keep it only under the checkout’s `.cursor/` directory, for example `.cursor/RULE_CATALOG`, `.cursor/RULE_CATALOG.md`, or `.cursor/skills/mpitt-pr-review/RULE_CATALOG.json`. Do not place it under versioned paths such as `ci-operator/`. Rely on the usual local-only treatment of `.cursor/` (for example `.git/info/exclude` or your team’s equivalent), not entries in the repo’s shared `.gitignore`, unless your project explicitly versions part of `.cursor/`.

### Applicability filter (mandatory)

Do not dispatch a rule against a file type it cannot judge.

| Rule group | Typical `ruleId` prefix | Applies only to |
|------------|-------------------------|-----------------|
| MPEX Bash (`# Bash Shell Script` in `.cursor/rules/mpex-best-practices.mdc`) | `bash-01` … `bash-10` (optional substeps `bash-10a` … for secrets) | `ci-operator/step-registry/**/*-commands.sh`; optionally `Dockerfile` / `Containerfile` if the PR touches them and the rule is container-related |
| MPEX CI Operator step development (`## Developing Step Script`) | `ci-step-01` … `ci-step-07` | **Step semantics** (idempotent `oc`/`jq`, `oc wait`, `jsonpath-as-json` counting, mocks): `*-commands.sh` only. **Job/env YAML** (e.g. env var naming with `__`): `ci-operator/config/**/*.yaml` only |
| mpitt [Review-Specific Extensions](#review-specific-extensions) | `mpitt-ext-01` … | `ci-operator/step-registry/**/*-commands.sh` |
| GitHub / Container sections in mpex (where paths match shell/container) | (orchestrator-defined IDs) | Same as Bash row: step scripts and, if touched, `Dockerfile` / `Containerfile` |
| [OCP Expansion CI Config Rules](#ocp-expansion-ci-config-rules) | `exp-01` … | `ci-operator/config/**/*.yaml` only |

**Orchestrator steps:** From `git diff --name-status main...HEAD`, keep `M|A|R` (not `D`) paths. Build the **shell queue** and **config queue** from [Phase 0 §4](#4-in-scope-file-filter). For each rule ID, include the task **only** if at least one in-scope path matches that rule’s row in the table above.

### Batched waves (parallelism)

Spawn `Task` calls in **waves of 4 to 8** parallel jobs (stay within tooling limits; do not launch dozens of simultaneous tasks). Within a wave, each task MUST use a **distinct** `ruleId`. Sequences of waves continue until all applicable rule IDs for the current PR have been run.

### Task prompt template (single rule, violations only)

Fill placeholders: `<REPO_ROOT>`, `<BRANCH>`, `<FILE_PATHS>` (newline-separated list of full paths, only in-scope changed files for this rule), `<RULE_ID>`, `<RULE_TEXT>` (verbatim quote from mpex or this skill), `<DIFF_RANGE>` (always `main...HEAD`).

For tasks that target shell scripts, include `<SET_OPTIONS_FORM>` from [Phase 0 §5](#5-set-options-convention-detection-step-scripts) (verbatim line, e.g. `set -eux -o pipefail`). Omit `<SET_OPTIONS_FORM>` for config-only tasks.

```
You are reviewing an openshift/release PR branch for a single mpitt rule.

Repo root: <REPO_ROOT>
Branch: <BRANCH>
Diff range (for context): git diff <DIFF_RANGE>
Files you may inspect (only these): 
<FILE_PATHS>

Rule ID: <RULE_ID>
Rule text (verbatim authority):
<RULE_TEXT>

Instructions:
- Inspect ONLY the listed files. Prefer lines touched in git diff <DIFF_RANGE>, but read full files when the rule requires it (e.g. summed `oc wait` timeouts, workflow structure).
- Report violations of THIS rule only. Do not report issues outside this rule. Do not propose fixes, do not edit files, do not run git, do not run make update.
- Shell/set convention: Set-options form: <SET_OPTIONS_FORM> — do NOT suggest normalizing to a different set form.

Output: Return ONE JSON object matching the schema below. No markdown fences, no prose before or after the JSON.
```

Remove the `Set-options form` bullet and the `<SET_OPTIONS_FORM>` line from the prompt when the task is config-only.

### Violation JSON schema (required output)

Every per-rule task MUST return exactly one JSON object of this shape (empty `violations` if none):

```json
{
  "ruleId": "bash-03",
  "violations": [
    {
      "file": "ci-operator/step-registry/.../foo-commands.sh",
      "line": 42,
      "snippet": "single line or short multi-line excerpt",
      "summary": "one sentence why this violates the rule"
    }
  ]
}
```

Rules: `line` is 1-based. `snippet` should be minimal but identifiable. No additional keys. No trailing commentary.

### Aggregation (orchestrator)

Merge all JSON objects; dedupe on `(file, line, ruleId)`. Optionally merge adjacent lines for the same rule. Drop duplicate findings where two rules describe the same fix (keep the more specific `ruleId`). Then run the [validation gate](#validation-gate-orchestrator-triage) before applying any edit. After triage, follow [Implementation phase (post-validation)](#implementation-phase-post-validation) for edits, `make update`, git steps, and pre-commit.

### Validation gate (orchestrator triage)

Run after aggregation and **before** any `StrReplace`, `make update` for findings, or commit driven by per-rule JSON output. Goal: a **validated list** with columns `ruleId`, `file`, `line`, `action` (brief) containing only genuine, in-scope, convention-aligned fixes.

#### 1. Receipt check

For each merged finding:

- **Authority:** The cited behavior must be actually forbidden by the **verbatim rule** in `.cursor/rules/mpex-best-practices.mdc` or this skill (including [Review-Specific Extensions](#review-specific-extensions) and [OCP Expansion CI Config Rules](#ocp-expansion-ci-config-rules)). If the only justification is taste or unstated team preference, **reject** the finding.
- **Evidence:** The `snippet` at `line` in `file` must match the claimed violation (same construct, not a nearby line mis-attributed).

If the rule text permits the pattern or is ambiguous, **reject** or flag for human-only review; do not auto-fix.

#### 2. Lessons Learned false-positive filter

**Reject** findings whose *fix* would repeat patterns already documented as harmful or invalid in [Lessons Learned](#lessons-learned). Use the lesson index for full narrative; this table is a fast triage checklist.

| If the proposed change would… | See lesson |
|------------------------------|------------|
| Treat stderr capture (`{ cmd 2>&1 1>&3; } 3>&2`, fd juggling) as broken | 21 |
| Replace `oc describe` with `oc get -o yaml` (losing events / formatted status) | 22 |
| Add or remove namerefs inappropriately; expand short-circuit patterns; remove diagnostics from failure branches | 9, 16 |
| Rewrite `if ! cmd` to verbose `if cmd; then true; else` | 13 |
| Add redundant `true` after `if` blocks (POSIX already yields 0) | 26 |
| Remove sole `true` from `then` blocks (invalid empty `then`) | 27, 32 |
| Remove terminal `true` at function end (best practice requires it) | 28 |
| Churn markers (`echo` vs `:`) for hook noise only | 11 |
| Change `base_images.cli.name` to "match" OCP or downgrade without source alignment | 7 |
| Fabricate or remove workflow steps | 8 |
| Normalize trap handlers away from `{( ... )}` | 30 |
| Add `cr-` to non-CR tests; mis-label FIPS; disable crons without context | 17, 31, 33 |
| Reintroduce `jq` when the step context removed it (cli image lacks `jq`) | 34 |

Also apply heuristic **24** (do not burn config scans on pure script-quality PRs with no semantic config changes) when deciding whether config findings are worth acting on, not as a blanket reject of YAML rules.

#### 3. Convention gate

- **Set options:** Reject fixes that normalize `set` to a different form than [Phase 0 §5](#5-set-options-convention-detection-step-scripts) detected for this repo (for example `set -euxo pipefail` vs `set -eux -o pipefail`). Subagent prompts already carry the override; validated edits must not fight it.
- **Hooks:** If pre-commit or repo hooks flag a proposed pattern, prefer **rejecting** the finding over oscillating with the hook (see Lessons Learned **11**, **12**).

#### 4. Scope gate

- **In scope for automated mpitt fixes:** paths that are `M`, `A`, or `R` (not `D`) in `git diff --name-status main...HEAD` **and** match [Phase 0 §4](#4-in-scope-file-filter): `ci-operator/step-registry/**/*-commands.sh` and/or `ci-operator/config/**/*.yaml` as applicable to the rule group ([Applicability filter](#applicability-filter-mandatory)).
- **Out of scope:** Makefile, generated jobs under `ci-operator/jobs/`, prowgen inputs, generic `ref.yaml` / chain YAML (unless the PR’s in-scope work requires coordinated edits explicitly planned), GitHub workflow YAML, OWNERS, `README`, and other paths excluded by Phase 0. Do not route “drive-by” fixes through this pass.

Never use this gate to edit `zz_generated_metadata` by hand; run `make update` after semantic YAML edits per [OCP Expansion CI Config Rules](#ocp-expansion-ci-config-rules).

#### 5. Comment policy (validation)

Synced MPEX text includes “add comments” as a guideline. **Do not** treat “missing comments” as a mandatory validated fix unless the team explicitly requests comment additions for that PR.

#### Output

Produce the validated list (`ruleId`, `file`, `line`, `action`). Implement only those rows. An empty list after triage means **no** edits from this audit round.

## Implementation phase (post-validation)

Use this after the [validation gate](#validation-gate-orchestrator-triage) yields a validated list. Per-rule audit subagents return JSON only; the orchestrator applies fixes and owns follow-up commands.

### Fix application

- Change **only** files and lines backed by the validated list. Prefer `StrReplace` on the listed paths.
- **Shell (`*-commands.sh`):** Follow [Guard Rails](#guard-rails) and [Lessons Learned](#lessons-learned): do not expand short-circuit logic; keep trap handlers in `{( ... )}` form; do not remove `true` from single-statement `then` blocks; do not normalize `set` away from the form from [Phase 0 §5](#5-set-options-convention-detection-step-scripts).
- **Config (`ci-operator/config/**/*.yaml`):** Edit semantics only. Never hand-edit `zz_generated_metadata` or other generator-owned fields; regenerate via `make update` (below).

### `make update` and generated files

- Run `make update` **once** after batched semantic edits to `ci-operator/config/**/*.yaml` so `zz_generated_metadata`, job definitions, and other generated outputs match the repo generator. If a round changes **only** step scripts under `ci-operator/step-registry/**/*-commands.sh`, you typically do **not** need a new `make update` unless [Phase 0](#phase-0-pre-flight-rebase-make-update-diff-scope-set-options) or an earlier step already left configs out of date.
- Subagents never run `make update` ([Lessons Learned](#lessons-learned) item 3). The orchestrator runs it after YAML fixes and before commit when configs changed.
- If image pulls hit rate limits, use `SKIP_PULL=true make update` when the checkconfig image is already local ([Orchestrator Responsibilities](#orchestrator-responsibilities), item 2).

### Git ownership

- **Orchestrator:** `git add`, `git commit`, rebase/amend as in Phase 0, and push after verification. Same split as [Commit Strategy](#commit-strategy): subagents perform no git operations.
- Keep commits limited to in-scope paths from the [scope gate](#4-scope-gate); do not commit drive-by fixes in generated jobs or unrelated files unless a separate, intentional change.

### Pre-commit verification

- Before treating a batch as done or before push, run the repo’s hooks on touched files (for example `pre-commit run --files <path> ...` or full `pre-commit run` if that is the team workflow).
- If hooks warn about `set` form or shell style, align with the convention from [Phase 0 §5](#5-set-options-convention-detection-step-scripts), not a different project’s default.
- Do not push while hooks still report errors on modified files ([Orchestrator Responsibilities](#orchestrator-responsibilities), item 11).

## Iterative Self-Fix Mode

Automated convergence loop for self-owned PRs. The orchestrator delegates file-level scanning to parallel subagents, each of which fixes violations in-place via StrReplace and returns a JSON result. Subagents perform NO git operations — the orchestrator handles all git add, commit, and push. The loop continues until the codebase converges (no more detections).

### Phase 0: Pre-flight (rebase, make update, diff, scope, set-options)

Run these steps **before** collecting the scan queue or dispatching subagents. Order matters.

#### 1. Sync fork and rebase the PR branch

The orchestrator MUST sync the fork and rebase the PR branch onto updated upstream `main`. That way `git diff main...HEAD` reflects **only** the PR's commits, not a long diverged history.

```bash
git fetch upstream
git switch main
git pull --rebase upstream main
git push origin main

git switch -
git rebase main
```

If the rebase has conflicts, stop and report them to the user. Do NOT force-push until the convergence loop completes (push happens after convergence).

#### 2. Regenerate CI metadata (`make update`)

After rebase, run `make update` so CI config YAML matches the repo generator (line wrapping, quoting, indentation). Doing this **before** review or fix loops avoids churn where subagents edit YAML that `make update` would rewrite.

```bash
make update
git add -u && git commit --amend --reset-author --no-edit
```

Use `SKIP_PULL=true make update` when rate-limited and the checkconfig image is already local (see [Orchestrator Responsibilities](#orchestrator-responsibilities)).

#### 3. Enumerate changes with `git diff main...HEAD`

Use **name-status**, not `--name-only`:

```bash
git diff --name-status main...HEAD
```

The range `main...HEAD` is the symmetric difference from the merge-base: commits on the PR branch that are not on `main`. That is the PR change set.

#### 4. In-scope file filter

From that diff, keep paths that are **both** changed as `M`, `A`, or `R` (**not** `D`) **and** under one of:

| Path pattern | Role |
|--------------|------|
| `ci-operator/step-registry/**/*-commands.sh` | Step scripts |
| `ci-operator/config/**/*.yaml` | Expansion configs |

Ignore everything else (Makefile, OWNERS, prowgen, generated jobs, workflow YAML, deleted-only paths, etc.).

```
changed_files = git diff --name-status main...HEAD
scan_queue = [
    f for status, f in changed_files
    if status in ('M', 'A', 'R')
    and (
        (f.startswith('ci-operator/step-registry/') and f.endswith('-commands.sh'))
        or (f.startswith('ci-operator/config/') and f.endswith('.yaml'))
    )
]
```

Per-rule review and third-party review modes use the same filter when limiting work to step scripts and/or config YAML.

#### 5. Set-options convention detection (step scripts)

Before the first shell subagent batch, detect how this repo writes `set` so subagents do not "fix" toward a different form than pre-commit expects.

- **Preferred:** `grep -m1 'set -e' <reference>` on the **first in-scope** `*-commands.sh` from the scan queue.
- **If the PR has no step scripts:** use any established reference under `ci-operator/step-registry/` (for example a file known to pass hooks).

Common forms: `set -euxo pipefail` (canonical MPEX) vs `set -eux -o pipefail` (openshift/release). Pass the detected line verbatim to every step-script prompt as `Set-options form: ...` and instruct subagents not to normalize it.

### PR Scope Filter

Same rules as [Phase 0 §4](#4-in-scope-file-filter). The orchestrator builds `scan_queue` only from `M|A|R` paths matching the step-registry and config patterns above.

### Subagent Type Selection

The orchestrator auto-selects the subagent type based on the file path:

| File Path Pattern | Subagent Type |
|-------------------|---------------|
| `ci-operator/step-registry/**/*-commands.sh` | `mpitt-step-reviewer` |
| `ci-operator/config/**/*.yaml` | `mpitt-expansion-reviewer` |

Mixed PRs (containing both step scripts and config YAML) dispatch both types in the same batch. The dedicated agents embed all rules, so the orchestrator prompt is minimal (file path + mode).

### Convergence Algorithm

The algorithm requires a **full clean round** — every in-scope file must scan clean
with zero fixes in a single pass — before declaring convergence. This prevents
false convergence where 3 files happen to scan clean while 26 others still have
violations.

```
# Phase 0: Pre-flight — rebase, make update, git diff main...HEAD, in-scope filter,
# set-options detection (see Phase 0: Pre-flight section above).
# After rebase + make update, main...HEAD is only the PR's commits with YAML normalized.

# Phase 1: Collect in-scope changed files.
changed_files = git diff --name-status main...HEAD
all_files = [
    f for status, f in changed_files
    if status in ('M', 'A', 'R')
    and (
        (f.startswith('ci-operator/step-registry/') and f.endswith('-commands.sh'))
        or (f.startswith('ci-operator/config/') and f.endswith('.yaml'))
    )
]

set_options_override = detect_repo_convention()

scan_queue = list(all_files)
round_num = 0
round_fix_counts = []  # track fix count per round for trajectory
total_invocations = 0
max_invocations = 4 * len(all_files)  # proportional cap

while True:
    round_num += 1
    round_fixes = 0
    round_false_positives = 0

    while scan_queue and total_invocations < max_invocations:
        batch = scan_queue[:4]
        scan_queue = scan_queue[4:]
        total_invocations += len(batch)

        for file in batch:
            agent = select_agent(file)
            spawn Task(subagent_type=agent, ...)

        fixed_files = []
        for each result:
            if result.fixes > 0:
                # Verify each fix before accepting (check git diff)
                # Revert false positives (oscillation, known bad patterns)
                if is_false_positive(result):
                    git checkout -- result.file
                    round_false_positives += 1
                else:
                    round_fixes += result.fixes
                    fixed_files.append(result.file)

        if fixed_files:
            git add <fixed_files>
            git commit -m "fix: <batch summary>"

    if total_invocations >= max_invocations:
        report("Max invocations reached, stopping for manual review")
        break

    round_fix_counts.append(round_fixes)

    # Convergence check (see Convergence Threshold below)
    if round_fixes == 0:
        break  # fully converged
    if is_practically_converged(round_fix_counts, round_false_positives):
        break  # diminishing returns

    scan_queue = list(all_files)   # full re-scan round
```

### Subagent Scope

Each subagent receives exactly **one file** to scan. This ensures:
- No merge conflicts between parallel fixes (different files).
- Fast iteration (small scope = fast subagent turnaround).

After a fix, the same file is re-enqueued because fixing one violation can expose or create another (e.g., removing an unused variable may leave an orphaned import).

### Subagent Prompt Templates

Subagents do NOT have access to the parent conversation. The dedicated agent definitions (`../../agents/mpitt-step-reviewer.md` and `../../agents/mpitt-expansion-reviewer.md` in this plugin) embed the full rule sets, so per-invocation prompts only need file paths and mode. Subagents must NOT run any git commands — the orchestrator handles all git operations after receiving subagent results.

**Step script (scan+fix):**

```
Task(
  subagent_type="mpitt-step-reviewer",
  description="Scan+fix <filename>",
  prompt="Fix violations in `<filepath>` (repo root: `<repo_root>`). Mode: fix. Do NOT run any git commands. Do NOT run any linter scripts. Do NOT modify any file other than the assigned file. Set-options form: `<set_options_form>` (do NOT normalize to a different form). Return JSON: {\"file\": \"...\", \"fixes\": N, \"details\": [...]}"
)
```

Note: The agent definition already includes rules against expanding short-circuit
patterns, adding namerefs to single-context functions, removing diagnostic `oc get`
from failure branches, and converting markers. These do NOT need to be repeated in
the prompt — they are baked into the agent. Only pass file path, mode, and
set-options form.

**Expansion config (scan+fix):**

```
Task(
  subagent_type="mpitt-expansion-reviewer",
  description="Review <filename>",
  prompt="Fix violations in `<filepath>` (repo root: `<repo_root>`). Source config: `<source_path>`. Mode: fix. Do NOT run any git commands. Do NOT run make update. Do NOT modify any file other than `<filepath>` — the orchestrator handles make update and prowgen after all batches. Do NOT change base_images.cli.name. Return JSON: {\"file\": \"...\", \"fixes\": N, \"details\": [...]}"
)
```

Note: "Do NOT change base_images.cli.name" MUST always be included in expansion
prompts — the CLI rule is the most frequently misapplied rule. The agent definition
now has stronger language but the prompt reinforcement is still needed as defense
in depth.

**Review-only (no fix, just report):**

```
Task(
  subagent_type="mpitt-step-reviewer",  # or mpitt-expansion-reviewer
  description="Review <filename>",
  prompt="Review `<filepath>` (repo root: `<repo_root>`). Mode: review. Do NOT run any git commands. Do NOT modify any files. Set-options form: `<set_options_form>` (do NOT normalize to a different form)."
)
```

### Orchestrator Responsibilities

The orchestrator (parent agent) handles:

1. **Fork sync & rebase** — fetch upstream, fast-forward local `main`, push to fork remote, then rebase the PR branch onto `main`. This ensures `git diff main...HEAD` returns only the PR's changes. See [Phase 0: Pre-flight](#phase-0-pre-flight-rebase-make-update-diff-scope-set-options).
2. **Normalize configs** — run `make update` BEFORE the convergence loop to normalize all config YAML to canonical form. This prevents subagents from wasting effort on formatting changes (line wrapping, value quoting) that `make update` would revert. Amend the rebase commit with the normalized files. If `make update` fails due to container registry rate limiting, use `SKIP_PULL=true make update` when the required image (`quay.io/openshift/ci-public:ci_ci-operator-checkconfig_latest`) is already cached locally (check with `podman images | grep checkconfig`).
3. **Initialization** — collect changed files from `git diff --name-status main...HEAD` (NOT `--name-only`). Filter to in-scope files only: step scripts (`ci-operator/step-registry/**/*-commands.sh`) and config YAML (`ci-operator/config/**/*.yaml`). Exclude deleted files (status `D`), and all files outside these two directories.
4. **Convention detection** — detect the repo's set-options convention (e.g., by checking pre-commit hook output or existing files). Pass the convention to subagents via prompt override to prevent wasted fix/revert cycles.
5. **Queue management** — maintain `scan_queue`, `round_fix_counts`, and false positive tracking.
6. **Subagent dispatch** — in iterative self-fix mode, spawn up to 4 subagents in parallel per batch, one per file. In [per-rule audit](#per-rule-review-subagent-contract) mode, use waves of 4–8 parallel tasks (one `ruleId` per task), not one file per task.
7. **Git operations** — after each batch completes, verify diffs for false positives (oscillation, known bad patterns), revert false positives, then `git add` and `git commit` for accepted fixes. Subagents NEVER touch git.
8. **Spawn on completion** — as each subagent completes with a fix, immediately dispatch the next file from `scan_queue` (do not wait for the full batch).
9. **Cross-cutting pattern propagation** — after EACH batch (not after the full round), run cross-cutting searches for patterns found in that batch. This front-loads known fixes into subsequent batches and dramatically reduces rounds. The orchestrator runs grep searches directly (no subagent needed for simple patterns) and applies StrReplace for each occurrence. For complex patterns, spawn a `generalPurpose` subagent. Cross-cutting subagents count toward the max invocations cap. After cross-cutting fixes, R2 can be scoped to only the files modified in R1 + cross-cut passes (see [R2 Scoping After Cross-Cutting Searches](#r2-scoping-after-cross-cutting-searches)). See [Cross-Cutting Search Patterns](#cross-cutting-search-patterns) for specific patterns to search.
10. **Convergence check** — use the [Convergence Threshold](#convergence-threshold) to determine whether to continue. Track fix trajectory across rounds. Do NOT use "3 consecutive clean" — this false-converges on large file sets.
11. **Post-batch validation** — after committing, verify no pre-commit hook warnings. If the hook flags set-options form mismatches, fix all files to match the repo convention before continuing the convergence loop.
12. **Regenerate derived files** — after convergence (not after each round), run `make update` to regenerate `zz_generated_metadata` and job configs. Commit the regenerated files separately. Subagents NEVER run `make update`. NOTE: Since `make update` was already run in Phase 0, this final run only picks up semantic changes from the convergence loop (not formatting).
13. **Push** — after convergence and final `make update`, push to remote. For self-owned branches after rebase + squash, use `git push -f` directly (not `--force-with-lease`, which fails when the remote was force-pushed in a prior session and the local reflog is stale).
14. **Summary** — after convergence, report total fixes applied, files modified, false positives reverted, and commit history.
15. **Post-run session review** — MANDATORY after every convergence run. Analyze the session for improvements and auto-apply them. See [Post-Run Session Review](#post-run-session-review).

### Commit Strategy

- **Orchestrator owns all git operations** — subagents NEVER run any git commands. They only apply fixes via StrReplace and return results.
- **One commit per batch** — after all subagents in a batch complete, the orchestrator runs `git add <files-with-fixes> && git commit` covering all fixed files in that batch.
- **Squash later** — the iterative loop produces multiple small commits. After convergence, the orchestrator prompts whether to squash per the [best practices squash workflow](#squashing-pr-commits-before-merging-to-upstream-repository-main-branch).
- **Push after convergence** — the orchestrator runs `git push -f origin <branch>` after the convergence loop closes (full clean round or practical convergence).

### Guard Rails

- **Max iterations cap**: `4 * len(all_files)` total subagent invocations (proportional to PR size). A 29-file PR gets 116 invocations max. If not converged by then, stop and report remaining detections for manual review.
- **Deleted file exclusion**: NEVER dispatch a subagent for a file with status `D` (deleted) in `git diff --name-status`. Deleted files don't exist on disk. If dispatched, the subagent may find and modify a similarly-named file in a different directory — a dangerous side effect that requires manual revert.
- **File scope enforcement**: Each subagent must ONLY modify the single file it was assigned. If the file doesn't exist, the subagent returns `fixes: 0` with a "File not found" detail. It must NEVER search for or modify alternative files.
- **Idempotency**: Each subagent reads the file fresh from disk. No cached state between rounds.
- **Conflict prevention**: One file per subagent, no overlapping file assignments within a batch.
- **Set-options convention**: The orchestrator detects the repo's preferred set-options form before the first batch by grepping an existing in-scope file: `grep -m1 'set -e' <first-in-scope-script>`. Common forms: `set -euxo pipefail` (canonical) vs `set -eux -o pipefail` (openshift/release). This form is passed to every subagent prompt. Failing to do so causes wasted iterations where subagents "fix" the form, the hook warns, and the orchestrator must revert.
- **No git in subagents**: Subagents must NEVER run ANY git commands (`git add`, `git commit`, `git pull`, `git rebase`, `git fetch`, `git push`, etc.). Subagents only read files and apply fixes via StrReplace. The orchestrator handles all git operations after each batch completes.
- **Rebase before the loop**: Rebasing onto upstream main happens in Phase 0, before the convergence loop starts. Never during the loop. Force-push happens only after convergence.
- **Path-scope enforcement**: ONLY queue files under `ci-operator/step-registry/` (ending in `-commands.sh`) and `ci-operator/config/` (ending in `.yaml`). All other files (Makefile, OWNERS, prowgen, metadata, non-shell scripts, workflow YAML, ref YAML, chain YAML) are out of scope and must NEVER be dispatched to subagents.

## Workflow

### 1. Fetch the PR

```bash
curl -s "https://api.github.com/repos/<owner>/<repo>/pulls/<num>/files"
```

Fetch file contents via `raw_url` from the response.

### 2. Generate diff anchor URLs

GitHub PR diff links use SHA256 of the file path:

```bash
echo -n "<filepath>" | sha256sum
# → https://github.com/<owner>/<repo>/pull/<num>/files#diff-<hash>R<line>
```

### 3. Review comment format

For each violation, output:

```
## Item N: <title>

**GitHub URL:** <diff anchor url to violation>

**The rule (receipt 1 — <source> line N):**
<url>
<quoted rule text>

**The violation (receipt 2 — <file> line N):**
<url>
<quoted code>

**The comparison (receipt 3 — <correct example> line N, if available):**
<url>
<quoted code>

**Rationale:** <why this matters>
```

### 4. Draft the GitHub comment

After presenting the item, draft the comment in this format and wait for approval:

```
> **<title>**
>
> <rationale with linked receipts>
>
> ```suggestion
> <fixed code replacing the flagged line(s)>
> ```
```

### 5. Post to GitHub (after approval)

Ensure a pending review exists first:

```
GitHub-pull_request_review_write method=create (once per session)
GitHub-add_comment_to_pending_review path=<file> line=<N> side=RIGHT
```

Output the comment URL after posting.

## Suggestion Blocks

GitHub `suggestion` blocks replace the exact line(s) targeted by the comment. Getting line ranges wrong produces broken diffs.

### Rules

1. **Fetch the actual file with line numbers before writing suggestions.** Never assume line numbers from the diff API — verify against the raw file content.
2. **Single-line comment (`line` only):** The suggestion replaces that one line. The suggestion content must be the full replacement for that line.
3. **Multi-line comment (`startLine` + `line`):** The suggestion replaces the entire range inclusive. The suggestion content must be the full replacement for all lines in the range.
4. **Deleting a line:** You cannot produce an empty suggestion. Instead, expand the range to include an adjacent line and include that neighbor in the suggestion content.
   - To delete line N when line N+1 is `foo`: use `startLine=N, line=N+1`, suggestion content = `foo`.
5. **Inserting a line:** Target the line before the insertion point and include both the original line and the new line in the suggestion content.
6. **Validate every suggestion before posting:** Walk through what GitHub will do — "lines X–Y get replaced with this content" — and confirm the result is correct. Watch for accidental duplications.

## Delegation & Subagents

Use dedicated subagent types for domain-specific work. The orchestrator (this skill) retains control of sequencing, approval gates, and GitHub review submission.

### Available Subagent Types

| Subagent Type | Purpose | Agent Definition |
|---------------|---------|------------------|
| `mpitt-step-reviewer` | Scan+fix step registry shell scripts | `../../agents/mpitt-step-reviewer.md` |
| `mpitt-expansion-reviewer` | Scan+fix expansion CI config YAML | `../../agents/mpitt-expansion-reviewer.md` |
| `generalPurpose` (built-in) | Ad-hoc tasks: rehearsal triage, Jira ops | N/A |

### When to Delegate

| Task | Delegate? | Subagent Type |
|------|-----------|---------------|
| Fetch + analyze a single PR's files | No — orchestrator reads directly | — |
| Analyze rehearsal failure logs | Yes — one subagent per PR | `generalPurpose` |
| Expand configs for multiple products | Yes — one subagent per product | `mpitt-expansion-reviewer` |
| Create/update PRs + Jira comments | Yes — one subagent per product | `generalPurpose` |
| Post GitHub review comments | No — orchestrator manages the pending review | — |
| Clone repo, sync upstream | No — sequential prerequisite | — |
| Iterative self-fix: step script | Yes — one subagent per file | `mpitt-step-reviewer` |
| Iterative self-fix: expansion config | Yes — one subagent per file | `mpitt-expansion-reviewer` |
| Iterative self-fix: convergence loop | No — orchestrator tracks counter + queue | — |
| Iterative self-fix: post-convergence squash | No — orchestrator prompts user | — |

### OCP Expansion Subagent Architecture

For expansion workflows (not just reviews), three subagent scopes apply:

1. **Repo setup** (sequential) — clone fork, fetch upstream, verify branch existence. Runs once before any product work starts.
2. **Product expander** (parallel, one per product) — uses `mpitt-expansion-reviewer` to copy source config, apply version edits, and run `make update`. The orchestrator handles branch creation, git add/commit, and push. Products are fully independent (different directories, different branches). FIPS and CR within a product share a branch → sequential within the subagent.
3. **PR lifecycle** (parallel, one per product) — uses `generalPurpose` to create/update PR via GitHub MCP, comment on Jira tickets, transition Jira status, update tracking artifacts.

Reference: the **external** `rosa-hcp-triage` skill (not bundled in this plugin; install globally if you use it) demonstrates the same orchestrator + subagent pattern with its per-LP triage and Jira ops subagents.

### Subagent Invocation Examples

**Step script fix (dedicated agent — rules embedded):**

```
Task(
  subagent_type="mpitt-step-reviewer",
  description="Scan+fix configure-aws-sg",
  prompt="Fix violations in `ci-operator/step-registry/ibm-fusion-access/configure-aws-security-groups/ibm-fusion-access-configure-aws-security-groups-commands.sh` (repo root: `/home/user/openshift-release`). Mode: fix. Do NOT run any git commands. Set-options form: `set -eux -o pipefail` (do NOT normalize to a different form)."
)
```

**Expansion config fix (dedicated agent — rules embedded):**

```
Task(
  subagent_type="mpitt-expansion-reviewer",
  description="Review ACS 4.22 config",
  prompt="Fix violations in `ci-operator/config/redhat-developer/acs-deploy-rhel/redhat-developer-acs-deploy-rhel-main__acs-osd-aws-422.yaml` (repo root: `/home/user/openshift-release`). Source config: `...__acs-osd-aws-421.yaml`. Mode: fix. Do NOT run any git commands."
)
```

**Rehearsal triage (generic — context in prompt):**

```
Task(
  subagent_type="generalPurpose",
  description="Triage GitOps rehearsal logs",
  prompt="Fetch the rehearsal build log for PR #75467 from GCS at <url>. Compare against the 4.21 periodic job history. Classify the failure as config-introduced or pre-existing product-side. Return: failure classification, error signature, and whether /pj-rehearse ack is appropriate."
)
```

Provide each subagent with the full context it needs (URLs, file paths, expected patterns). Subagents do NOT have access to the parent conversation — specify everything in the prompt.

## Lessons Learned

Pitfalls observed in production sessions — avoid repeating these:

1. **"3 consecutive clean" is broken** — With 29 files, scanning 3 clean files
   in a row doesn't mean the codebase converged. A batch of 4 can have 3 clean + 1
   fix, nearly triggering false convergence. Always require a FULL round clean.

2. **Subagents find new violations on re-scan** — Each invocation of the same
   subagent on the same file may find different issues because LLMs are
   non-deterministic. The rules must be exhaustive and explicit. When a new
   violation pattern is discovered, add it to the agent definition immediately
   so future first-pass scans catch it.

3. **Expansion reviewer runs `make update` = disaster** — `make update` modifies
   `.config.prowgen`, job YAML, metadata — files outside the subagent's scope.
   The orchestrator had to revert these changes multiple times. Solution: only
   the orchestrator runs `make update`, after all subagent batches complete.

4. **File renames are structural changes** — Subagents that rename config files
   (e.g., removing `-cr` from the filename) create cascading changes across
   prowgen, job configs, and metadata. These should be flagged as
   `unfixable_structural` and deferred to the orchestrator or a separate PR.

5. **Pre-flight scripts were missing at first** — The skill originally referenced
   `check_expansion.py` and `check_step_scripts.py` before they were implemented.
   Subagents tried to run them and silently skipped. Always keep status markers
   in sync with actual implementation state.

6. **Max iterations cap must be proportional** — A fixed cap of 20 is too low for
   29 files. Use `4 * num_files` to scale with PR size.

7. **CLI base image rule misinterpretation** — Subagents consistently misread
   "must NOT be bumped to match the target OCP version" as "must differ from
   target version." They downgraded `cli.name` from `4.20` to `4.14` or `4.19`
   across multiple passes. Fix: the rule means "don't change cli when creating
   a new version config" — if cli already matches the target in the source
   config, leave it. The orchestrator MUST pass "Do NOT change
   base_images.cli.name" in every expansion subagent prompt.

8. **Expansion reviewer hallucinated workflow steps** — A subagent fabricated
   `mpiit-data-router-reporter` (a step that doesn't exist) and added it to
   a config's post steps. Fix: the expansion agent definition now includes
   "NEVER add or remove workflow steps."

9. **Recurring false positives waste rounds** — Across 5 passes, the same
   rejected patterns (nameref refactoring of AddTestResult, short-circuit
   expansion to if/then, diagnostic `oc get` removal from failure branches)
   were proposed and reverted repeatedly. Fix: these are now baked into the
   agent definitions as explicit "DO NOT" rules, eliminating the need for
   growing constraint blocks in orchestrator prompts.

10. **No diminishing returns detection** — 5 passes produced 56 → 6 → 2 → 2 → 3
    fixes. By pass 3, the branch was effectively converged, but the orchestrator
    had no threshold to stop. Fix: see [Convergence Threshold](#convergence-threshold).

11. **Marker conversion churn** — Converting `echo "msg" 1>&2` to `: "msg"`
    trades one pre-commit hook warning for another. Both forms trigger warnings
    in openshift/release. Fix: the step-reviewer agent now leaves markers as-is
    unless the orchestrator explicitly requests conversion.

12. **`make update` reverts config YAML formatting** — Subagents spent effort
    consolidating multi-line FIREWATCH labels to single lines and quoting cron
    expressions. `make update`'s YAML serializer controls canonical formatting
    and reverted all of it. Fix: run `make update` in Phase 0 (before the loop)
    to normalize configs. The expansion-reviewer agent definition now has an
    explicit "YAML formatting is out of scope" rule.

13. **`if !` → `if ... then true; else` is a new false positive** — A subagent
    converted idiomatic `if ! cmd; then ...` to verbose `if cmd; then true;
    else ...` claiming "errexit safety." The negation in `if` condition is
    safe — conditional context suppresses errexit. Fix: added explicit "Do NOT
    convert `if !`" rule to the step-reviewer agent.

14. **Cross-file pattern propagation reduces rounds** — The same fix pattern
    (SHARED_DIR simplification, echo→printf in EscapeXml) was independently
    "discovered" across 3 rounds in different files. After R1, the orchestrator
    should grep for recurring patterns and apply them proactively to all
    matching files before R2. This front-loads known fixes and reduces the
    number of convergence rounds needed.

15. **Nounset default removal is low-priority noise** — Subagents across
    multiple rounds independently "fixed" `${SHARED_DIR:-}` to `${SHARED_DIR}`
    in different files. While technically correct, this is a trivial style
    change that inflates round fix counts and delays convergence. The agent
    rule now deprioritizes this: only fix nounset defaults when zero other
    violations exist in the file.

16. **Nameref removal despite DO NOT rule** — The step-reviewer agent
    definition said "Do NOT ADD namerefs to single-context functions" but a
    subagent interpreted this as one-directional and REMOVED existing namerefs.
    Fix: the rule now explicitly says "Do NOT ADD OR REMOVE namerefs."

17. **FIPS detection false positive on non-FIPS configs** — The expansion
    reviewer added `"fips"` to `FIREWATCH_DEFAULT_JIRA_ADDITIONAL_LABELS` on
    a config that had `LPINTEROP` project and `FAIL_WITH_TEST_FAILURES` but
    no `FIPS_ENABLED: "true"`. Non-FIPS interop jobs also use those fields.
    Fix: the expansion-reviewer agent now explicitly defines FIPS entry
    detection: "A test entry is FIPS if and only if `FIPS_ENABLED: 'true'`
    is present in its `steps.env`."

18. **Cross-cutting subagents eliminate redundant rounds** — Instead of
    waiting for R2 to independently rediscover the same pattern in other
    files, spawning a `generalPurpose` subagent immediately after R1
    detection to search+fix all in-scope files for the same pattern reduced
    convergence from 3+ rounds to 2. This should be the default behavior,
    not an optimization the user has to request.

19. **Step reviewer misses *missing* diagnostics** — The step reviewer
    correctly preserves existing `oc get` diagnostics in `oc wait` failure
    branches but did not flag when a failure branch was MISSING a diagnostic.
    Fix: added explicit "add missing `oc get` diagnostic in failure branches"
    rule to the step-reviewer agent.

20. **`make update` rate limiting** — `make update` pulls container images
    from `quay.io`. When rate limited, use `SKIP_PULL=true make update` if
    the image is already cached. Check with `podman images | grep checkconfig`.

21. **Stderr capture idiom is a known false positive** — The step-reviewer
    consistently misidentifies `{ cmd 2>&1 1>&3; } 3>&2` as broken, claiming
    it "leaves stderr empty." This is a valid bash idiom for capturing stderr
    into a variable while passing stdout through. The fd-juggling redirections
    work correctly: `2>&1` sends stderr to the capture pipe, `1>&3` sends
    stdout to the terminal. Added explicit "Do NOT modify stderr capture
    redirection patterns" rule to the step-reviewer agent.

22. **`oc describe` vs `oc get -o yaml` serve different purposes** — The
    step-reviewer replaced `oc describe pod` with `oc get pod -o yaml` in
    failure branches, losing event information and human-readable conditions.
    `oc describe` shows events and formatted status; `oc get -o yaml` shows
    raw resource state. Both are valuable. Added explicit "Do NOT replace
    `oc describe`" rule: add `oc get -o yaml` BEFORE the existing describe.

23. **Bare `oc wait` detection is inconsistent across invocations** — The
    same agent definition found bare `oc wait namespace` in test-vm-migration
    (R2) but missed the identical pattern in test-vm-lifecycle (R1). LLM
    non-determinism causes different files to get different treatment. Fix:
    added explicit "Bare oc wait without failure guard" rule to the
    step-reviewer agent, and added specific cross-cutting search patterns
    to the orchestrator (see Cross-Cutting Search Patterns).

24. **Config YAML scans are wasted on script-quality PRs** — All 6 expansion
    config YAMLs scanned clean (0 fixes, 6 wasted invocations) because the
    PR was about step script quality, not config changes. When the commit
    message indicates "script quality" and configs have no semantic changes,
    skip or spot-check configs instead of scanning all of them.

25. **`--force-with-lease` fails on rebased self-owned branches** — After
    Phase 0 rebase + squash, `--force-with-lease` is rejected because the
    local reflog doesn't match the remote (which was force-pushed in a prior
    session). For self-owned branches where the orchestrator just verified
    the branch state, use `git push -f` directly.

26. **Redundant `true` after `if` blocks is a false positive** — A subagent
    added `true` after `if ! oc wait; then ... fi` inside a parent `then`
    block, claiming the `if` would leave non-zero exit status. This is
    incorrect: per POSIX, an `if` statement returns 0 when the condition is
    false and there is no `else` clause. Added explicit "Do NOT Add Redundant
    `true` After `if` Blocks" rule to the step-reviewer agent.

27. **Empty then block creation is a critical false positive** — Subagents
    removed `true` from `if ! cmd; then true fi` patterns (where `true` is
    the ONLY statement in the then block), creating bash syntax errors. An
    empty then block (`if ...; then fi`) is invalid bash. This pattern
    appeared 7 times across R1 in a single session. The `true` inside these
    then blocks exists specifically to make the then block non-empty while
    allowing the `if` to suppress errexit for the command. The step-reviewer
    agent must never remove `true` when it is the sole statement in a then
    block.

28. **Defensive `true` at function end follows best practice** — Subagents
    removed `true` at the end of functions, claiming it was redundant after
    `if ... then exit 1; fi`. While the `if` returns 0 per POSIX, the best
    practice explicitly requires "always have `true` at the end of functions."
    Lesson 26 says do not ADD redundant `true` after `if` blocks, but this
    is about not REMOVING existing `true` at function scope. The two rules
    are complementary, not contradictory: do not add `true` mid-function
    after every `if`, but always keep `true` at the end of functions.

29. **Code restructuring for unused-in-some-path variables is overengineering** —
    A subagent restructured code to avoid a variable being "unused when
    volumeSnapshots == 0" by splitting one API call into two (existence check
    then conditional full fetch). This added latency and complexity for zero
    functional benefit. The original single-fetch pattern was idiomatic and
    efficient. Do not restructure conditional code paths to eliminate variables
    that are unused in some branches if it adds API calls or complexity.

30. **Trap handler `{( ... )}` form must be preserved** — A subagent changed
    `'{( cmd; true )}'` to `'{ ( cmd; true ); }'` claiming the original was
    non-standard. The skill prescribes `{( ... )}` as the trap handler form.
    Do not normalize it to the more verbose `{ ( ... ); }` form.

31. **Expansion reviewer adds `cr-` prefix to IPI tests** — The expansion
    reviewer misidentified IPI (non-CR) test entries as CR and added `cr-`
    prefix to their `as:` field. IPI and CR are different test types. The
    distinguishing signal is `FIREWATCH_CONFIG_FILE_PATH`: CR uses `cr/`
    path, IPI uses `aws-ipi/` path. Fix: added "Do NOT Add `cr-` Prefix
    to Non-CR Test Entries" rule to the expansion-reviewer agent, keyed
    on the firewatch config path.

32. **Step reviewer removes `true` from single-statement `then` blocks** —
    Despite Lesson 27 being documented, the step-reviewer agent definition
    lacked an explicit "Do NOT Remove" rule for this case. A subagent
    removed `true` from `if ! oc describe ...; then true fi`, which would
    create invalid bash syntax. Fix: added explicit "Do NOT Remove `true`
    from Single-Statement `then` Blocks" rule to the step-reviewer agent.

33. **Cron disabling applied to deliberately re-enabled crons** — The
    expansion reviewer disabled the 4.22 CR cron because 4.23 exists,
    but the user had explicitly re-enabled it after reviewer discussion.
    The cron disabling rule applies when CREATING a new version config,
    not retroactively to existing configs. Fix: added "Do NOT Disable
    Crons Without Checking Context" rule to the expansion-reviewer agent.

34. **Step reviewer re-introduces jq after explicit removal** — The
    step-reviewer converted shell heredocs to jq-based marshaling in
    the base install-operator step, despite the commit explicitly
    removing jq dependency because the cli image lacks it. When the
    orchestrator prompt includes "jq unavailable" context, the subagent
    correctly skips the conversion. Lesson: always pass runtime
    constraints to subagents when known.

### Convergence Threshold

After a full round, assess whether further passes are productive:

- **Converged**: 0 genuine fixes in a full round → stop.
- **Practically converged**: ALL of these conditions → stop after applying:
  - All fixes are style-only (not functional — e.g., quoting, variable
    initialization, formatting, nounset defaults).
  - Fix trajectory is non-decreasing OR plateau: R(n) >= R(n-1) when
    both are small (< 10). LLM non-determinism means each round surfaces
    slightly different style-only findings — this does NOT mean convergence
    is failing.
  - Round N >= 3 (minimum 2 full rounds before declaring practical convergence).
  - False positive rate > 30% of reported fixes in the round indicates the
    subagents are running out of real issues and hallucinating fixes.
- **Still converging**: Any functional fix (logic change, API call consolidation,
  resource parameterization) → continue with another round.

**Key insight**: With LLM-based subagents, true zero-fix convergence on style rules
may never occur because non-determinism surfaces ~2-6 trivial findings per round.
After R1 handles the bulk of real issues, R2 catches residuals, and R3 is
dominated by noise. Stopping at R3 with style-only fixes is the pragmatic choice.

When the orchestrator detects the same branch has been reviewed in prior sessions
(check `git log` for squash-and-push patterns), it SHOULD present the fix history
to the user and recommend skipping unless the user explicitly requests another pass.

### Cross-Cutting Search Patterns

After each R1 batch completes with fixes, the orchestrator SHOULD run these grep
searches across ALL in-scope step scripts (not configs) before dispatching the
next batch. These are the most common patterns that subagents find independently
across files, wasting rounds:

1. **`oc get` without `--ignore-not-found` in failure branches:**
   ```bash
   rg 'oc get .* -o yaml$' ci-operator/step-registry/<scope>/ --glob '*-commands.sh'
   ```
   Fix: append `--ignore-not-found` to each match inside a failure branch.

2. **Bare `oc wait` not inside `if` guard:**
   ```bash
   rg '^\s+oc wait ' ci-operator/step-registry/<scope>/ --glob '*-commands.sh' -B2
   ```
   Check context: if the `oc wait` is NOT on an `if` line, it needs wrapping in
   `if ! oc wait ...; then <diagnostic>; exit 1; fi`.

3. **`oc describe` without preceding `oc get -o yaml`:**
   ```bash
   rg 'oc describe ' ci-operator/step-registry/<scope>/ --glob '*-commands.sh' -B1
   ```
   If the line before is NOT an `oc get ... -o yaml`, add one.

These searches are cheap (grep, not LLM) and prevent the most common R2
rediscoveries. Apply fixes directly via StrReplace. Do NOT spawn subagents
for these; the patterns are deterministic.

### Config YAML Scan Heuristic

For self-review PRs where the commit message indicates "script quality" or similar
(not "expansion", "version bump", or "new config"), check whether config YAML
changes are semantic or cosmetic:

```bash
git diff main...HEAD -- ci-operator/config/ | grep -E '^[+-]\s' | grep -vE '(zz_generated|^\+\+\+|^---)'
```

If the diff is empty or only contains `zz_generated_metadata` changes, SKIP config
YAML scanning entirely (or scan 1 file as a spot-check). This avoids wasting 6+
invocations on files that were already clean from prior sessions.

### R2 Scoping After Cross-Cutting Searches

When R1 includes cross-cutting pattern propagation subagents that searched ALL
in-scope files for each detected pattern, a full R2 re-scan of all files is
wasteful. Instead, R2 can be scoped to:

1. **Files modified in R1** (by either per-file subagents or cross-cutting subagents).
2. **A sample of 2-3 unmodified files** as a spot-check for patterns the cross-cutting
   search may have missed.

This is valid because the cross-cutting searches already confirmed no further
occurrences of each detected pattern across all in-scope files. A full R2 is
only needed when R1 did NOT include cross-cutting searches.

If the scoped R2 finds 0 fixes, convergence is achieved. If it finds fixes,
revert to full-round scanning for R3.

### Cross-Session Awareness

When `/mpitt-pr-review` is invoked on a branch that already has a single squashed
commit with an mpitt-style commit message (e.g., "Improve script quality for..."),
the orchestrator should:

1. Check if the commit is the result of prior review passes (look for the commit
   message pattern and single-commit-ahead-of-main).
2. If yes, inform the user: "This branch has been through prior review passes.
   The fix trajectory was [N1 → N2 → N3]. Would you like another pass or is the
   branch ready for PR creation?"
3. Only proceed with a full convergence round if the user explicitly confirms.

## Post-Run Session Review

**MANDATORY** — after every convergence run (self-fix mode), the orchestrator
performs an automated session review and applies improvements to the agent
definitions and skill file. This is NOT optional and does NOT require user
confirmation. The goal is continuous improvement: each run makes the next run
faster and more accurate.

### Data Collection During the Loop

The orchestrator tracks these metrics throughout the convergence loop (not just
at the end):

1. **False positives**: Every `git checkout --` revert, with:
   - The file path
   - The subagent type (`mpitt-step-reviewer` or `mpitt-expansion-reviewer`)
   - A short description of the rejected pattern (e.g., "replaced oc describe
     with oc get -o yaml")
   - Whether the pattern has appeared in prior sessions (check Lessons Learned)

2. **Cross-cutting patterns found late**: Fixes independently discovered in R2+
   that were present in other files during R1. These indicate missing cross-cutting
   search patterns.

3. **Wasted invocations**: Subagent calls that returned `fixes: 0` where the
   file category could have been predicted clean (e.g., config YAMLs on a
   script-quality PR).

4. **Manual orchestrator corrections**: Fixes the orchestrator had to adjust
   after a subagent applied them incorrectly (e.g., adding `oc describe` back
   after subagent removed it).

5. **Missed detections**: Violations that existed in a file during R1 but were
   only caught in R2, by cross-cutting search, or by the orchestrator manually.
   For each miss, record:
   - The file path and the rule that was missed
   - The subagent type that should have caught it
   - The **scope category** from the agent's Scope Map (e.g., `oc-patterns`,
     `shell-options`, `fips-cr`)
   - Whether this rule category has been missed in prior sessions (check
     `.AI_HISTORY.md` for cumulative counts)

   These are distinct from false positives (wrong fixes) and wasted invocations
   (clean files). A missed detection means the subagent scanned the file and
   returned `fixes: 0` or a partial fix set, but a real violation remained.

### Auto-Apply Checklist

After push and summary, the orchestrator walks through each category and applies
improvements directly. No user confirmation needed for these changes.

#### 1. New "DO NOT" Rules for Agent Definitions

For each false positive pattern that was reverted:

- Check if a matching "DO NOT" rule already exists in the agent definition
  (`../../agents/mpitt-step-reviewer.md` or `../../agents/mpitt-expansion-reviewer.md`).
- If NOT present, append a new rule section with:
  - A descriptive heading (`### Do NOT <action>`)
  - An explanation of WHY the pattern is correct/intentional
  - A code example showing the pattern that must be preserved
  - Clear instructions on what to do instead (if applicable)

Use `StrReplace` to insert the new rule after the most topically related existing
rule. Read the agent file first to find the right insertion point.

#### 2. New Cross-Cutting Search Patterns

For each pattern found in R2+ that existed in multiple files during R1:

- Check if the pattern is already in [Cross-Cutting Search Patterns](#cross-cutting-search-patterns).
- If NOT present, add a new numbered entry with:
  - The `rg` command to find occurrences
  - A description of what to check in context
  - The fix template

#### 3. New Lessons Learned Entries

For each novel finding (not already covered by existing lessons 1-25+):

- Append a new numbered entry following the existing format:
  ```
  N. **Short title** — Description of what happened, why it was wrong,
     and what was done to prevent recurrence.
  ```
- Reference any agent rules or skill sections that were updated as part of the fix.

#### 4. Algorithm Refinements

If the session revealed inefficiencies in the convergence algorithm:

- **Scan heuristic**: If a file category was 100% clean, add a heuristic to
  skip or spot-check that category in future runs.
- **Convergence detection**: If practical convergence was reached earlier than
  the algorithm detected, tighten the threshold conditions.
- **Convention detection**: If set-options or other convention mismatches caused
  wasted iterations, improve the detection method.

#### 5. Agent Splitting Assessment

For agents with repeated missed detections, evaluate whether the agent's rule
set is too broad and should be split into smaller, more focused agents.

**Trigger**: A scope category (from the agent's Scope Map) has missed detections
in 2+ sessions. Check `.AI_HISTORY.md` for cumulative missed-detection counts
by category from prior sessions.

**Assessment steps**:

1. Aggregate missed-detection counts by scope category across the current session
   and `.AI_HISTORY.md` entries. A "miss" is any violation the subagent failed to
   catch on its first scan of a file (caught only in R2+, by cross-cutting search,
   or by the orchestrator).
2. Identify categories where the cumulative miss count >= 2. These are split
   candidates.
3. Check whether the agent's total rule count exceeds 20 and whether the split
   candidates form coherent, self-contained groups with minimal cross-dependencies
   (e.g., `oc-patterns` rules rarely interact with `declarations` rules).
4. If splitting is warranted, draft a splitting proposal:
   - Proposed new agent names and descriptions
   - Which rules move to each new agent
   - Updated dispatch logic for the orchestrator (file pattern to agent type mapping)
   - Whether existing rules need duplication across agents (e.g., `shell-options`
     is a prerequisite for all step script agents)

**Output**: Add the splitting proposal to the Session Review Output. If splitting
is NOT warranted, state why (e.g., "miss count below threshold," "categories are
too interdependent to split").

**Recording**: Always update `.AI_HISTORY.md` with the per-category miss counts
for this session, even when no split is recommended. This builds the cumulative
data needed for future assessments.

#### 6. Update `.AI_HISTORY.md`

Append an entry to `<repo_root>/.cursor/.AI_HISTORY.md` (gitignored, local-only)
under today's date heading. This file tracks changes to the mpitt review system
across sessions. Each entry should include:

- What convergence run was performed (branch, file count, trajectory).
- What agent rules, lessons learned, or algorithm changes were added.
- Key metrics (invocations, fixes, false positives, wasted invocations).

Follow the format established in the file: `## YYYY-MM-DD` date headings (newest
first), `### Brief Title` subsections, bullet-point details. If today's date
heading already exists, append new `###` subsections to it.

If the file does not exist, create it with the header:

```markdown
# AI History Log

This file tracks important changes and decisions for the mpitt PR review system
(agents, skills, and workflows) in this project's `.cursor/` directory.
```

### What NOT to Auto-Apply

- **Agent splitting** — creating new agent definition files, deleting or
  renaming existing agents, and updating the dispatch table in this skill.
  Always present as a recommendation in the Session Review Output and wait
  for user approval before executing.
- **Structural changes** to agent definitions (reordering sections, renaming
  headings, merging rules). These require user review.
- **Removal of existing rules**. Only additions are auto-applied. If a rule
  seems obsolete, flag it in the summary for user review.
- **Changes to files outside the allowed set**. The auto-review only modifies:
  - `../../agents/mpitt-step-reviewer.md`
  - `../../agents/mpitt-expansion-reviewer.md`
  - `SKILL.md` (this file, `skills/mpitt-pr-review/SKILL.md` in the plugin)
  - `<repo_root>/.cursor/.AI_HISTORY.md`

  It never modifies the reviewed codebase itself.

### Session Review Output

After applying improvements, output a summary:

```
## Session Review Applied

### Agent Updates
- mpitt-step-reviewer: +N rules (list titles)
- mpitt-expansion-reviewer: +N rules (list titles)

### Skill Updates
- Lessons Learned: +N entries (list numbers and titles)
- Cross-Cutting Patterns: +N patterns (list descriptions)
- Algorithm: <description of changes, if any>

### Metrics
| Metric | Value |
|--------|-------|
| Total invocations | N |
| Genuine fixes | N |
| False positives reverted | N |
| Manual corrections | N |
| Wasted invocations | N |
| Missed detections | N |
| Rounds to convergence | N |

### Agent Splitting Assessment
- mpitt-step-reviewer: <recommendation or "No split needed">
  - Missed detections by category (this session): <category: count, ...>
  - Missed detections by category (cumulative): <category: count, ...>
  - Proposed split: <description or "N/A">
- mpitt-expansion-reviewer: <recommendation or "No split needed">
  - Missed detections by category (this session): <category: count, ...>
  - Missed detections by category (cumulative): <category: count, ...>
  - Proposed split: <description or "N/A">
```

### Skip Conditions

Skip the session review (but still output the summary metrics) when:

- The convergence loop completed in R1 with 0 fixes (nothing to learn from).
- The run was aborted by max invocations cap (incomplete data).
- The user explicitly says "skip review" in the initial prompt.

## GitHub Auth

If GitHub MCP returns 401/403, retrieve the classic PAT (needs `repo` scope):

```
op read "op://RH-Agents/GitHub Personal Access Token/credential"
```

Update `~/.cursor/mcp.json` `GITHUB_PERSONAL_ACCESS_TOKEN` and ask user to reload MCP.
