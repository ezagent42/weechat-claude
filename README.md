# WeeChat-Claude

**[English](README.md)** | **[中文](README_zh.md)**

A local/LAN-based multi-agent collaboration system that bridges [WeeChat](https://weechat.org/) with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) through [Zenoh](https://zenoh.io/) P2P messaging.

Run multiple Claude Code instances as chat participants — talk to them, let them talk to each other, and manage their lifecycle from your terminal.

## Architecture

Three composable components connected via Zenoh topic contracts. Each can be used independently:

```
Scenario 1: Person ↔ Person (weechat-zenoh only)
┌─────────┐  Zenoh  ┌─────────┐
│ WeeChat │ ◄─────► │ WeeChat │
│ + zenoh │         │ + zenoh │
│ (Alice) │         │ (Bob)   │
└─────────┘         └─────────┘

Scenario 2: Person ↔ Agent (+ weechat-channel-server)
┌─────────┐  Zenoh  ┌───────────────────┐
│ WeeChat │ ◄─────► │ weechat-channel   │
│ + zenoh │         │ (MCP server)      │
│ (Alice) │         │    ↕ stdio        │
└─────────┘         │ Claude Code       │
                    └───────────────────┘

Scenario 3: Full deployment (all three components)
┌─────────────────────────────────┐
│ WeeChat                         │
│  weechat-zenoh.py   (P2P chat)  │
│  weechat-agent.py   (lifecycle) │
└────────┬────────────────┬───────┘
         │  Zenoh mesh    │ subprocess
    ┌────▼────┐      ┌───▼──────────┐
    │ WeeChat │      │ Claude Code  │
    │ (Bob)   │      │ + channel    │
    └─────────┘      │ (agent0)     │
                     └──────────────┘
```

| Component | Type | Purpose |
|-----------|------|---------|
| **weechat-zenoh** | WeeChat Python plugin | P2P channels & privates over Zenoh. Treats all participants equally — no Claude awareness. |
| **weechat-channel-server** | Claude Code plugin (MCP server) | Bridges Claude Code ↔ Zenoh. No WeeChat awareness — only knows Zenoh topics & MCP. |
| **weechat-agent** | WeeChat Python plugin | Agent lifecycle manager. Spawns/stops Claude instances in tmux panes. |

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) ≥ 2.1.80
- [uv](https://docs.astral.sh/uv/) ≥ 0.4
- [WeeChat](https://weechat.org/) ≥ 4.0
- [tmux](https://github.com/tmux/tmux)
- [zenohd](https://github.com/eclipse-zenoh/zenoh) — local Zenoh router (auto-started by start.sh)
- Python ≥ 3.10

## Quick Start

```bash
git clone https://github.com/ezagent42/weechat-claude.git
cd weechat-claude

# Launch the full system (agent0 + WeeChat in tmux)
# zenohd is automatically started if not already running
./start.sh ~/my-project alice
```

This will:
1. Install dependencies (eclipse-zenoh, MCP server deps)
2. Copy WeeChat plugins to your WeeChat config directory
3. Create a tmux session with two panes:
   - **Pane 0**: Claude Code (agent0) with the channel plugin
   - **Pane 1**: WeeChat with zenoh + agent plugins loaded

Once running, message the agent in WeeChat:

```
/zenoh join @agent0
hello agent0, what can you help me with?
```

## Usage

### WeeChat Commands

**Chat (weechat-zenoh)**

| Command | Description |
|---------|-------------|
| `/zenoh join #channel` | Join a channel |
| `/zenoh join @nick` | Open a private buffer |
| `/zenoh leave [target]` | Leave current or specified channel/private |
| `/zenoh nick <name>` | Change nickname |
| `/zenoh list` | List joined channels and privates |
| `/zenoh status` | Show Zenoh session status |

**Agent Management (weechat-agent)**

| Command | Description |
|---------|-------------|
| `/agent create <name> [--workspace <path>]` | Spawn a new Claude Code instance |
| `/agent stop <name>` | Stop an agent (cannot stop agent0) |
| `/agent restart <name>` | Restart an agent |
| `/agent list` | List all agents and their status |
| `/agent join <agent> #channel` | Tell an agent to join a channel |

### Using Components Independently

**Person-to-person chat** (weechat-zenoh only, channel buffers):

```bash
# Terminal A
weechat
/python load /path/to/weechat-zenoh.py
/zenoh nick alice
/zenoh join #team

# Terminal B (same LAN)
weechat
/python load /path/to/weechat-zenoh.py
/zenoh nick bob
/zenoh join #team
```

**Single agent without agent manager** (weechat-zenoh + weechat-channel-server, private buffer):

```bash
# Terminal A: Claude Code with channel plugin
cd weechat-channel-server
claude --dangerously-load-development-channels plugin:weechat-channel

# Terminal B: WeeChat
weechat
/python load /path/to/weechat-zenoh.py
/zenoh nick alice
/zenoh join @agent0
```

## Message Protocol

All messages are JSON over Zenoh pub/sub:

```json
{
  "id": "uuid-v4",
  "nick": "alice",
  "type": "msg",
  "body": "hello everyone",
  "ts": 1711036800.123
}
```

**Message types**: `msg`, `action` (/me), `join`, `leave`, `nick`

**Zenoh topic hierarchy**:

```
wc/
├── channels/{channel_id}/
│   ├── messages                # Channel messages (pub/sub)
│   └── presence/{nick}         # Channel member presence (liveliness)
├── private/{sorted_pair}/
│   └── messages                # Private messages (pair sorted alphabetically, e.g. alice_bob)
└── presence/{nick}             # Global online status (liveliness)
```

## Project Structure

```
weechat-claude/
├── start.sh                        # Full system launcher
├── stop.sh                         # Stop tmux session
├── weechat-zenoh/
│   └── weechat-zenoh.py            # P2P chat plugin
├── weechat-agent/
│   └── weechat-agent.py            # Agent lifecycle plugin
├── weechat-channel-server/
│   ├── server.py                   # MCP server + Zenoh bridge
│   ├── tools.py                    # MCP tools (reply)
│   ├── message.py                  # Message utilities (dedup, chunking, mentions)
│   ├── pyproject.toml              # Dependencies
│   └── .claude-plugin/plugin.json  # Claude Code plugin metadata
├── tests/
│   ├── conftest.py                 # Mock Zenoh fixtures
│   ├── unit/                       # Fast, mocked tests
│   └── integration/                # Real Zenoh integration tests (requires zenohd)
└── docs/
    ├── PRD.md                      # Full design document
    └── specs/                      # Implementation specs
```

## Testing

```bash
# Unit tests (mocked Zenoh — fast)
pytest tests/unit/

# Integration tests (requires zenohd running)
pytest -m integration tests/integration/

# All tests
pytest
```

## Known Constraints

| Constraint | Impact | Workaround |
|-----------|--------|-----------|
| Channel MCP is research preview | Requires `--dangerously-load-development-channels` | Wait for official release |
| Claude Code requires login | No API key auth | Use claude.ai account |
| `--dangerously-skip-permissions` | Claude executes file ops without confirmation | Use only in trusted environments |
| zenohd must be running | All Zenoh communication routes through local zenohd | Auto-started by start.sh |
| No cross-session history | Messages lost on restart | WeeChat logger saves locally; future: zenohd storage |

## Roadmap

- **Agent-to-agent communication** — agents collaborate via private topics
- **zenohd + storage backend** — persistent message history across sessions
- **Feishu bridge** — Feishu as another Zenoh node
- **Ed25519 signing** — message authenticity verification
- **Web UI** — WeeChat relay API exposing a web frontend

## License

MIT
