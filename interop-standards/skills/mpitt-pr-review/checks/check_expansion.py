#!/usr/bin/env python3
"""Lint OCP expansion CI config YAML files against deterministic rules.

Usage:
    check_expansion.py --target TARGET [--source SOURCE] [--prowgen PROWGEN]
    check_expansion.py --pr PR_URL [--token TOKEN]

Checks are derived from mpitt-pr-review SKILL.md expansion rules and
findings from prior reviews (PRs #75337, #75413, #75467).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class Severity(IntEnum):
    ERROR = 0
    WARNING = 1
    INFO = 2

    def label(self) -> str:
        return self.name


@dataclass
class Finding:
    severity: Severity
    check: str
    message: str
    file: str = ""
    test_name: str = ""


@dataclass
class CheckContext:
    target: dict[str, Any]
    target_path: str
    source: dict[str, Any] | None = None
    source_path: str = ""
    prowgen: dict[str, Any] | None = None
    prowgen_path: str = ""
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity: Severity, check: str, message: str,
            file: str = "", test_name: str = "") -> None:
        self.findings.append(Finding(
            severity=severity, check=check, message=message,
            file=file or self.target_path, test_name=test_name,
        ))


DISABLED_CRON = "0 23 31 2 *"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_tests(config: dict[str, Any]) -> list[dict[str, Any]]:
    return config.get("tests", [])


def get_env(test: dict[str, Any]) -> dict[str, str]:
    return test.get("steps", {}).get("env", {})


def get_workflow(test: dict[str, Any]) -> str:
    return test.get("steps", {}).get("workflow", "")


def is_fips(test: dict[str, Any]) -> bool:
    return get_env(test).get("FIPS_ENABLED") == "true"


def is_cr(test: dict[str, Any]) -> bool:
    workflow = get_workflow(test)
    return workflow.endswith("-cr") or get_env(test).get("MAP_TESTS") == "true"


def target_ocp_version(config: dict[str, Any]) -> str | None:
    releases = config.get("releases", {})
    latest = releases.get("latest", {})
    for key in ("candidate", "prerelease", "release"):
        if key in latest:
            ver = latest[key].get("version")
            if ver:
                return str(ver)
            bounds = latest[key].get("version_bounds", {})
            if bounds:
                return str(bounds.get("upper", ""))
    return None


def parse_labels_json(raw: str) -> list[str]:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


def variant_from_filename(path: str) -> str:
    basename = Path(path).stem
    parts = basename.split("__", 1)
    if len(parts) == 2:
        return parts[1]
    return ""


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_cli_base_image(ctx: CheckContext) -> None:
    if ctx.source is None:
        return
    source_cli = ctx.source.get("base_images", {}).get("cli", {})
    target_cli = ctx.target.get("base_images", {}).get("cli", {})
    if not source_cli or not target_cli:
        return
    source_name = str(source_cli.get("name", ""))
    target_name = str(target_cli.get("name", ""))
    target_ver = target_ocp_version(ctx.target) or ""
    if source_name != target_name and target_name == target_ver:
        ctx.add(Severity.ERROR, "cli-base-image",
                f"cli base image changed from \"{source_name}\" to "
                f"\"{target_name}\" (matches target OCP version). "
                f"This causes GLIBC mismatches — keep it at \"{source_name}\".")


def check_test_name_length(ctx: CheckContext) -> None:
    for test in get_tests(ctx.target):
        name = test.get("as", "")
        if len(name) > 61:
            ctx.add(Severity.ERROR, "test-name-length",
                    f"Test name \"{name}\" is {len(name)} chars "
                    f"(max 61, K8s 63-char label limit minus 2-char hash).",
                    test_name=name)


def check_fips_jira_project(ctx: CheckContext) -> None:
    for test in get_tests(ctx.target):
        if not is_fips(test):
            continue
        env = get_env(test)
        project = env.get("FIREWATCH_DEFAULT_JIRA_PROJECT", "")
        if project != "LPINTEROP":
            ctx.add(Severity.ERROR, "fips-jira-project",
                    f"FIPS job \"{test.get('as')}\" has "
                    f"FIREWATCH_DEFAULT_JIRA_PROJECT: \"{project}\" "
                    f"(must be \"LPINTEROP\").",
                    test_name=test.get("as", ""))


def check_fips_labels(ctx: CheckContext) -> None:
    for test in get_tests(ctx.target):
        if not is_fips(test):
            continue
        env = get_env(test)
        raw = env.get("FIREWATCH_DEFAULT_JIRA_ADDITIONAL_LABELS", "")
        labels = parse_labels_json(raw)
        if "fips" not in labels:
            ctx.add(Severity.ERROR, "fips-labels",
                    f"FIPS job \"{test.get('as')}\" is missing \"fips\" in "
                    f"FIREWATCH_DEFAULT_JIRA_ADDITIONAL_LABELS.",
                    test_name=test.get("as", ""))


FIPS_DR_REQUIRED_VARS = {"MAP_TESTS", "OCP_VERSION", "REPORT_TO_DR", "REPORTPORTAL_CMP"}


def _fips_has_dr_vars(test: dict[str, Any]) -> bool:
    env = get_env(test)
    return FIPS_DR_REQUIRED_VARS.issubset(env.keys())


def check_fips_config_file_path(ctx: CheckContext) -> None:
    for test in get_tests(ctx.target):
        if not is_fips(test):
            continue
        env = get_env(test)
        path = env.get("FIREWATCH_CONFIG_FILE_PATH", "")
        if not path:
            ctx.add(Severity.ERROR, "fips-config-file-path",
                    f"FIPS job \"{test.get('as')}\" is missing "
                    f"FIREWATCH_CONFIG_FILE_PATH.",
                    test_name=test.get("as", ""))
        elif "cr/lp-interop.json" in path and not _fips_has_dr_vars(test):
            ctx.add(Severity.ERROR, "fips-config-file-path",
                    f"FIPS job \"{test.get('as')}\" uses CR config path "
                    f"(cr/lp-interop.json) without DR/TFA vars. "
                    f"Either add DR vars or use aws-ipi/lp-interop.json.",
                    test_name=test.get("as", ""))


def check_fips_workflow(ctx: CheckContext) -> None:
    for test in get_tests(ctx.target):
        if not is_fips(test):
            continue
        workflow = get_workflow(test)
        if workflow.endswith("-cr") and not _fips_has_dr_vars(test):
            ctx.add(Severity.ERROR, "fips-workflow",
                    f"FIPS job \"{test.get('as')}\" uses CR workflow "
                    f"\"{workflow}\" without DR/TFA vars "
                    f"({', '.join(sorted(FIPS_DR_REQUIRED_VARS))}). "
                    f"Either add the DR vars or use the non-CR workflow.",
                    test_name=test.get("as", ""))


def check_fips_dr_var_completeness(ctx: CheckContext) -> None:
    for test in get_tests(ctx.target):
        if not is_fips(test):
            continue
        env = get_env(test)
        has_any = FIPS_DR_REQUIRED_VARS & env.keys()
        missing = FIPS_DR_REQUIRED_VARS - env.keys()
        if has_any and missing:
            ctx.add(Severity.ERROR, "fips-dr-var-completeness",
                    f"FIPS job \"{test.get('as')}\" has partial DR/TFA vars. "
                    f"Missing: {', '.join(sorted(missing))}.",
                    test_name=test.get("as", ""))


def check_fips_labels_cr_leak(ctx: CheckContext) -> None:
    for test in get_tests(ctx.target):
        if not is_fips(test):
            continue
        env = get_env(test)
        raw = env.get("FIREWATCH_DEFAULT_JIRA_ADDITIONAL_LABELS", "")
        labels = parse_labels_json(raw)
        cr_labels = [l for l in labels if re.match(r"\d+\.\d+-lp-cr", l)]
        if cr_labels:
            ctx.add(Severity.ERROR, "fips-labels-cr-leak",
                    f"FIPS job \"{test.get('as')}\" has CR version labels "
                    f"{cr_labels} in FIREWATCH_DEFAULT_JIRA_ADDITIONAL_LABELS. "
                    f"Use \"<ver>-lp\" without \"-cr\" for FIPS tests.",
                    test_name=test.get("as", ""))


def check_fips_fail_with_test_failures(ctx: CheckContext) -> None:
    for test in get_tests(ctx.target):
        if not is_fips(test):
            continue
        env = get_env(test)
        if env.get("FIREWATCH_FAIL_WITH_TEST_FAILURES") != "true":
            ctx.add(Severity.ERROR, "fips-fail-with-test-failures",
                    f"FIPS job \"{test.get('as')}\" is missing "
                    f"FIREWATCH_FAIL_WITH_TEST_FAILURES: \"true\".",
                    test_name=test.get("as", ""))


def check_version_edit_completeness(ctx: CheckContext) -> None:
    if ctx.source is None:
        return
    source_ver = target_ocp_version(ctx.source) or ""
    target_ver = target_ocp_version(ctx.target) or ""
    if not source_ver or not target_ver:
        return

    for test_s, test_t in zip(get_tests(ctx.source), get_tests(ctx.target)):
        env_s = get_env(test_s)
        env_t = get_env(test_t)
        version_env_keys = {"OCP_VERSION", "FIREWATCH_DEFAULT_JIRA_ADDITIONAL_LABELS"}
        all_keys = set(env_s.keys()) | set(env_t.keys())
        for key in sorted(all_keys):
            val_s = env_s.get(key, "")
            val_t = env_t.get(key, "")
            if val_s == val_t:
                continue
            if key in version_env_keys:
                continue
            change_is_version_only = (
                val_s.replace(source_ver, "") == val_t.replace(target_ver, "")
            )
            if change_is_version_only:
                continue
            ctx.add(Severity.WARNING, "version-edit-completeness",
                    f"Unexpected env change in \"{test_t.get('as', '')}\": "
                    f"{key} differs beyond version bump.",
                    test_name=test_t.get("as", ""))


def check_source_cron_disabled(ctx: CheckContext) -> None:
    if ctx.source is None:
        return
    for test in get_tests(ctx.source):
        if is_fips(test):
            continue
        cron = test.get("cron", "")
        if cron and cron != DISABLED_CRON:
            ctx.add(Severity.WARNING, "source-cron-disabled",
                    f"Source config test \"{test.get('as')}\" has active cron "
                    f"\"{cron}\" — should be disabled (\"{DISABLED_CRON}\") "
                    f"when the newer version is active.",
                    file=ctx.source_path, test_name=test.get("as", ""))


def check_cr_required_fields(ctx: CheckContext) -> None:
    for test in get_tests(ctx.target):
        if not is_cr(test):
            continue
        env = get_env(test)
        missing = []
        if "MAP_TESTS" not in env:
            missing.append("MAP_TESTS")
        if "OCP_VERSION" not in env:
            missing.append("OCP_VERSION")
        if "REPORTPORTAL_CMP" not in env:
            missing.append("REPORTPORTAL_CMP")
        if missing:
            ctx.add(Severity.WARNING, "cr-required-fields",
                    f"CR job \"{test.get('as')}\" is missing env vars: "
                    f"{', '.join(missing)}.",
                    test_name=test.get("as", ""))


def check_url_format_consistency(ctx: CheckContext) -> None:
    urls: list[tuple[str, str]] = []
    for test in get_tests(ctx.target):
        env = get_env(test)
        url = env.get("FIREWATCH_CONFIG_FILE_PATH", "")
        if url:
            urls.append((test.get("as", ""), url))
    if len(urls) < 2:
        return

    def extract_ref(url: str) -> str:
        match = re.search(
            r"githubusercontent\.com/[^/]+/[^/]+/(refs/heads/[^/]+|[^/]+)/",
            url)
        return match.group(1) if match else ""

    ref_patterns = {extract_ref(url) for _, url in urls if extract_ref(url)}
    if len(ref_patterns) > 1:
        ctx.add(Severity.WARNING, "url-format-consistency",
                f"FIREWATCH_CONFIG_FILE_PATH URLs use inconsistent ref "
                f"formats: {', '.join(sorted(ref_patterns))}. "
                f"Use the same format across all tests.")


def check_prowgen_job_names(ctx: CheckContext) -> None:
    if ctx.prowgen is None:
        return
    reporters = ctx.prowgen.get("slack_reporter", [])
    all_job_names: set[str] = set()
    for reporter in reporters if isinstance(reporters, list) else [reporters]:
        for name in reporter.get("job_names", []):
            all_job_names.add(name)
    if not all_job_names:
        return
    for test in get_tests(ctx.target):
        name = test.get("as", "")
        if name and name not in all_job_names:
            ctx.add(Severity.WARNING, "prowgen-job-names",
                    f"Test \"{name}\" is not listed in "
                    f".config.prowgen job_names.",
                    file=ctx.prowgen_path, test_name=name)


def check_fips_cron_disabled(ctx: CheckContext) -> None:
    for test in get_tests(ctx.target):
        if not is_fips(test):
            continue
        cron = test.get("cron", "")
        if cron and cron != DISABLED_CRON:
            ctx.add(Severity.INFO, "fips-cron-disabled",
                    f"FIPS job \"{test.get('as')}\" has active cron "
                    f"\"{cron}\". New FIPS jobs typically start disabled.",
                    test_name=test.get("as", ""))


def check_variant_cr_leak(ctx: CheckContext) -> None:
    variant = variant_from_filename(ctx.target_path)
    if not variant:
        return
    has_fips = any(is_fips(t) for t in get_tests(ctx.target))
    has_cr = any(is_cr(t) for t in get_tests(ctx.target))
    if has_fips and has_cr and "-cr" in variant:
        ctx.add(Severity.ERROR, "variant-cr-leak",
                f"Variant \"{variant}\" contains \"-cr\" but config has both "
                f"FIPS and CR tests. This causes FIPS periodic job names to "
                f"include \"-cr\", misclassifying them as CR in data "
                f"collection. Remove \"-cr\" from the filename and prefix "
                f"the CR test's as: field with \"cr-\" instead.")


def check_zz_generated_metadata(ctx: CheckContext) -> None:
    meta = ctx.target.get("zz_generated_metadata", {})
    variant = meta.get("variant", "")
    expected = variant_from_filename(ctx.target_path)
    if not variant or not expected:
        return
    if variant != expected:
        ctx.add(Severity.INFO, "zz-generated-metadata",
                f"zz_generated_metadata.variant \"{variant}\" does not "
                f"match filename variant \"{expected}\".")


ALL_CHECKS = [
    check_cli_base_image,
    check_test_name_length,
    check_fips_jira_project,
    check_fips_labels,
    check_fips_config_file_path,
    check_fips_workflow,
    check_fips_dr_var_completeness,
    check_fips_labels_cr_leak,
    check_fips_fail_with_test_failures,
    check_version_edit_completeness,
    check_source_cron_disabled,
    check_cr_required_fields,
    check_url_format_consistency,
    check_prowgen_job_names,
    check_fips_cron_disabled,
    check_variant_cr_leak,
    check_zz_generated_metadata,
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_checks(ctx: CheckContext) -> list[Finding]:
    for check_fn in ALL_CHECKS:
        check_fn(ctx)
    return ctx.findings


def format_findings(findings: list[Finding]) -> str:
    if not findings:
        return "All checks passed."
    findings.sort(key=lambda f: (f.severity, f.check))
    lines: list[str] = []
    for i, f in enumerate(findings, 1):
        prefix = f"[{f.severity.label()}]"
        loc = f.file
        if f.test_name:
            loc += f" (test: {f.test_name})"
        lines.append(f"{i}. {prefix} {f.check}: {f.message}")
        if loc:
            lines.append(f"   File: {loc}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GitHub PR fetching
# ---------------------------------------------------------------------------

def fetch_pr_files(pr_url: str, token: str | None = None) -> list[dict[str, Any]]:
    if requests is None:
        print("ERROR: 'requests' package required for --pr mode. "
              "Install with: pip install requests", file=sys.stderr)
        sys.exit(1)

    match = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if not match:
        print(f"ERROR: Cannot parse PR URL: {pr_url}", file=sys.stderr)
        sys.exit(1)

    owner, repo, number = match.group(1), match.group(2), match.group(3)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}/files"
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    resp = requests.get(api_url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_raw(url: str, token: str | None = None) -> str:
    assert requests is not None
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"token {token}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


CI_CONFIG_DIR = "ci-operator/config/"
PROWGEN_FILENAME = ".config.prowgen"


def is_ci_config(path: str) -> bool:
    return (path.startswith(CI_CONFIG_DIR)
            and path.endswith(".yaml")
            and PROWGEN_FILENAME not in path
            and "/jobs/" not in path)


def run_from_pr(pr_url: str, token: str | None = None) -> list[Finding]:
    files = fetch_pr_files(pr_url, token)

    added_configs: list[dict[str, Any]] = []
    modified_configs: list[dict[str, Any]] = []
    prowgen_file: dict[str, Any] | None = None

    for f in files:
        path = f["filename"]
        if path.endswith(PROWGEN_FILENAME):
            prowgen_file = f
        elif is_ci_config(path):
            if f["status"] == "added":
                added_configs.append(f)
            elif f["status"] == "modified":
                modified_configs.append(f)

    all_findings: list[Finding] = []

    prowgen_data = None
    prowgen_path = ""
    if prowgen_file:
        prowgen_path = prowgen_file["filename"]
        raw = fetch_raw(prowgen_file["raw_url"], token)
        prowgen_data = yaml.safe_load(raw)

    source_by_dir: dict[str, dict[str, Any]] = {}
    for f in modified_configs:
        raw = fetch_raw(f["raw_url"], token)
        data = yaml.safe_load(raw)
        parent = str(Path(f["filename"]).parent)
        source_by_dir[parent] = data
        source_by_dir[f"path:{f['filename']}"] = data

    for f in added_configs:
        raw = fetch_raw(f["raw_url"], token)
        target_data = yaml.safe_load(raw)
        target_path = f["filename"]

        parent = str(Path(target_path).parent)
        source_data = source_by_dir.get(parent)
        source_path = ""
        if source_data:
            for mf in modified_configs:
                if str(Path(mf["filename"]).parent) == parent:
                    source_path = mf["filename"]
                    break

        ctx = CheckContext(
            target=target_data,
            target_path=target_path,
            source=source_data,
            source_path=source_path,
            prowgen=prowgen_data,
            prowgen_path=prowgen_path,
        )
        all_findings.extend(run_checks(ctx))

    for f in modified_configs:
        raw = fetch_raw(f["raw_url"], token)
        data = yaml.safe_load(raw)
        ctx = CheckContext(
            target=data,
            target_path=f["filename"],
            prowgen=prowgen_data,
            prowgen_path=prowgen_path,
        )
        target_only_checks = [
            check_test_name_length,
            check_fips_jira_project,
            check_fips_labels,
            check_fips_config_file_path,
            check_fips_workflow,
            check_fips_dr_var_completeness,
            check_fips_labels_cr_leak,
            check_fips_fail_with_test_failures,
            check_cr_required_fields,
            check_url_format_consistency,
            check_fips_cron_disabled,
            check_zz_generated_metadata,
        ]
        for check_fn in target_only_checks:
            check_fn(ctx)
        all_findings.extend(ctx.findings)

    return all_findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lint OCP expansion CI config YAML files.")
    parser.add_argument("--target", help="Target (new version) config YAML")
    parser.add_argument("--source", help="Source (old version) config YAML")
    parser.add_argument("--prowgen", help=".config.prowgen YAML")
    parser.add_argument("--pr", help="GitHub PR URL to fetch files from")
    parser.add_argument("--token", help="GitHub token (or set GITHUB_TOKEN)")
    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")

    if args.pr:
        findings = run_from_pr(args.pr, token)
    elif args.target:
        target_path = args.target
        with open(target_path) as f:
            target_data = yaml.safe_load(f)

        source_data = None
        source_path = ""
        if args.source:
            source_path = args.source
            with open(source_path) as f:
                source_data = yaml.safe_load(f)

        prowgen_data = None
        prowgen_path = ""
        if args.prowgen:
            prowgen_path = args.prowgen
            with open(prowgen_path) as f:
                prowgen_data = yaml.safe_load(f)

        ctx = CheckContext(
            target=target_data,
            target_path=target_path,
            source=source_data,
            source_path=source_path,
            prowgen=prowgen_data,
            prowgen_path=prowgen_path,
        )
        findings = run_checks(ctx)
    else:
        parser.error("Provide --target or --pr")
        return

    print(format_findings(findings))

    has_errors = any(f.severity == Severity.ERROR for f in findings)
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
