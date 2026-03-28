#!/bin/bash
# e2e-setup.sh — Set up isolated test environment for manual testing
#
# Usage:
#   1. Create a tmux session:
#        tmux -CC new -s test     (iTerm2)
#        tmux new -s test         (standard terminal)
#
#   2. Source this script:
#        source tests/e2e/e2e-setup.sh
#
#   3. Follow the steps:
#        ./zchat.sh irc daemon start              # Start ergo
#        ./zchat.sh irc start                     # Start WeeChat (new pane)
#        ./zchat.sh irc status                    # Verify IRC connected
#        ./zchat.sh agent create agent0            # Create agent (new pane)
#        ./zchat.sh agent list                     # Check agent status
#        ./zchat.sh agent send agent0 'hello'      # Send text to agent pane
#        ./zchat.sh agent stop agent0              # Stop agent
#        ./zchat.sh shutdown                       # Stop everything
#
#      In WeeChat #general, test @mention:
#        @alice-agent0 what is the capital of France?
#
#   4. In new panes, re-source to get env vars:
#        source tests/e2e/e2e-setup.sh
#      (Reuses same E2E_ID, skips setup)
#
#   5. Cleanup:
#        source tests/e2e/e2e-cleanup.sh

# Find project root
_find_project_root() {
    local dir="$PWD"
    while [ "$dir" != "/" ]; do
        [ -f "$dir/zchat.sh" ] && echo "$dir" && return
        dir="$(dirname "$dir")"
    done
    echo ""
}
PROJECT_DIR="$(_find_project_root)"
if [ -z "$PROJECT_DIR" ]; then
    echo "ERROR: Cannot find project root (no zchat.sh found)."
    echo "  cd to the project directory first."
    return 1 2>/dev/null || exit 1
fi

if [ -z "$TMUX" ]; then
    echo "ERROR: Must be inside a tmux session."
    echo ""
    echo "  tmux -CC new -s test   # iTerm2"
    echo "  tmux new -s test       # standard"
    return 1 2>/dev/null || exit 1
fi

# Reuse existing environment if already set up
if [ -n "$ZCHAT_HOME" ] && [ -d "$ZCHAT_HOME" ]; then
    echo "(Reusing e2e environment: id=$E2E_ID port=$E2E_IRC_PORT)"
    cd "$PROJECT_DIR"
    return 0 2>/dev/null || exit 0
fi

# Fresh environment
export E2E_ID="$$"
export E2E_IRC_PORT=$((16667 + (E2E_ID % 1000)))
export ZCHAT_HOME="/tmp/e2e-zchat-${E2E_ID}"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"

# Source proxy
[ -f "$PROJECT_DIR/claude.local.env" ] && set -a && source "$PROJECT_DIR/claude.local.env" && set +a

cd "$PROJECT_DIR"

echo "Setting up e2e environment (id: $E2E_ID, port: $E2E_IRC_PORT)..."

# Sync deps
(cd "$PROJECT_DIR" && uv sync --quiet 2>/dev/null || true)
(cd "$PROJECT_DIR/zchat-channel-server" && uv sync --quiet 2>/dev/null || true)

# Create project with unique port
mkdir -p "$ZCHAT_HOME/projects/e2e"
cat > "$ZCHAT_HOME/projects/e2e/config.toml" << EOF
[irc]
server = "127.0.0.1"
port = ${E2E_IRC_PORT}
tls = false
password = ""

[agents]
default_channels = ["#general"]
username = "alice"
EOF
echo "e2e" > "$ZCHAT_HOME/default"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Ready! Port: $E2E_IRC_PORT  ID: $E2E_ID"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  ./zchat.sh irc daemon start"
echo "  ./zchat.sh irc start"
echo "  ./zchat.sh agent create agent0"
echo "  ./zchat.sh agent send agent0 'say hello to #general'"
echo "  ./zchat.sh agent list"
echo "  ./zchat.sh shutdown"
echo ""
echo "  New panes: source tests/e2e/e2e-setup.sh"
echo "  Cleanup:   source tests/e2e/e2e-cleanup.sh"
echo ""
