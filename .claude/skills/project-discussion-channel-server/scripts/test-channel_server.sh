#!/bin/bash
set -euo pipefail

# Run unit tests for the channel_server module (Router / RoutingTable / watcher / PluginRegistry / IRCConnection / WSServer).
# Covers: router.py / routing.py / routing_watcher.py / plugin.py bindings.
# Baseline: 47 passed (2026-04-22, V6 finalize)

PROJECT="/home/yaosh/projects/zchat/zchat-channel-server"
DRY_RUN=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [--dry-run] [--help]

Run channel_server core unit tests:
  tests/unit/test_router.py
  tests/unit/test_routing.py
  tests/unit/test_routing_watcher.py
  tests/unit/test_plugin_registry.py

Options:
  --dry-run   Show the test command without executing
  --help      Show this help message
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --help) usage ;;
        *) echo "Error: unknown option '$1'. Use --help for usage." >&2; exit 1 ;;
    esac
done

CMD="cd $PROJECT && uv run pytest tests/unit/test_router.py tests/unit/test_routing.py tests/unit/test_routing_watcher.py tests/unit/test_plugin_registry.py -v"

if $DRY_RUN; then
    echo "[dry-run] $CMD"
    exit 0
fi

cd "$PROJECT" && uv run pytest tests/unit/test_router.py tests/unit/test_routing.py tests/unit/test_routing_watcher.py tests/unit/test_plugin_registry.py -v
