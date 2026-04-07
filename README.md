# amp-rh Claude Code Plugins

Public plugin marketplace for Claude Code extensions by [amp-rh](https://github.com/amp-rh).

## Plugins

### agent-reflection
Automated session reflection that reviews agent, skill, and command usage at session end, scores performance across 8 quality axes, and implements improvements directly or via GitHub issues.

### ci-monitoring
MCP-based CI monitoring infrastructure for OpenShift interop job health, agent-driven triage workflows, and watcher rotation automation. Bundles Sippy, Watcher, and Loki MCP servers with 5 skills, 2 agents, and 5 operational runbooks.

### interop-standards
Codified interop testing standards for OpenShift CI: expansion workflows, PR review enforcement, rule auditing, and rehearsal best practices. Includes 5 skills, 3 agents, deterministic Python linters, and domain reference docs.

## Usage

Add this marketplace to your Claude Code settings:

```json
{
  "extraKnownMarketplaces": {
    "amp-rh-plugins": {
      "source": {
        "source": "github",
        "repo": "amp-rh/claude-plugins"
      },
      "autoUpdate": true
    }
  }
}
```

Then enable individual plugins:

```json
{
  "enabledPlugins": {
    "plugin-name@amp-rh-plugins": true
  }
}
```
