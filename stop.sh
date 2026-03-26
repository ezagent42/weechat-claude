#!/bin/bash
# stop.sh — Stop WeeChat-Claude system
# Usage: ./stop.sh [--all]
#   --all: also stop ergo IRC server

SESSION="weechat-claude"
STOP_ERGO=false
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/weechat-claude.toml"

for arg in "$@"; do
  if [ "$arg" = "--all" ]; then
    STOP_ERGO=true
  fi
done

echo "Stopping session: $SESSION"
python3 "$SCRIPT_DIR/wc-agent/cli.py" --config "$CONFIG" shutdown 2>/dev/null || true
tmux kill-session -t "$SESSION" 2>/dev/null && echo "  tmux session stopped" || echo "  (not running)"

if [ "$STOP_ERGO" = true ]; then
  pkill -x ergo 2>/dev/null && echo "  ergo stopped" || echo "  ergo (not running)"
fi
