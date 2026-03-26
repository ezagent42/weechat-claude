# E2E Manual Test Guide

Step-by-step manual test for the full WeeChat-Claude system using the new CLI.

## Prerequisites

- `ergo` IRC server binary installed
- `uv` installed
- `tmux` installed
- `weechat` installed
- `claude` CLI installed

## Setup

```bash
# Clone and enter the project
cd ~/workspace/weechat-claude

# Sync deps
(cd wc-agent && uv sync)
(cd weechat-channel-server && uv sync)
```

## Step 1: Create a project

```bash
wc-agent project create local
wc-agent project show
```

Expected: project config created at `~/.wc-agent/projects/local/config.toml`

## Step 2: Start ergo IRC daemon

```bash
wc-agent --project local irc daemon start
```

Expected: ergo process starts, listening on `127.0.0.1:6667`

Verify:
```bash
pgrep -x ergo && echo "running"
```

## Step 3: Start WeeChat (alice)

Open a new terminal or tmux pane, then:

```bash
weechat -r '/server add wc-local 127.0.0.1/6667 -notls -nicks=alice; /connect wc-local; /join #general'
```

Expected: WeeChat connects to ergo, joins `#general`

## Step 4: Create agent0

```bash
wc-agent --project local agent create agent0 --workspace ~/workspace/weechat-claude
```

Expected:
- A new tmux pane opens with `claude` running
- `alice-agent0` joins `#general` in WeeChat

Verify in WeeChat:
```
/names #general
```
Should show: `alice` and `alice-agent0`

## Step 5: Send a message to agent0

In WeeChat `#general`:
```
@alice-agent0 what is the capital of France?
```

Expected: `alice-agent0` responds in `#general` within ~30 seconds

## Step 6: List agents

```bash
wc-agent --project local agent list
```

Expected: shows `agent0` with status `running`

## Step 7: Send text directly to agent

```bash
wc-agent --project local agent send agent0 "Please say hello to the channel"
```

Expected: agent0 sends a message to `#general`

## Step 8: Create a second agent

```bash
wc-agent --project local agent create agent1 --workspace ~/workspace/weechat-claude
```

Expected:
- New pane opens with `claude` for agent1
- `alice-agent1` joins `#general`

## Step 9: Stop agent1

```bash
wc-agent --project local agent stop agent1
```

Expected:
- agent1 pane exits
- WeeChat shows `alice-agent1 has quit`

## Step 10: Check agent status

```bash
wc-agent --project local agent status agent0
```

Expected: shows agent0 is running, its tmux pane ID, and IRC nick

## Step 11: Restart agent0

```bash
wc-agent --project local agent restart agent0
```

Expected: agent0 reconnects to IRC, rejoins `#general`

## Step 12: Shutdown everything

```bash
wc-agent --project local shutdown
```

Expected:
- All agents stop
- IRC connections closed
- WeeChat shows quit messages

## Troubleshooting

### ergo won't start
- Check if port 6667 is already in use: `lsof -i :6667`
- Check ergo logs: `~/.local/share/ergo/`

### Agent not joining IRC
- Check channel-server logs in the agent's tmux pane
- Verify ergo is running: `pgrep -x ergo`
- Check project config: `wc-agent --project local project show`

### WeeChat can't connect
- Ensure ergo started before WeeChat
- Try `127.0.0.1` not `localhost` (IPv4 vs IPv6 issues)

## Project Config

Project configs are stored at `~/.wc-agent/projects/<name>/config.toml`:

```toml
[irc]
server = "127.0.0.1"
port = 6667
tls = false
password = ""

[agents]
default_channels = ["#general"]
username = "alice"
```

Edit this file to change IRC server, port, or default username.
