"""Configuration loading for watcher-mcp."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class WatcherConfig:
    """Watcher MCP configuration."""

    # Jira settings
    jira_url: str = "https://issues.redhat.com"
    jira_project: str = "LPINTEROP"
    jira_labels: list[str] = field(default_factory=lambda: ["4.19-lp", "4.20-lp", "opp-aws-lp", "rosa-hcp-lp"])

    # Sippy settings
    sippy_url: str = "https://sippy.dptools.openshift.org"
    releases: list[str] = field(default_factory=lambda: ["4.19", "4.20"])

    # Job pattern matching
    interop_patterns: list[str] = field(default_factory=lambda: ["*interop*", "*opp*", "*lp-*"])
    hcp_patterns: list[str] = field(default_factory=lambda: ["*hypershift*", "*rosa-hcp*"])


def load_config(config_path: str | None = None) -> WatcherConfig:
    """Load configuration from file or environment.

    Priority:
    1. Explicit config_path argument
    2. WATCHER_CONFIG_PATH environment variable
    3. /app/config/default.yaml (container default)
    4. ./config/default.yaml (local development)
    5. Built-in defaults
    """
    # Determine config file path
    if config_path is None:
        config_path = os.environ.get("WATCHER_CONFIG_PATH")

    if config_path is None:
        # Try container path first, then local
        for path in ["/app/config/default.yaml", "./config/default.yaml"]:
            if Path(path).exists():
                config_path = path
                break

    # Load from file if available
    config_data: dict = {}
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}

    # Build config with environment overrides
    jira_config = config_data.get("jira", {})
    sippy_config = config_data.get("sippy", {})
    patterns_config = config_data.get("job_patterns", {})

    return WatcherConfig(
        jira_url=os.environ.get("JIRA_URL", jira_config.get("url", "https://issues.redhat.com")),
        jira_project=os.environ.get("JIRA_PROJECT", jira_config.get("project", "LPINTEROP")),
        jira_labels=jira_config.get("labels", ["4.19-lp", "4.20-lp", "opp-aws-lp", "rosa-hcp-lp"]),
        sippy_url=os.environ.get("SIPPY_URL", sippy_config.get("url", "https://sippy.dptools.openshift.org")),
        releases=sippy_config.get("releases", ["4.19", "4.20"]),
        interop_patterns=patterns_config.get("interop", ["*interop*", "*opp*", "*lp-*"]),
        hcp_patterns=patterns_config.get("hcp", ["*hypershift*", "*rosa-hcp*"]),
    )
