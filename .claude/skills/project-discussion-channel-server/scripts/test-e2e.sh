#!/bin/bash
set -euo pipefail

# Run end-to-end tests (tests/e2e/).
# Covers: bridge lazy_create / CSAT lifecycle / help_request lifecycle / plugin pipeline full lifecycle.
# Baseline: 12 passed (2026-04-22, V6 finalize)
#
# Note: pytest.ini 不 strict markers，默认不过滤 -m e2e；测试本身以 @pytest.mark.e2e 标记但都能在 CI 本地跑通（Mock 外部依赖）。

PROJECT="/home/yaosh/projects/zchat/zchat-channel-server"
DRY_RUN=false

usage() {
    cat <<EOF
Usage: $(basename "$0") [--dry-run] [--help]

Run channel-server end-to-end tests (tests/e2e/).

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

CMD="cd $PROJECT && uv run pytest tests/e2e/ -v"

if $DRY_RUN; then
    echo "[dry-run] $CMD"
    exit 0
fi

cd "$PROJECT" && uv run pytest tests/e2e/ -v
