# WeeChat-Claude

Multi-agent collaboration system: WeeChat ↔ Zenoh P2P ↔ Claude Code (MCP).

## Architecture

Three composable components connected via Zenoh topic contracts:
- `weechat-zenoh/weechat-zenoh.py` — WeeChat plugin for P2P rooms & DMs over Zenoh
- `weechat-channel-server/` — FastMCP server bridging Claude Code ↔ Zenoh (server.py, tools.py, message.py)
- `weechat-agent/weechat-agent.py` — Agent lifecycle manager (spawn/stop Claude in tmux panes)

## Zenoh Topics

- `wc/rooms/{room_id}/messages` — room pub/sub
- `wc/rooms/{room_id}/presence/{nick}` — room presence (liveliness)
- `wc/dm/{sorted_pair}/messages` — DM pub/sub (alphabetically sorted pair, e.g. `alice_bob`)
- `wc/presence/{nick}` — global online status

Messages are JSON: `{id, nick, type, body, ts}`

## Development

### Commands

```bash
./start.sh ~/workspace username    # Full system startup (tmux + username:agent0 + weechat)
./stop.sh                          # Kill tmux session
pytest tests/unit/                 # Unit tests (mocked Zenoh, fast)
pytest -m integration tests/       # Integration tests (real Zenoh peers)
```

### Dependencies

- `eclipse-zenoh` ≥1.0.0 — P2P messaging
- `mcp[cli]` ≥1.2.0 — FastMCP server framework
- `uv` — Python dependency management (used by MCP runner)
- `tmux` — Session/pane management for agents

### Testing

- `tests/conftest.py` — MockZenohSession fixtures for unit tests
- Unit tests: mock Zenoh, test message utilities, tools, protocol
- Integration tests: real Zenoh peer sessions, marked with `@pytest.mark.integration`

### Adding MCP Tools

1. Add async function in `weechat-channel-server/tools.py` with `@mcp.tool()`
2. Pass mcp instance from `server.py`
3. Add tests in `tests/unit/test_tools.py`

### Key Constraints

- Channel MCP requires `--dangerously-load-development-channels` flag
- `{username}:agent0` is the primary agent — created by start.sh, cannot be stopped via `/agent stop`
- Agent names are scoped to creator: `alice:agent0`, `alice:helper` (separator: `:`)
- WeeChat callbacks must not block — use deques + timers for async work
- Zenoh Python + WeeChat .so may conflict — sidecar process is planned
