#!/bin/bash
set -euo pipefail

# Test runner for cs_server module
# Runs: tests/unit/test_legacy.py (sys message roundtrip, instructions interpolation)
# Baseline: 5/5 passed (2026-04-14)

show_help() {
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Run cs_server module tests (test_legacy.py)"
  echo ""
  echo "Options:"
  echo "  --help      Show this help"
  echo "  --dry-run   Show command without executing"
}

DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --help) show_help; exit 0 ;;
    --dry-run) DRY_RUN=true ;;
  esac
done

PROJECT_ROOT="$(cd "$(dirname "$0")/../../../../zchat-channel-server" && pwd)"
CMD="uv run pytest tests/unit/test_legacy.py -v"

if [ "$DRY_RUN" = true ]; then
  echo "[dry-run] cd $PROJECT_ROOT && $CMD"
  exit 0
fi

cd "$PROJECT_ROOT"
exec $CMD
