# agent-reflection

Automated session reflection plugin for Claude Code. Reviews all agent, skill, and command usage at the end of every session, scores performance across 8 quality axes, and implements improvements.

## How It Works

1. **Stop Hook** fires when Claude wants to end the conversation
2. **Reflect Skill** orchestrates a comprehensive session review
3. **Session Reflector Agent** scores every item on 8 axes and identifies improvements
4. **Improvement Implementer Agent** applies edits to user-owned files or files GitHub issues for read-only marketplace plugins

## Scoring Axes

| Axis | What It Measures |
|------|-----------------|
| Accuracy | Correct results, errors, retries |
| Efficiency | Token/tool economy |
| Approach | Strategy quality |
| Tool Selection | Right tools used |
| Prompt Clarity | Prompt completeness and scope |
| Error Handling | Edge cases and failure handling |
| Missed Opportunities | Unexploited possibilities |
| Output Format | Format fitness for consumer |

## Improvement Channels

| File Location | Action |
|---|---|
| `~/.claude/skills/*`, `~/.claude/agents/*`, `~/.claude/commands/*` | Direct edit |
| `~/.claude/plugins/cache/*` (marketplace) | GitHub issue on `amp-rh/claude-code` |
| This plugin's own files | GitHub issue on `amp-rh/claude-code` |
| Behavioral (no file) | Memory or report |

## Manual Usage

Invoke mid-session: `/agent-reflection:reflect`

## Loop Prevention

The Stop hook uses a session-scoped guard file to prevent infinite reflection loops. First stop triggers reflection; second stop proceeds normally.
