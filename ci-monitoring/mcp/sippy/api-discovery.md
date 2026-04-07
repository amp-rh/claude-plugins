# Sippy API Discovery

API documentation for https://sippy.dptools.openshift.org

## Base URL

```
https://sippy.dptools.openshift.org
```

## Authentication

No authentication required (public data).

## Discovered Endpoints

### GET /api/releases

List available OpenShift releases.

**Response:**
```json
{
  "releases": ["4.22", "4.21", "4.20", "4.19", ...],
  "ga_dates": { "4.19": "2025-06-17T00:00:00Z", ... },
  "dates": { ... },
  "last_updated": "2026-01-06T17:11:24.869726Z",
  "release_attrs": {
    "4.19": {
      "name": "4.19",
      "ga": "2025-06-17T00:00:00Z",
      "development_start": "2024-11-25T00:00:00Z",
      "previous_release": "4.18",
      "capabilities": {
        "componentReadiness": true,
        "featureGates": true,
        "metrics": true,
        "payloadTags": true,
        "sippyClassic": true
      }
    }
  }
}
```

### GET /api/jobs

Get CI jobs for a release.

**Parameters:**
- `release` (required): Release version (e.g., "4.19")

**Response:**
```json
[
  {
    "id": 7928,
    "name": "periodic-ci-openshift-...",
    "brief_name": "e2e-aws-ovn",
    "variants": ["Platform:aws", "Architecture:amd64", "Network:ovn", ...],
    "last_pass": "2026-01-06T05:30:30Z",
    "current_pass_percentage": 100,
    "current_runs": 8,
    "current_passes": 8,
    "previous_pass_percentage": 100,
    "net_improvement": 0,
    "test_grid_url": "https://testgrid.k8s.io/...",
    "open_bugs": 0
  }
]
```

**Key Fields:**
- `variants`: Tags like Platform, Architecture, Network, Installer, JobTier
- `current_pass_percentage`: Pass rate for current period
- `current_runs` / `current_passes`: Run counts
- `net_improvement`: Change from previous period
- `open_bugs`: Number of linked bugs

### GET /api/health

Get release health indicators.

**Parameters:**
- `release` (required): Release version

**Response:**
```json
{
  "indicators": {
    "bootstrap": {
      "name": "install should succeed: cluster bootstrap",
      "current_pass_percentage": 99.35,
      "current_runs": 1397,
      "net_improvement": 0.19
    },
    "infrastructure": { ... },
    "install": { ... },
    "upgrade": { ... }
  }
}
```

### GET /api/tests

Get test results for a release.

**Parameters:**
- `release` (required): Release version
- `limit` (optional): Max results

**Response:**
```json
[
  {
    "id": 5346,
    "name": "[sig-storage] In-tree Volumes ...",
    "jira_component": "Storage",
    "current_pass_percentage": 0,
    "current_failures": 1,
    "current_flakes": 0,
    "open_bugs": 0
  }
]
```

## Variant Filters

Jobs can be filtered by variant values:

| Variant | Example Values |
|---------|----------------|
| `Platform` | aws, azure, gcp, metal, vsphere, kubevirt |
| `Architecture` | amd64, arm64, multi |
| `Network` | ovn |
| `Topology` | ha, single, external, microshift |
| `Installer` | ipi, upi, hypershift, agent |
| `JobTier` | blocking, informing, candidate |
| `FeatureSet` | default, techpreview |
| `Upgrade` | none, minor, micro |

## Useful Filters for HCP/OPP Watcher

### ROSA HCP Jobs
- Variant: `Installer:hypershift`
- Variant: `Topology:external`

### OPP/Layered Product Jobs
- Job names containing: `opp`, `layered`, or product-specific patterns

## UI URLs

- Job runs: `https://sippy.dptools.openshift.org/sippy-ng/job_runs/{BUILD_ID}`
- Release view: `https://sippy.dptools.openshift.org/sippy-ng/release/{RELEASE}`

## Notes

- All endpoints return JSON
- Times are in UTC (ISO 8601 format)
- Pass percentages are 0-100 floats
- The API is read-only (no mutations)
