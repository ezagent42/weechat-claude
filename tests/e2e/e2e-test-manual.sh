#!/bin/bash
# e2e-test-manual.sh — Set up isolated test environment for manual testing
#
# Usage (inside tmux):
#   source tests/e2e/e2e-test-manual.sh
#
# What it does:
#   1. Sets WC_AGENT_HOME to temp dir (via tmux set-environment — all panes inherit)
#   2. Creates test project with unique ergo port
#   3. Starts ergo
#   4. Prints step-by-step guide
#
# New panes automatically inherit WC_AGENT_HOME. Use ./wc-agent.sh for commands.
# After testing: e2e-cleanup (or just close the tmux session)

# ============================================================
# Detect environment
# ============================================================

if [ -z "$TMUX" ]; then
    echo "ERROR: Must be run inside a tmux session."
    echo ""
    echo "Start one first:"
    echo "  tmux -CC new -s test     # iTerm2"
    echo "  tmux new -s test         # standard terminal"
    echo ""
    echo "Then: source tests/e2e/e2e-test-manual.sh"
    return 1 2>/dev/null || exit 1
fi

# Find project dir (relative to this script)
_E2E_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$_E2E_SCRIPT_DIR/../.." && pwd)"

# ============================================================
# Create isolated environment
# ============================================================

E2E_ID="${E2E_ID:-$$}"
E2E_IRC_PORT=$((16667 + (E2E_ID % 1000)))
E2E_ERGO_DIR="/tmp/e2e-ergo-${E2E_ID}"
export WC_AGENT_HOME="/tmp/e2e-wc-agent-${E2E_ID}"

# Set tmux session-level env vars — ALL new panes inherit these
tmux set-environment WC_AGENT_HOME "$WC_AGENT_HOME"
tmux set-environment E2E_IRC_PORT "$E2E_IRC_PORT"
tmux set-environment E2E_ID "$E2E_ID"
tmux set-environment E2E_ERGO_DIR "$E2E_ERGO_DIR"

# Source proxy/env
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"
[ -f "$PROJECT_DIR/claude.local.env" ] && set -a && source "$PROJECT_DIR/claude.local.env" && set +a

# cd to project dir
cd "$PROJECT_DIR"

# ============================================================
# Cleanup function (available in this pane)
# ============================================================

e2e-cleanup() {
    echo "Cleaning up e2e environment (id: $E2E_ID)..."
    ./wc-agent.sh shutdown 2>/dev/null || true
    # Kill ergo by PID if we know it
    [ -n "$E2E_ERGO_PID" ] && kill "$E2E_ERGO_PID" 2>/dev/null
    # Kill any ergo on our port
    lsof -ti :${E2E_IRC_PORT} 2>/dev/null | xargs kill 2>/dev/null
    # Remove temp dirs
    rm -rf "/tmp/e2e-ergo-${E2E_ID}" "$WC_AGENT_HOME"
    # Unset tmux env vars
    tmux set-environment -u WC_AGENT_HOME 2>/dev/null
    tmux set-environment -u E2E_IRC_PORT 2>/dev/null
    tmux set-environment -u E2E_ID 2>/dev/null
    tmux set-environment -u E2E_ERGO_DIR 2>/dev/null
    echo "Done."
}

# ============================================================
# Auto-setup
# ============================================================

echo "╔══════════════════════════════════════╗"
echo "║  WeeChat-Claude Manual Test Setup    ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Project dir:    $PROJECT_DIR"
echo "  ID:             $E2E_ID"
echo "  IRC port:       $E2E_IRC_PORT"
echo "  WC_AGENT_HOME:  $WC_AGENT_HOME"
echo ""

# Sync deps
echo "Syncing dependencies..."
(cd "$PROJECT_DIR/wc-agent" && uv sync --quiet 2>/dev/null || true)
(cd "$PROJECT_DIR/weechat-channel-server" && uv sync --quiet 2>/dev/null || true)

# Create test project with unique port
echo "Creating test project 'e2e'..."
mkdir -p "$WC_AGENT_HOME/projects/e2e"
cat > "$WC_AGENT_HOME/projects/e2e/config.toml" << TOMLEOF
[irc]
server = "127.0.0.1"
port = ${E2E_IRC_PORT}
tls = false
password = ""

[agents]
default_channels = ["#general"]
username = "alice"
TOMLEOF
# Set as default project
mkdir -p "$WC_AGENT_HOME"
echo "e2e" > "$WC_AGENT_HOME/default"

# Start ergo on unique port
echo "Starting ergo on port $E2E_IRC_PORT..."
mkdir -p "$E2E_ERGO_DIR"
if [ -d "$HOME/.local/share/ergo/languages" ] && [ ! -d "$E2E_ERGO_DIR/languages" ]; then
    cp -r "$HOME/.local/share/ergo/languages" "$E2E_ERGO_DIR/"
fi
ergo defaultconfig > "$E2E_ERGO_DIR/ergo.yaml" 2>/dev/null
sed -i '' "s|\"127.0.0.1:6667\":|\"127.0.0.1:${E2E_IRC_PORT}\":|" "$E2E_ERGO_DIR/ergo.yaml"
sed -i '' '/\[::1\]:6667/d' "$E2E_ERGO_DIR/ergo.yaml"
sed -i '' '/"[^"]*:6697":/,/min-tls-version:/d' "$E2E_ERGO_DIR/ergo.yaml"

cd "$E2E_ERGO_DIR" && ergo run --conf "$E2E_ERGO_DIR/ergo.yaml" &>/dev/null &
E2E_ERGO_PID=$!
cd "$PROJECT_DIR"
sleep 2

if kill -0 "$E2E_ERGO_PID" 2>/dev/null; then
    echo "  ergo running (pid $E2E_ERGO_PID, port $E2E_IRC_PORT)"
else
    echo "  ERROR: ergo failed to start!"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Ready! CWD: $PROJECT_DIR"
echo "  New tmux panes auto-inherit WC_AGENT_HOME."
echo "  Use ./wc-agent.sh for all commands."
echo ""
echo "━━━ Step 1: Start WeeChat ━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ./wc-agent.sh irc start"
echo ""
echo "━━━ Step 2: Check status ━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ./wc-agent.sh irc status"
echo ""
echo "━━━ Step 3: Create agent ━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ./wc-agent.sh agent create agent0"
echo ""
echo "  Then in WeeChat #general:"
echo "    @alice-agent0 what is the capital of France?"
echo ""
echo "━━━ Step 4: Agent commands ━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ./wc-agent.sh agent list"
echo "  ./wc-agent.sh agent status agent0"
echo "  ./wc-agent.sh agent send agent0 'Reply hello to #general'"
echo ""
echo "━━━ Step 5: Multi-agent ━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ./wc-agent.sh agent create helper"
echo "  ./wc-agent.sh agent stop helper"
echo ""
echo "━━━ Step 6: Cleanup ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ./wc-agent.sh shutdown"
echo "  e2e-cleanup"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
