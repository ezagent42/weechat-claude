#!/bin/bash
# start.sh — Start zchat system
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="${1:-$(pwd)}"
PROJECT="${2:-local}"
SESSION="zchat-${PROJECT}"

echo "╔══════════════════════════════════════╗"
echo "║           zchat Launcher             ║"
echo "╚══════════════════════════════════════╝"
echo "  Workspace: $WORKSPACE"
echo "  Project:   $PROJECT"

# --- Dependency check ---
MISSING=""
for cmd in claude uv weechat tmux; do
  command -v "$cmd" &>/dev/null || MISSING="$MISSING $cmd"
done
if [ -n "$MISSING" ]; then
  echo "Missing:$MISSING"; exit 1
fi

# Ensure deps
echo "  Syncing deps..."
(cd "$SCRIPT_DIR" && uv sync --quiet 2>/dev/null || true)
(cd "$SCRIPT_DIR/weechat-channel-server" && uv sync --quiet 2>/dev/null || true)

ZCHAT="ZCHAT_TMUX_SESSION=$SESSION uv run --project $SCRIPT_DIR python -m zchat.cli --project $PROJECT"

# Create project if it doesn't exist
if ! eval $ZCHAT project show &>/dev/null; then
  echo "  Creating project '$PROJECT'..."
  eval $ZCHAT project create "$PROJECT"
fi

# Start IRC + WeeChat + agent0
eval $ZCHAT irc daemon start
eval $ZCHAT irc start
eval $ZCHAT agent create agent0 --workspace "$WORKSPACE"

echo "  Launching tmux session '$SESSION'..."
tmux -CC attach -t "$SESSION" 2>/dev/null || tmux attach -t "$SESSION"
