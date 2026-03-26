#!/bin/bash
# wc-agent — CLI wrapper
# Runs the wc-agent Typer CLI with proper uv project context
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec uv run --project "$SCRIPT_DIR/wc-agent" python -m wc_agent.cli "$@"
