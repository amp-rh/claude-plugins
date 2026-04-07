#!/usr/bin/env python3
"""Lint OCP CI step registry shell scripts for deterministic rule violations.

Usage:
    check_step_scripts.py --target FILE
    check_step_scripts.py --dir DIRECTORY
    check_step_scripts.py --pr PR_URL [--token TOKEN]

Checks are derived from mpitt-pr-review SKILL.md step script rules and
review patterns from prior PRs (#67409, #74892).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

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
    line: int = 0


def _find_heredoc_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """Return (content_start, closing_marker) line ranges (1-based, inclusive)."""
    ranges: list[tuple[int, int]] = []
    in_heredoc = False
    marker = ""
    content_start = 0

    for lineno, line in enumerate(lines, 1):
        if in_heredoc:
            if line.strip() == marker:
                ranges.append((content_start, lineno))
                in_heredoc = False
        else:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            match = re.search(r"<<-?\s*['\"]?([A-Za-z_]\w*)['\"]?", stripped)
            if match:
                marker = match.group(1)
                in_heredoc = True
                content_start = lineno + 1

    return ranges


@dataclass
class CheckContext:
    file_path: str
    lines: list[str]
    findings: list[Finding] = field(default_factory=list)
    _heredoc_ranges: list[tuple[int, int]] | None = field(
        default=None, repr=False
    )

    @property
    def heredoc_ranges(self) -> list[tuple[int, int]]:
        if self._heredoc_ranges is None:
            self._heredoc_ranges = _find_heredoc_ranges(self.lines)
        return self._heredoc_ranges

    def in_heredoc(self, lineno: int) -> bool:
        return any(s <= lineno <= e for s, e in self.heredoc_ranges)

    def add(
        self, severity: Severity, check: str, message: str, line: int = 0,
    ) -> None:
        self.findings.append(Finding(
            severity=severity, check=check, message=message,
            file=self.file_path, line=line,
        ))


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_namespace_wait_jsonpath(ctx: CheckContext) -> None:
    for lineno, line in enumerate(ctx.lines, 1):
        if ctx.in_heredoc(lineno):
            continue
        if "--for=jsonpath" not in line:
            continue
        if not re.search(r"\bnamespace/", line) and not re.search(r"\bns/", line):
            continue
        if "Active" in line or ".status.phase" in line:
            ctx.add(
                Severity.ERROR, "namespace-wait-jsonpath",
                "Uses jsonpath for namespace Active wait; "
                "use --for=create instead",
                line=lineno,
            )


def check_wc_l_counting(ctx: CheckContext) -> None:
    for lineno, line in enumerate(ctx.lines, 1):
        if ctx.in_heredoc(lineno):
            continue
        if "wc -l" not in line:
            continue
        start = max(0, lineno - 4)
        end = min(len(ctx.lines), lineno + 1)
        if any("oc " in n for n in ctx.lines[start:end]):
            ctx.add(
                Severity.WARNING, "wc-l-counting",
                "Uses wc -l for resource counting; "
                "use -o json | jq '.items | length' instead",
                line=lineno,
            )


def check_heredocs(ctx: CheckContext) -> None:
    in_heredoc = False
    marker = ""
    start_line = 0
    has_interpolation = False
    has_escaped_dollar = False
    is_oc_context = False
    is_quoted = False

    for lineno, line in enumerate(ctx.lines, 1):
        if in_heredoc:
            if line.strip() == marker:
                if not is_quoted:
                    if is_oc_context and has_interpolation:
                        ctx.add(
                            Severity.WARNING, "heredoc-yaml-interpolation",
                            "Heredoc with shell interpolation piped to "
                            "oc apply/create; use jq -cn --arg for data "
                            "marshaling instead",
                            line=start_line,
                        )
                    if not has_interpolation and has_escaped_dollar:
                        ctx.add(
                            Severity.INFO, "non-literal-heredoc",
                            "Unquoted heredoc with escaped dollars but no "
                            "interpolation; use <<'EOF' (literal) instead",
                            line=start_line,
                        )
                in_heredoc = False
            else:
                if not is_quoted:
                    if re.search(r"(?<!\\)\$[{(]", line):
                        has_interpolation = True
                    if "\\$" in line:
                        has_escaped_dollar = True
        else:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            quoted_match = re.search(
                r"<<-?\s*['\"]([A-Za-z_]\w*)['\"]", stripped
            )
            unquoted_match = re.search(
                r"<<-?\s*([A-Za-z_]\w*)", stripped
            )
            if quoted_match:
                marker = quoted_match.group(1)
                in_heredoc = True
                start_line = lineno
                has_interpolation = False
                has_escaped_dollar = False
                is_oc_context = False
                is_quoted = True
            elif unquoted_match:
                marker = unquoted_match.group(1)
                in_heredoc = True
                start_line = lineno
                has_interpolation = False
                has_escaped_dollar = False
                is_oc_context = bool(
                    re.search(r"oc\s+(apply|create)", line)
                )
                is_quoted = False


def check_jsonpath_array_index(ctx: CheckContext) -> None:
    for lineno, line in enumerate(ctx.lines, 1):
        if ctx.in_heredoc(lineno):
            continue
        if "-o jsonpath" not in line and "-o=jsonpath" not in line:
            continue
        if re.search(r"items\[\d+\]", line):
            ctx.add(
                Severity.WARNING, "jsonpath-array-index",
                "Unsafe jsonpath array indexing (items[N]); "
                "use jq -r 'first(.items[]) // empty' instead",
                line=lineno,
            )


def check_post_increment_errexit(ctx: CheckContext) -> None:
    for lineno, line in enumerate(ctx.lines, 1):
        if ctx.in_heredoc(lineno):
            continue
        if re.search(r"(?<!\$)\(\(\s*\w+\s*\+\+\s*\)\)", line):
            ctx.add(
                Severity.WARNING, "post-increment-errexit",
                "Post-increment ((var++)) returns 0 when var=0, "
                "triggering errexit; use ((++var)) instead",
                line=lineno,
            )


def check_polling_loop_oc_wait(ctx: CheckContext) -> None:
    in_loop = False
    loop_start = 0
    has_oc_wait = False
    depth = 0

    for lineno, line in enumerate(ctx.lines, 1):
        if ctx.in_heredoc(lineno):
            continue
        stripped = line.strip()

        if not in_loop and re.match(r"(while|until)\b", stripped):
            in_loop = True
            loop_start = lineno
            has_oc_wait = False
            depth = 0

        if in_loop:
            depth += len(re.findall(r"\bdo\b", stripped))
            if "oc wait" in stripped:
                has_oc_wait = True
            depth -= len(re.findall(r"\bdone\b", stripped))
            if depth <= 0:
                if has_oc_wait:
                    ctx.add(
                        Severity.WARNING, "polling-loop-oc-wait",
                        "Polling loop wrapping oc wait; use "
                        "oc wait --for=create --timeout=Ns directly",
                        line=loop_start,
                    )
                in_loop = False


def _is_boilerplate(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("#"):
        return True
    if re.match(r"^set\s+-", stripped):
        return True
    if re.match(r"^shopt\s+-s", stripped):
        return True
    if stripped == "true":
        return True
    return False


def check_single_command_step(ctx: CheckContext) -> None:
    substantive = 0
    for lineno, line in enumerate(ctx.lines, 1):
        if ctx.in_heredoc(lineno):
            continue
        if not _is_boilerplate(line):
            substantive += 1

    if 1 <= substantive <= 3:
        ctx.add(
            Severity.INFO, "single-command-step",
            f"Step has only {substantive} substantive line(s); "
            f"consider merging to reduce container lifecycle overhead",
            line=1,
        )


_FUNC_DECL_RE = re.compile(
    r"(?:function\s+([\w-]+)\s*(?:\(\))?\s*\{|([\w][\w-]*)\s*\(\)\s*\{)"
)
_FUNC_START_RE = re.compile(
    r"(?:function\s+[\w-]+|[\w][\w-]*\s*\(\))"
)


def check_redundant_set_eux_in_function(ctx: CheckContext) -> None:
    in_function = False
    brace_depth = 0
    func_name = ""

    for lineno, line in enumerate(ctx.lines, 1):
        if ctx.in_heredoc(lineno):
            continue
        stripped = line.strip()

        if not in_function:
            m = _FUNC_DECL_RE.match(stripped)
            if m:
                func_name = m.group(1) or m.group(2) or ""
                in_function = True
                brace_depth = 0

        if in_function:
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                in_function = False
                continue
            if _FUNC_START_RE.match(stripped):
                continue
            if re.search(r"\bset\s+-[euxo]", stripped):
                ctx.add(
                    Severity.WARNING, "redundant-set-eux-in-function",
                    f"set options inside function '{func_name}' are "
                    f"inherited from script level; remove from function",
                    line=lineno,
                )


ALL_CHECKS = [
    check_namespace_wait_jsonpath,
    check_wc_l_counting,
    check_heredocs,
    check_jsonpath_array_index,
    check_post_increment_errexit,
    check_polling_loop_oc_wait,
    check_single_command_step,
    check_redundant_set_eux_in_function,
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_checks(ctx: CheckContext) -> list[Finding]:
    for fn in ALL_CHECKS:
        fn(ctx)
    return ctx.findings


def format_findings(findings: list[Finding]) -> str:
    if not findings:
        return "All checks passed."
    findings.sort(key=lambda f: (f.severity, f.check, f.file, f.line))
    out: list[str] = []
    for i, f in enumerate(findings, 1):
        loc = f.file
        if f.line:
            loc += f":{f.line}"
        out.append(f"{i}. [{f.severity.label()}] {f.check}: {f.message}")
        if loc:
            out.append(f"   File: {loc}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# GitHub PR fetching
# ---------------------------------------------------------------------------

STEP_REGISTRY_DIR = "ci-operator/step-registry/"


def is_step_script(path: str) -> bool:
    return path.startswith(STEP_REGISTRY_DIR) and path.endswith("-commands.sh")


def fetch_pr_files(
    pr_url: str, token: str | None = None,
) -> list[dict[str, Any]]:
    if requests is None:
        print(
            "ERROR: 'requests' package required for --pr mode. "
            "Install with: pip install requests",
            file=sys.stderr,
        )
        sys.exit(1)

    m = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url,
    )
    if not m:
        print(f"ERROR: Cannot parse PR URL: {pr_url}", file=sys.stderr)
        sys.exit(1)

    owner, repo, number = m.group(1), m.group(2), m.group(3)
    api_url = (
        f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}/files"
    )
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    all_files: list[dict[str, Any]] = []
    page = 1
    while True:
        resp = requests.get(
            api_url, headers=headers,
            params={"per_page": 100, "page": page}, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        all_files.extend(data)
        if len(data) < 100:
            break
        page += 1

    return all_files


def fetch_raw(url: str, token: str | None = None) -> str:
    assert requests is not None
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"token {token}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def run_from_pr(pr_url: str, token: str | None = None) -> list[Finding]:
    files = fetch_pr_files(pr_url, token)
    all_findings: list[Finding] = []

    for f in files:
        path = f["filename"]
        if not is_step_script(path):
            continue
        if f["status"] == "removed":
            continue
        raw = fetch_raw(f["raw_url"], token)
        ctx = CheckContext(file_path=path, lines=raw.splitlines())
        all_findings.extend(run_checks(ctx))

    return all_findings


# ---------------------------------------------------------------------------
# File / directory scanning
# ---------------------------------------------------------------------------

def run_from_file(file_path: str) -> list[Finding]:
    with open(file_path) as fh:
        content = fh.read()
    ctx = CheckContext(file_path=file_path, lines=content.splitlines())
    return run_checks(ctx)


def run_from_dir(dir_path: str) -> list[Finding]:
    all_findings: list[Finding] = []
    for path in sorted(Path(dir_path).rglob("*-commands.sh")):
        all_findings.extend(run_from_file(str(path)))
    return all_findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lint OCP CI step registry shell scripts.",
    )
    parser.add_argument("--target", help="Single shell script to lint")
    parser.add_argument(
        "--dir", help="Directory to scan for *-commands.sh files",
    )
    parser.add_argument("--pr", help="GitHub PR URL to fetch files from")
    parser.add_argument(
        "--token", help="GitHub token (or set GITHUB_TOKEN env var)",
    )
    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")

    if args.pr:
        findings = run_from_pr(args.pr, token)
    elif args.target:
        findings = run_from_file(args.target)
    elif args.dir:
        findings = run_from_dir(args.dir)
    else:
        parser.error("Provide --target, --dir, or --pr")
        return

    print(format_findings(findings))
    sys.exit(1 if any(f.severity == Severity.ERROR for f in findings) else 0)


if __name__ == "__main__":
    main()
