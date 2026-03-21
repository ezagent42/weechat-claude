# weechat-channel-server

Claude Code Channel plugin — bridges Zenoh P2P messaging and Claude Code via MCP.

## Install

```bash
claude plugin install weechat-channel
```

## Usage

```bash
# Start Claude Code with the channel plugin
claude --dangerously-load-development-channels plugin:weechat-channel

# Agent joins Zenoh mesh as "agent0" (configurable via AGENT_NAME env var)
# Any WeeChat user with weechat-zenoh can /zenoh join @agent0 to chat
```

## Environment Variables

- `AGENT_NAME` — agent identifier (default: `agent0`)
- `ZENOH_CONNECT` — Zenoh endpoints (optional, multicast by default)
