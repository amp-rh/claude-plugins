# Failure Classification Guide

Decision tree for classifying test failures and determining the appropriate triage path.

## Classification Categories

### 1. Infrastructure/Interop Issues → MPIIT Triage

**Indicators:**
- Cluster provisioning failed
- Network connectivity issues
- Resource quota exhausted
- CI infrastructure problems
- Test framework issues (not product code)

**Examples:**
- `ipi-install-install` step timeout
- AWS resource limit exceeded
- VPN/network flakes
- Missing CI secrets

**Action:**
1. Add `infra-failure` label
2. Retrigger the job
3. Track in MPIIT queue

### 2. Product Bugs → Route to PQE Team

**Indicators:**
- Product component failed during test
- API errors from product services
- Product-specific error messages
- Test passed infra steps but failed product steps

**Examples:**
- ACM hub cluster deployment failed
- ACS policy application error
- ODF storage provisioning failed
- Quay registry connection refused

**Action:**
1. Identify responsible PQE team
2. Update ticket with findings
3. Ping team in Slack
4. Add `product-bug` label

### 3. Transient/Flaky → Retrigger with Label

**Indicators:**
- Failure not reproducible
- Timing-related issues
- Temporary resource unavailability
- Known flaky test

**Examples:**
- Timeout on usually-fast operation
- Resource not ready (but should be)
- Intermittent network error

**Action:**
1. Add `retrigger` label
2. Add `flaky-test` label if known flaky
3. Retrigger the job
4. Monitor next run

## Decision Tree

```
Is cluster provisioning complete?
├── NO → Infrastructure Issue
│   └── Check: AWS limits, network, CI config
│
└── YES → Continue...
    │
    Which step failed?
    ├── Product deployment step → Likely Product Bug
    │   └── Check: Product logs, error messages
    │
    ├── Test execution step → Analyze further
    │   ├── Product API error → Product Bug
    │   ├── Timeout (usually works) → Transient
    │   └── Test framework error → Interop Issue
    │
    └── Unknown → Analyze logs
        ├── Infra error messages → Infrastructure
        ├── Product error messages → Product Bug
        └── No clear cause → Transient (retrigger first)
```

## Product Team Mapping

| Component | PQE Team | Slack Channel |
|-----------|----------|---------------|
| ACM | ACM QE | #forum-acm-qe |
| ACS | ACS QE | #forum-acs-qe |
| ODF | ODF QE | #forum-odf-qe |
| Quay | Quay QE | #forum-quay-qe |
| OCP Core | OCP QE | #forum-ocp-qe |

## Related

- @daily-triage.md — Full triage workflow
- @retrigger-protocol.md — Retrigger steps
- @../slack-channels.md — Team channels
