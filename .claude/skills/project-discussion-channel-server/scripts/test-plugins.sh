#!/bin/bash
set -euo pipefail

# Run unit tests for 6 official plugins (mode / resolve / sla / audit / activation / csat).
# Baseline: 50 passed (2026-04-22, V6 finalize)

PROJECT="/home/yaosh/projects/zchat/zchat-channel-server"
DRY_RUN=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [--dry-run] [--help]

Run plugin unit tests:
  tests/unit/test_mode_plugin.py
  tests/unit/test_resolve_plugin.py
  tests/unit/test_sla_plugin.py
  tests/unit/test_audit_plugin.py
  tests/unit/test_activation_plugin.py
  tests/unit/test_csat_plugin.py

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

CMD="cd $PROJECT && uv run pytest tests/unit/test_mode_plugin.py tests/unit/test_resolve_plugin.py tests/unit/test_sla_plugin.py tests/unit/test_audit_plugin.py tests/unit/test_activation_plugin.py tests/unit/test_csat_plugin.py -v"

if $DRY_RUN; then
    echo "[dry-run] $CMD"
    exit 0
fi

cd "$PROJECT" && uv run pytest tests/unit/test_mode_plugin.py tests/unit/test_resolve_plugin.py tests/unit/test_sla_plugin.py tests/unit/test_audit_plugin.py tests/unit/test_activation_plugin.py tests/unit/test_csat_plugin.py -v
