#!/bin/bash
# stop.sh — 停止所有 WeeChat-Claude 进程
SESSION="${1:-weechat-claude}"
echo "Stopping session: $SESSION"
tmux kill-session -t "$SESSION" 2>/dev/null && echo "Done" || echo "  (not running)"
