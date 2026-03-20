# amp-rh Claude Code Plugins

Public plugin marketplace for Claude Code extensions by [amp-rh](https://github.com/amp-rh).

## Plugins

None yet. Plugins will be added here as they are ready for public release.

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
