# ROSA HCP Triage — Known Failure Patterns

Check this catalog before classifying a new failure as unknown. If the error matches, apply the listed classification and action directly.

**RC codes are internal only.** Never include RC codes (e.g. RC-HCP-3) in Jira tickets, spreadsheet comments, Slack pings, reports, or any other external-facing artifact. Use plain-language descriptions of the failure instead.

When a new pattern is found during triage, assign the next available `RC-HCP-N` code and append a new entry at the bottom of this file (above the Quick Reference table). The highest current code is **RC-HCP-5**.

## RC-HCP-1: ROSA CLI Version String Rejected

**Error signature**:
```
ERR: Error getting version: A valid policy version number must be specified
Valid versions: [4.11, 4.12, 4.13, 4.14, 4.15, 4.16, 4.17, 4.18, 4.19, 4.20, 4.21, 4.22]
```

**Failed step**: `rosa-sts-account-roles-create` (pre phase, ~25s)

**Root cause**: Step passes `--version release:latest` to `rosa create account-roles`. The ROSA CLI only accepts a concrete version number. No cluster is ever provisioned so Firewatch does not fire — no ticket is auto-created.

**Classification**: CI / Job configuration

**Owner**: openshift/release maintainers / ROSA QE

**Fix**: Update `rosa-sts-account-roles-create` step to resolve the nightly tag to a numeric version (e.g. `4.19`) before invoking the ROSA CLI.

**Retrigger**: No — identical failure on every run.

**Slack channel**: `#team-qe-lp-triage`, `#wg-openshift-operators-poc-test`

---

## RC-1: AWS Credential Failure (Systemic)

**Error signatures**:
```
AuthFailure: AWS was not able to validate the provided access credentials
InvalidAccessKeyId: The AWS Access Key Id you provided does not exist in our records
```

**Failed step**: `ipi-install-install` or any step requiring AWS API access (pre phase, typically 5–25m)

**Root cause**: The `aws-cspi-qe` cluster profile credentials have expired or been rotated in AWS but not yet updated in the CI vault. Affects all jobs using this profile simultaneously.

**Classification**: Infrastructure — systemic (multiple jobs fail at the same time)

**Owner**: Test Platform team (credential rotation)

**Fix**: Rotate credentials in the CI vault (`aws-cspi-qe` profile, `.awscred` file). Check `#team-qe-lp-triage` for active rotation status before escalating.

**Retrigger**: Only after credentials are confirmed rotated.

**Slack channel**: `#team-qe-lp-triage`

---

## RC-2: AWS Instance Capacity Exhaustion

**Error signature**:
```
InsufficientInstanceCapacity: We currently do not have sufficient <instance-type> capacity in <region>
```

**Failed step**: `ipi-install-install` worker node provisioning (pre phase, ~30m timeout)

**Root cause**: The requested EC2 instance type is unavailable in the target AZ. Common with specialized instance types (e.g. `c5n.metal`) in specific regions (e.g. `ca-central-1a`).

**Classification**: Infrastructure — capacity

**Owner**: Test Platform / job config maintainers

**Fix**: Switch to an available instance type or different AZ. Track any open PRs changing the instance type.

**Retrigger**: Yes — capacity is often restored within hours.

**Slack channel**: `#team-qe-lp-triage`

---

## RC-3: OLM Bundle Unpacking Stuck

**Error signature**:
```
"unpacking is not complete yet, requeueing"
```
Combined with a deployment (e.g. `hco-operator`) that is `NotFound` after many retries, eventually timing out after ~2h.

**Failed step**: Product deployment step (test phase)

**Root cause**: OLM cannot unpack the operator bundle from the index image. Usually tied to a specific IIB image (e.g. `brew.registry.redhat.io/rh-osbs/iib:<id>`).

**Classification**: Product / Operator — needs OLM + product QE investigation

**Owner**: Relevant product QE team (e.g. CNV QE for `kubevirt-hyperconverged`)

**Fix**: Investigate the index image and channel. May require a new IIB build or channel change.

**Retrigger**: No — will time out identically on every run until the bundle is fixed.

**Slack channel**: Product team channel (e.g. `#forum-cnv-qe`)

---

## RC-4: CI Pod Scheduling Failure

**Error signature**:
```
Pod <name> stuck in Pending for >1 hour
```
Containers `sidecar` and `test` never start. Pre-step times out after 1h.

**Failed step**: Any pre-step requiring a pod to be scheduled on a build cluster node

**Root cause**: Build cluster node pressure or scheduling constraints. One-off or systemic depending on recurrence.

**Classification**: CI Infrastructure — pod scheduling

**Owner**: Test Platform team

**Fix**: Monitor for recurrence. If it happens to multiple jobs simultaneously, escalate in `#team-qe-lp-triage`.

**Retrigger**: Yes — one-off scheduling failures typically clear on the next run.

**Slack channel**: `#team-qe-lp-triage` (only if recurring)

---

## RC-HCP-2: VPC CloudFormation Stack DELETE_FAILED

**Error signature**:
```
Deleting stack ci-op-<namespace>-c46c4-vpc ...
Deleted stack ci-op-<namespace>-c46c4-vpc
Waiter StackDeleteComplete failed: terminal failure state: "DELETE_FAILED"
```

**Failed step**: `aws-deprovision-stacks` (post phase, ~17m timeout)

**Root cause**: The VPC CloudFormation stack enters DELETE_FAILED because dependent AWS resources (ENIs, security groups, subnets) remain attached after ROSA cluster deprovision. The stack waiter times out at ~17m18s. Tests pass and results reach ReportPortal — Sippy shows 0% but it is a false negative. Firewatch may not auto-file since the failure is post-phase only.

**Classification**: Infrastructure — AWS cleanup

**Owner**: openshift/release maintainers + aws-perfscale-qe account admin

**Fix**: (1) Manually delete zombie CloudFormation stacks in us-west-2 (aws-perfscale-qe account) — detach dependent resources first, then retry stack deletion. (2) Fix `aws-deprovision-stacks` step ordering to ensure VPC-dependent resources are deleted before stack teardown.

**Retrigger**: No — zombie stacks block cleanup on every subsequent run until cleared from AWS.

**Slack channel**: `#team-qe-lp-triage`, `#wg-openshift-operators-poc-test`

---

## RC-HCP-3: Route 53 Hosted Zone Deletion Failed (HostedZoneNotEmpty)

**Error signature**:
```
operation error Route 53: DeleteHostedZone, https response error StatusCode: 400, HostedZoneNotEmpty: The specified hosted zone contains non-required resource record sets and so cannot be deleted.
```

**Failed step**: `rosa-teardown` (post phase, ~10-15m)

**Root cause**: The ingress hosted zone created during cluster provisioning retains non-required resource record sets (likely leftover DNS records from the ROSA HCP cluster). The rosa-teardown step cannot delete the hosted zone and fails. Tests pass and results reach ReportPortal — Sippy shows 0% but it is a false negative.

**Classification**: Infrastructure (cleanup)

**Owner**: openshift/release maintainers + aws-perfscale-qe account admin

**Fix**: (1) Manually delete orphaned resource record sets from the hosted zone in Route 53 (us-west-2, aws-perfscale-qe account). (2) Fix rosa-teardown to force-delete non-required record sets before deleting the hosted zone.

**Retrigger**: No — zombie hosted zones block teardown on every subsequent run until cleaned from AWS.

**Slack channel**: `#team-qe-lp-triage`, `#wg-openshift-operators-poc-test`

---

## RC-HCP-4: AWS VPC Limit Exceeded (Cascading from Teardown Failures)

**Error signature**:
```
VpcLimitExceeded: The maximum number of VPCs has been reached.
```

**Failed step**: `rosa-setup` (pre phase, ~1-2m)

**Root cause**: The AWS account has reached its VPC quota in the target region (us-west-2). This is a cascading effect of RC-HCP-3 (Route 53 HostedZoneNotEmpty) — failed teardowns leave zombie VPCs that accumulate over multiple test runs until the quota is exhausted. No cluster is provisioned and no tests run.

**Classification**: Infrastructure (AWS quota)

**Owner**: aws-perfscale-qe account admin + openshift/release maintainers

**Fix**: (1) Resolve RC-HCP-3 first (clean orphaned Route 53 records). (2) Delete zombie VPCs. (3) Request VPC quota increase if needed.

**Retrigger**: No — identical failure until VPCs are cleaned up.

**Slack channel**: `#team-qe-lp-triage`, `#wg-openshift-operators-poc-test`

---

## RC-HCP-5: GPU Scheduling Webhook Failure in Build Cluster

**Error signature**:
```
failed calling webhook "gpu-scheduling.ci.openshift.io": failed to call webhook:
Post "https://gpu-scheduling-webhook.gpu-scheduling-webhook.svc:443/mutate--v1-pod?timeout=10s":
no endpoints available for service "gpu-scheduling-webhook"
```

**Failed step**: Any step after the initial test pod completes — `firewatch-report-issues`, `gather-*`, `rosa-teardown`, `send-results-to-reportportal`. Pod creation is rejected by the admission webhook.

**Root cause**: The `gpu-scheduling-webhook` MutatingAdmissionWebhook in the CI build cluster has no running endpoints. When the test pod completes and new pods need to be created for subsequent steps, the webhook intercepts the pod creation request but has no backend to process it, returning an Internal Server Error. This prevents all post-test steps from executing.

**Classification**: CI Infrastructure — build cluster webhook

**Owner**: Test Platform team (build cluster admin)

**Fix**: (1) Restart or redeploy the gpu-scheduling-webhook deployment in the build cluster. (2) If the webhook is not needed for CI workloads, add a namespace exclusion.

**Retrigger**: Yes — after the webhook is restored or removed.

**Slack channel**: `#team-qe-lp-triage`

---

## Classification Quick Reference

| Phase | Error keyword | RC | Retrigger |
|-------|---------------|----|-----------|
| Pre, <1m | `valid policy version` | RC-HCP-1 | No |
| Pre, 1-2m | `VpcLimitExceeded` | RC-HCP-4 | After VPC cleanup |
| Pre, 5–25m | `AuthFailure`, `InvalidAccessKeyId` | RC-1 | After cred rotation |
| Pre, ~30m | `InsufficientInstanceCapacity` | RC-2 | Yes |
| Pre, >1h | Pod `Pending` | RC-4 | Yes |
| Test | `unpacking is not complete yet` | RC-3 | No |
| Post, ~17m | `DELETE_FAILED`, `StackDeleteComplete` | RC-HCP-2 | After AWS cleanup |
| Post, ~10-15m | `DeleteHostedZone`, `HostedZoneNotEmpty` | RC-HCP-3 | After hosted zone cleanup |
| Test/Post, 0s | `gpu-scheduling.ci.openshift.io`, `no endpoints` | RC-HCP-5 | After webhook fix |

## Slack Channel Reference

| Channel | Use for |
|---------|---------|
| `#team-qe-lp-triage` | All infra/CI issues, systemic failures |
| `#wg-openshift-operators-poc-test` | ROSA HCP workflow and cluster profile issues |
| `#forum-qe-mpiit` | General MPIIT team communication |
| `#forum-cnv-qe` | CNV / KubeVirt product bugs |
| `#forum-acs-qe` | ACS product bugs |
| `#forum-odf-qe` | ODF product bugs |
| `#forum-quay-qe` | Quay product bugs |
