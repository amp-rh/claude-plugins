#!/usr/bin/env bash
set -euo pipefail

# Read stdin (Stop event JSON) — consume it even if unused
INPUT=$(cat)

# Session-scoped guard file using parent PID (approximates Claude Code session)
GUARD="/tmp/.agent-reflection-done-$$-${PPID}"

if [ -f "$GUARD" ]; then
  # Second stop attempt — reflection already ran, allow stop
  echo '{}'
  exit 0
fi

# First stop — create guard and trigger reflection
touch "$GUARD"

# Clean up guard when this shell exits
trap "rm -f '$GUARD'" EXIT

MSG="STOP: Before ending this session, you MUST invoke the /agent-reflection:reflect skill to review this session. After the reflection workflow completes, you may stop."

# Output systemMessage to redirect Claude to reflect
printf '{"systemMessage": "%s"}\n' "$MSG"
exit 0
