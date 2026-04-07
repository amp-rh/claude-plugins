---
name: openshift-release-ci
description: Patterns for working with the openshift/release repository, including CI configuration, code generation, and rebase workflows.
---

# openshift/release CI Patterns

Guide for contributing CI configurations to the [openshift/release](https://github.com/openshift/release) repository, which manages CI for all OpenShift projects.

## When to Use This Skill

Use this when:
- Adding or modifying CI configurations for OpenShift projects
- CI jobs are failing with "config-metadata" errors
- Rebasing a PR with conflicts in job files
- Understanding the config → jobs generation workflow
- Troubleshooting rehearsal job failures

## Key Concept: Generated Files

The openshift/release repo uses **code generation**. CI will fail if you edit generated files directly.

| Directory | Type | Action |
|-----------|------|--------|
| `ci-operator/config/` | **Source** | ✅ Edit this |
| `ci-operator/jobs/` | **Generated** | ❌ Never edit manually |
| `ci-operator/step-registry/` | Source | ✅ Edit carefully |

**Rule**: Always edit config files, then regenerate job files.

## Workflow: Config Changes

Standard workflow for adding or modifying CI configurations:

```bash
# 1. Edit config files (source of truth)
vim ci-operator/config/<org>/<repo>/*.yaml

# 2. Regenerate jobs
make update
# OR for specific directory (faster):
make ci-operator-prowgen WHAT="--config-dir ci-operator/config/<org>/<repo>"
make sanitize-prow-jobs WHAT="--prow-jobs-dir /ci-operator/jobs/<org>/<repo>"

# 3. Commit BOTH configs AND generated jobs
git add ci-operator/config/ ci-operator/jobs/
git commit -m "Update CI config for <repo>"
```

**Important**: Always commit both the config changes AND the regenerated job files together.

## Pre-Push Validation Checklist

Before pushing CI config changes, verify step requirements to avoid runtime failures.

### 1. Check Step Requirements

For each step or chain you're adding, check its required env vars:

```bash
# Find the step definition
ls ci-operator/step-registry/**/STEP_NAME/

# Check the ref.yaml for env requirements
cat ci-operator/step-registry/.../STEP_NAME-ref.yaml

# Check the commands.sh for required vars (look for :? syntax)
grep -E '\$\{[A-Z_]+:\?' ci-operator/step-registry/.../STEP_NAME-commands.sh
```

**Example**: For `interop-tests-deploy-cnv`:
```bash
grep -E '\$\{[A-Z_]+:\?' ci-operator/step-registry/interop-tests/deploy-cnv/*-commands.sh
# Output: CNV_VERSION=${CNV_VERSION:?CNV_VERSION environment variable is required}
```

### 2. Check Working Examples

Find configs that already use the same step successfully:

```bash
# Find configs using this step
rg "interop-tests-deploy-cnv" ci-operator/config/ --files-with-matches

# Check how they set the required vars
rg "CNV_VERSION" ci-operator/config/RedHatQE/interop-testing/
```

### 3. Validate Chain Dependencies

When using a chain, check ALL steps in the chain:

```bash
# View the chain definition
cat ci-operator/step-registry/.../CHAIN_NAME-chain.yaml

# For each step listed, check its requirements
```

### 4. Run Local Validation

```bash
# Validate config syntax
SKIP_PULL=true make ci-operator-checkconfig WHAT=path/to/config

# Regenerate jobs (catches some issues)
SKIP_PULL=true make ci-operator-prowgen WHAT=org/repo
SKIP_PULL=true make sanitize-prow-jobs WHAT=org/repo
```

### Common Required Vars

| Step | Required Vars |
|------|---------------|
| `interop-tests-deploy-cnv` | `CNV_VERSION` |
| `interop-tests-deploy-odf` | `ODF_OPERATOR_CHANNEL`, `ODF_VERSION_MAJOR_MINOR` |
| `ipi-install-install` | `BASE_DOMAIN` |

### AWS Zone Configuration

The `ipi-conf-aws` step **dynamically computes** availability zones - you cannot override with a `ZONES` env var.

| Env Var | Effect |
|---------|--------|
| `ZONES` | ❌ **Does NOT work** - overwritten by step |
| `ZONES_COUNT` | ✅ Controls how many zones (default: "auto") |
| `ADD_ZONES` | Whether to add zones at all (default: "yes") |

**ZONES_COUNT values:**
- `"auto"` - 1 zone for presubmits, 2 zones for periodics
- `"1"`, `"2"`, `"3"` - Explicit zone count

**When to use `ZONES_COUNT: "2"`:**
- Metal instances (c6in.metal, c5n.metal) with capacity issues
- Reduce exposure to zone-specific AWS InsufficientInstanceCapacity errors
- Example: us-west-2b often has capacity issues for metal instances

```yaml
env:
  COMPUTE_NODE_TYPE: c6in.metal
  ZONES_COUNT: "2"  # Limit to 2 zones to reduce capacity failure risk
```

## Workflow: Rebasing PRs with Conflicts

When dependency PRs merge and your branch has conflicts in `ci-operator/jobs/`, **do NOT resolve conflicts manually**.

### The Problem

Generated job files are derived from config files. Manually resolving conflicts:
1. Takes a long time (files are huge)
2. Will likely be wrong (generated format is precise)
3. Will fail CI metadata checks

### The Solution: Config-First Rebase

```bash
cd <repo-location>

# 1. Fetch latest upstream
git fetch upstream main

# 2. Create fresh branch from upstream
git checkout -b <branch>-rebased upstream/main

# 3. Checkout ONLY config files from your PR branch
git checkout <branch> -- \
  "ci-operator/config/<org>/<repo>/.config.prowgen" \
  "ci-operator/config/<org>/<repo>/README.md" \
  "ci-operator/config/<org>/<repo>/<your-new-config-files>.yaml"

# 4. Regenerate job files
make ci-operator-prowgen WHAT="--config-dir ci-operator/config/<org>/<repo>"
make sanitize-prow-jobs WHAT="--prow-jobs-dir /ci-operator/jobs/<org>/<repo>"

# 5. Commit all changes
git add -A
git commit -m "Your commit message"

# 6. Force push to update PR
git push origin <branch>-rebased:<branch> --force
```

**Why this works**: Config files are the source of truth. Regenerating from configs avoids manual conflict resolution and ensures output matches what CI expects.

## Common CI Failures

### `ci-operator-config-metadata`

This failure means job files don't match what would be generated from configs.

| Cause | Fix |
|-------|-----|
| Job files edited manually | Run `make update`, commit regenerated files |
| Jobs not regenerated after config change | Run `make update`, commit regenerated files |
| Config/job mismatch | Use config-first rebase workflow |

### Rehearsal Failures

Prow runs "rehearsal" jobs on PRs to test new configurations before merge.

→ **Full guide**: @../pj-rehearse/SKILL.md

**Key rule**: Never run `/pj-rehearse` without a job name — always specify the full job name to avoid wasting CI resources.

### Bash Arithmetic Bug

A common bug in shell scripts:

```bash
# ❌ This FAILS with set -e when VAR=0
((VAR++))

# Why: ((0++)) returns 0 (false), which is exit code 1

# ✅ Fix: Add || true
((VAR++)) || true

# ✅ Or use assignment form
VAR=$((VAR + 1))
```

## Container Registry Authentication

The `make jobs` / `make update` targets pull container images from `quay.io`. Unauthenticated pulls are rate-limited and will fail with `too many requests to registry`.

```bash
# Log in using 1password CLI
op item get <quay-item-id> --fields label=password --reveal | \
  podman login quay.io --username <username> --password-stdin

# Or with SKIP_PULL if images are already cached
SKIP_PULL=true make jobs
```

The 1password vault item for quay.io credentials is in the `RH-Agents` vault.

## Local Repository Setup

Recommended setup for working with openshift/release:

```bash
# Clone to a central location (not inside task directories)
git clone https://github.com/openshift/release.git ~/src/openshift-release
cd ~/src/openshift-release

# Rename origin to upstream (the official repo)
git remote rename origin upstream

# Add your fork as origin
git remote add origin https://github.com/<your-username>/release.git

# Verify remotes
git remote -v
# origin    https://github.com/<your-username>/release.git (fetch)
# upstream  https://github.com/openshift/release.git (fetch)
```

## Step Registry

The step registry (`ci-operator/step-registry/`) contains reusable CI steps, chains, and workflows.

| Component | Purpose | Location |
|-----------|---------|----------|
| **Steps** | Single actions | `step-registry/<category>/<name>/` |
| **Chains** | Sequences of steps | `step-registry/<category>/<name>/chain.yaml` |
| **Workflows** | Full test workflows | `step-registry/<category>/workflow.yaml` |

### Creating New Steps

```bash
# Create step directory
mkdir -p ci-operator/step-registry/<category>/<name>

# Required files:
# - <name>-commands.sh   (the script)
# - <name>-ref.yaml      (step definition)
```

**Step definition example**:
```yaml
ref:
  as: category-name
  from: src
  commands: category-name-commands.sh
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
```

## Checking PR Status

Before force-pushing or making changes:

```bash
# Check if PR is mergeable
gh pr view <number> --json mergeable,mergeStateStatus

# Check CI status
gh pr checks <number>
```

## Anti-Patterns

### ❌ Don't

- Edit files in `ci-operator/jobs/` directly
- Manually resolve conflicts in generated files
- Forget to regenerate after config changes
- Clone the repo inside task directories (use central location)
- Skip rehearsal checks ("it's probably fine")

### ✅ Do

- Edit only config files, regenerate jobs
- Use config-first rebase for conflicts
- Commit configs and jobs together
- Test rehearsals before requesting review
- Keep a single clone with upstream/origin remotes

## Local Testing with CI Operator Emulator

Test Step scripts locally before pushing to CI for faster iteration and real-time debugging.

### Overview

The CI Operator Emulator:
1. Creates an Image Retriever job to build the CI container image
2. Downloads that container image locally
3. Starts a local container mimicking the CI environment
4. Allows repeated script execution without CI round-trips

### Quick Workflow

```bash
# 1. Start emulator session (generates image retriever job config)
ci-op-emulator

# 2. Push generated config to a DUMMY WIP PR (never merge!)
make -C src/ update
git add ci-operator/{config,jobs}/
git commit -m "CI Operator Emulator - Image Retrieval Job"
git push origin HEAD

# 3. Rehearse the image retriever job
/pj-rehearse pull-ci-<org>-<repo>-<branch>-imgRetr-img-retr

# 4. Login to CI build cluster and pull image (within 30 min of job completion)
ci--pull--ctr-img

# 5. Start local container with Step scripts mounted at /ws/step/
ci--start--ctr

# 6. Execute step script inside container
bash '/ws/step/<step-name>-commands.sh' |& tee "${ARTIFACT_DIR}/build.log"
```

### Key Points

| Aspect | Details |
|--------|---------|
| **Image validity** | 30 minutes after job completes |
| **Secrets** | Must populate manually (never use CI-owned secrets) |
| **Step location** | `/ws/step/` inside container |
| **Iteration** | Modify script locally, re-run in container |

### Dummy PR Requirements

The image retriever PR should **never be merged**:
- Add `[WIP]` prefix to title
- Remove reviewers (`/uncc @reviewerNames`)
- Add hold label (`/hold`)
- Set to Draft

→ Full guide: [CI Operator docs](https://docs.ci.openshift.org/docs/architecture/ci-operator/)

## Reference Links

- [openshift/release repository](https://github.com/openshift/release)
- [CI Operator documentation](https://docs.ci.openshift.org/docs/architecture/ci-operator/)
- [Step Registry documentation](https://docs.ci.openshift.org/docs/architecture/step-registry/)
- [How to contribute to the CI system](https://docs.ci.openshift.org/docs/how-tos/contributing/)

## Examples

### Example: Adding a New Test Job

1. **Create config file** (`ci-operator/config/org/repo/org-repo-main.yaml`):
```yaml
base_images:
  cli:
    name: "4.16"
    namespace: ocp
    tag: cli
tests:
- as: e2e
  steps:
    cluster_profile: aws
    test:
    - as: test
      commands: make test
      from: src
      resources:
        requests:
          cpu: 100m
```

2. **Regenerate jobs**:
```bash
make ci-operator-prowgen WHAT="--config-dir ci-operator/config/org/repo"
make sanitize-prow-jobs WHAT="--prow-jobs-dir /ci-operator/jobs/org/repo"
```

3. **Commit both**:
```bash
git add ci-operator/config/org/repo/ ci-operator/jobs/org/repo/
git commit -m "Add e2e test job for org/repo"
```

### Example: Fixing Metadata Failure

```bash
# Pull latest and regenerate
git fetch upstream main
git rebase upstream/main

# If conflicts in jobs/, use config-first rebase
# Otherwise, just regenerate:
make update

git add -A
git commit --amend
git push --force
```

## Related Skills

| Skill | When to Use |
|-------|-------------|
| @../pj-rehearse/SKILL.md | Triggering and managing rehearsal jobs |
| bash-ci-scripts (external, not yet created) | Writing robust bash scripts for CI steps |
| task-extraction (external, not yet created) | Track multi-PR work as tasks |
| handoff-ready-work (external, not yet created) | Document CI debugging for continuity |
