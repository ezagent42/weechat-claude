#!/bin/bash
# stop.sh — Stop zchat system
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="${1:-local}"
SESSION="zchat-${PROJECT}"

ZCHAT="ZCHAT_TMUX_SESSION=$SESSION uv run --project $SCRIPT_DIR python -m zchat.cli --project $PROJECT"

echo "Stopping session: $SESSION"
eval $ZCHAT shutdown 2>/dev/null || true
tmux kill-session -t "$SESSION" 2>/dev/null && echo "  tmux session stopped" || echo "  (not running)"
