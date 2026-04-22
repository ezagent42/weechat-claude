#!/bin/bash
set -euo pipefail

# Run unit tests for the feishu_bridge module (飞书 ↔ channel-server 桥接层).
# Covers: outbound_router / group_manager / routing_reader / sender / parsers / card_action / client_extended / visibility_router.
# Baseline: 67 passed (2026-04-22, V6 finalize)

PROJECT="/home/yaosh/projects/zchat/zchat-channel-server"
DRY_RUN=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [--dry-run] [--help]

Run feishu_bridge unit tests:
  tests/unit/test_outbound_router.py
  tests/unit/test_group_manager.py
  tests/unit/test_routing_reader.py
  tests/unit/test_sender.py
  tests/unit/test_parsers.py
  tests/unit/test_card_action.py
  tests/unit/test_client_extended.py
  tests/unit/test_visibility_router.py

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

CMD="cd $PROJECT && uv run pytest tests/unit/test_outbound_router.py tests/unit/test_group_manager.py tests/unit/test_routing_reader.py tests/unit/test_sender.py tests/unit/test_parsers.py tests/unit/test_card_action.py tests/unit/test_client_extended.py tests/unit/test_visibility_router.py -v"

if $DRY_RUN; then
    echo "[dry-run] $CMD"
    exit 0
fi

cd "$PROJECT" && uv run pytest tests/unit/test_outbound_router.py tests/unit/test_group_manager.py tests/unit/test_routing_reader.py tests/unit/test_sender.py tests/unit/test_parsers.py tests/unit/test_card_action.py tests/unit/test_client_extended.py tests/unit/test_visibility_router.py -v
