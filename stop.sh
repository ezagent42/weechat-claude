#!/bin/bash
# stop.sh — Stop zchat system
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="${1:-local}"
SESSION="zchat-${PROJECT}"

ZCHAT="ZCHAT_ZELLIJ_SESSION=$SESSION uv run --project $SCRIPT_DIR python -m zchat.cli --project $PROJECT"

echo "Stopping session: $SESSION"
eval $ZCHAT shutdown 2>/dev/null || true
zellij kill-session "$SESSION" 2>/dev/null && echo "  Zellij session stopped" || echo "  (not running)"
