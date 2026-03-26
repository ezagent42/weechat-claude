# E2E Manual Test Guide

Step-by-step manual test for the full WeeChat-Claude system using `wc-agent` CLI.

## Prerequisites

- `ergo` IRC server binary (`~/.local/bin/ergo`)
- `ergo` languages dir (`~/.local/share/ergo/languages/`)
- `uv`, `tmux`, `weechat`, `claude` installed

## Setup

```bash
cd ~/Workspace/weechat-claude    # or your worktree path

# Sync deps (first time)
(cd wc-agent && uv sync)
(cd weechat-channel-server && uv sync)
```

## Start a tmux session

**All wc-agent commands must be run inside tmux.** Start one first:

```bash
# iTerm2 — native tabs/panes integration
tmux -CC new -s weechat-claude

# Standard terminal
tmux new -s weechat-claude
```

You should now be inside the tmux session. All commands below are run here.

---

## Step 0: Create a project (first time only)

```bash
./wc-agent.sh project create e2e-test
```

Follow the prompts:
```
IRC server [127.0.0.1]:          ← Enter for local ergo
IRC port [6667]:                 ← Enter
TLS [y/N]:                       ← Enter (no TLS for local)
Password:                        ← Enter (empty)
Nickname [your-username]: alice  ← your IRC nick
Default channels [#general]:     ← Enter
```

Set as default project:
```bash
./wc-agent.sh project use e2e-test
```

Verify:
```bash
./wc-agent.sh project list       # should show: e2e-test (default)
./wc-agent.sh project show       # shows IRC server, nick, channels
```

## Step 1: Start ergo IRC server

```bash
./wc-agent.sh irc daemon start
```

Expected output:
```
ergo running (pid XXXXX, port 6667).
```

## Step 2: Start WeeChat

```bash
./wc-agent.sh irc start
```

A new tmux pane opens with WeeChat, labeled **`weechat (alice)`** in iTerm2.
WeeChat auto-connects to IRC and joins `#general`.

Switch to the WeeChat pane:
- **iTerm2**: click the `weechat (alice)` tab
- **Standard tmux**: `Ctrl+b` then arrow keys

## Step 3: Check IRC status

Switch back to your command pane and run:

```bash
./wc-agent.sh irc status
```

Expected:
```
IRC Server:
  status: running (pid XXXXX)
  server: 127.0.0.1:6667

IRC Client (WeeChat):
  status: running (pane %X)
  nick: alice
```

## Step 4: Create agent0

```bash
./wc-agent.sh agent create agent0
```

Expected:
```
Created alice-agent0
  pane: %X
  workspace: /tmp/wc-agent-alice_agent0
```

A new tmux pane opens with Claude, labeled **`agent: alice-agent0`** in iTerm2.
In WeeChat, you should see `alice-agent0` join `#general`.

Optional — to have the agent work in a specific code directory:
```bash
./wc-agent.sh agent create agent0 --workspace /path/to/your/project
```

## Step 5: Test @mention

Switch to the WeeChat pane. In `#general`, type:

```
@alice-agent0 what is the capital of France?
```

Expected: `alice-agent0` responds in `#general` within ~30 seconds.

## Step 6: Send text to agent via CLI

Switch back to your command pane:

```bash
./wc-agent.sh agent send agent0 'Use the reply MCP tool to send "Hello from CLI!" to #general'
```

Expected: `Sent to alice-agent0 (pane %X)`, and the message appears in WeeChat `#general`.

## Step 7: Check agent status

```bash
./wc-agent.sh agent list
./wc-agent.sh agent status agent0
```

Expected:
```
alice-agent0
  status:    running
  uptime:    Xm Xs
  pane:      %X
  workspace: /tmp/wc-agent-alice_agent0
  channels:  #general
```

## Step 8: Create a second agent

```bash
./wc-agent.sh agent create helper
./wc-agent.sh agent list
```

Expected:
- New pane opens labeled **`agent: alice-helper`**
- `alice-helper` joins `#general` in WeeChat

> Note: `agent create helper` produces `alice-helper` on IRC (username prefix from config).

## Step 9: Agent-to-agent communication

```bash
./wc-agent.sh agent send agent0 'Use the reply tool to send "hello helper, please respond with PONG" to "alice-helper"'
```

Switch to the helper's pane — it should receive the message and respond.

## Step 10: Stop helper

```bash
./wc-agent.sh agent stop helper
./wc-agent.sh agent list
```

Expected:
- helper pane exits
- WeeChat shows `alice-helper has quit`
- `agent list` shows helper as `offline`

## Step 11: Restart agent0

```bash
./wc-agent.sh agent restart agent0
```

Expected: agent0 stops and restarts, a new pane opens, rejoins `#general`.

## Step 12: Shutdown everything

```bash
./wc-agent.sh shutdown
```

Expected:
```
Stopped alice-agent0
WeeChat stopped.
ergo stopped.
Shutdown complete.
```

---

## Troubleshooting

### "wc-agent must be run inside a tmux session"

You're not inside tmux. Start one:
```bash
tmux -CC new -s weechat-claude
```

### ergo won't start
- Port in use: `lsof -i :6667`
- Missing languages: `ls ~/.local/share/ergo/languages/`
- Check data dir: `ls ~/.local/share/ergo/`

### Agent not joining IRC
- Check the agent's tmux pane for errors
- Verify ergo is running: `pgrep -x ergo`
- Check config: `./wc-agent.sh project show`
- Proxy issue: ensure `no_proxy` includes `127.0.0.1`

### WeeChat can't connect
- Use `127.0.0.1` not `localhost` (IPv4 vs IPv6)
- Ensure ergo started before WeeChat

### Agent has no reply tool
- Wait ~10s for MCP channel-server to initialize
- Look for `Listening for channel messages` in agent pane
- Check `.mcp.json` in agent workspace: `cat /tmp/wc-agent-*/mcp.json`

### Pane titles not showing in iTerm2
- Use `tmux -CC` mode (not plain `tmux`)
- Ensure `set -g pane-border-status top` in tmux.conf

---

## Project Config Reference

Configs at `~/.wc-agent/projects/<name>/config.toml`:

```toml
[irc]
server = "127.0.0.1"    # IRC server address
port = 6667              # IRC port
tls = false              # TLS encryption
password = ""            # Server password (optional)

[agents]
default_channels = ["#general"]  # Channels agents auto-join
username = "alice"               # IRC nick prefix for agents
```

## Using a Public IRC Server

```bash
./wc-agent.sh project create libera
# IRC server: irc.libera.chat
# IRC port: 6697
# TLS: true
# Nickname: your-nick
# Default channels: #your-channel

./wc-agent.sh project use libera
./wc-agent.sh agent create agent0
```

No `irc daemon start` needed — connects directly to the public server.
