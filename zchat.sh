#!/bin/bash
# zchat — CLI wrapper
# Runs the zchat Typer CLI with proper uv project context
# Respects ZCHAT_HOME env var if set (e.g., for testing)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec env ${ZCHAT_HOME:+ZCHAT_HOME="$ZCHAT_HOME"} \
    uv run --project "$SCRIPT_DIR" python -m zchat.cli "$@"
