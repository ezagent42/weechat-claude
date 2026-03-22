#!/bin/bash
# stop.sh — Stop WeeChat-Claude session (optionally stop zenohd)
# Usage: ./stop.sh [session-name] [--all]
#   --all: also stop zenohd

SESSION="weechat-claude"
STOP_ZENOHD=false

for arg in "$@"; do
  if [ "$arg" = "--all" ]; then
    STOP_ZENOHD=true
  else
    SESSION="$arg"
  fi
done

echo "Stopping session: $SESSION"
tmux kill-session -t "$SESSION" 2>/dev/null && echo "  tmux session stopped" || echo "  (not running)"

if [ "$STOP_ZENOHD" = true ]; then
  pkill -x zenohd 2>/dev/null && echo "  zenohd stopped" || echo "  zenohd (not running)"
fi
