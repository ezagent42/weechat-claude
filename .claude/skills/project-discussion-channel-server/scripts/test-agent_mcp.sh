#!/bin/bash
set -euo pipefail

# Run unit tests for the agent_mcp module (MCP stdio agent process).
# Covers: chunk_message, encode_*, run_zchat_cli, join_channel, sys message injection.
# Baseline: 15 passed (2026-04-22, V6 finalize)

PROJECT="/home/yaosh/projects/zchat/zchat-channel-server"
DRY_RUN=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [--dry-run] [--help]

Run agent_mcp module unit tests (tests/unit/test_agent_mcp.py).

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

CMD="cd $PROJECT && uv run pytest tests/unit/test_agent_mcp.py -v"

if $DRY_RUN; then
    echo "[dry-run] $CMD"
    exit 0
fi

cd "$PROJECT" && uv run pytest tests/unit/test_agent_mcp.py -v
