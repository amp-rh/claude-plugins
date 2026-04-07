# amp-rh Claude Code Plugins

Public plugin marketplace for Claude Code extensions by [amp-rh](https://github.com/amp-rh).

## Plugins

### agent-reflection
Automated session reflection that reviews agent, skill, and command usage at session end, scores performance across 8 quality axes, and implements improvements directly or via GitHub issues.

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
