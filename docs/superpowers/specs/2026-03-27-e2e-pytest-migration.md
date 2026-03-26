# E2E Test Migration: Bash → Pytest

**Date**: 2026-03-27
**Scope**: Migrate automated e2e tests from bash scripts to pytest, using `irc` library for verification. Keep manual testing as documentation + setup script.

## Overview

Replace `e2e-test.sh` / `helpers.sh` bash scripts with pytest-based e2e tests that:
- Simulate real user operations (tmux, WeeChat, wc-agent CLI)
- Verify via IRC protocol (IrcProbe class using `irc` library)
- Use pytest fixtures for lifecycle management (ergo, tmux, agents)

Manual testing remains shell-based: `e2e-setup.sh` (environment config) + `docs/e2e-manual-test.md` (step-by-step guide).

## Components

### New files

```
tests/e2e/conftest.py      # pytest fixtures: ergo, tmux, project, probe, weechat, agent
tests/e2e/irc_probe.py     # IrcProbe class: nick check, message capture
tests/e2e/test_e2e.py      # Test cases: full user operation simulation
tests/e2e/e2e-setup.sh     # Manual test: environment config (source)
docs/e2e-manual-test.md    # Manual test: step-by-step guide
```

### Delete

```
tests/e2e/e2e-test.sh       # Replaced by pytest
tests/e2e/e2e-test-manual.sh # Split into e2e-setup.sh + docs
tests/e2e/e2e-cleanup.sh    # Replaced by fixture teardown + setup script cleanup
tests/e2e/helpers.sh        # Migrated to Python
```

### Keep

```
tests/e2e/ergo-test.yaml    # Ergo config template (used by conftest.py)
tests/e2e/test-config.toml  # Not needed (conftest generates config dynamically)
```

## IrcProbe Class

```python
# tests/e2e/irc_probe.py
"""IRC probe client for e2e test verification."""

import irc.client
import threading
import time


class IrcProbe:
    """Lightweight IRC client that joins a channel and records messages."""

    def __init__(self, server: str, port: int, nick: str = "e2e-probe"):
        self.server = server
        self.port = port
        self.nick = nick
        self.messages: list[dict] = []  # {"nick": str, "channel": str, "text": str}
        self._reactor = irc.client.Reactor()
        self._conn = None
        self._thread = None

    def connect(self):
        """Connect to IRC server and start reactor in background thread."""
        self._conn = self._reactor.server().connect(self.server, self.port, self.nick)
        self._conn.add_global_handler("pubmsg", self._on_pubmsg)
        self._conn.add_global_handler("privmsg", self._on_privmsg)
        self._thread = threading.Thread(target=self._reactor.process_forever, daemon=True)
        self._thread.start()

    def join(self, channel: str):
        """Join a channel to receive messages."""
        self._conn.join(channel)

    def disconnect(self):
        """Disconnect from IRC."""
        if self._conn:
            self._conn.disconnect()

    def nick_exists(self, nick: str) -> bool:
        """Check if a nick is online via WHOIS."""
        # Synchronous WHOIS using a separate short-lived connection
        result = {"found": False}
        def on_whois(conn, event):
            if event.arguments and nick.lower() in str(event.arguments).lower():
                result["found"] = True
        reactor = irc.client.Reactor()
        conn = reactor.server().connect(self.server, self.port, f"probe-{id(self) % 10000}")
        conn.add_global_handler("whoisuser", on_whois)
        conn.whois([nick])
        deadline = time.time() + 3
        while time.time() < deadline and not result["found"]:
            reactor.process_once(timeout=0.1)
        conn.disconnect()
        return result["found"]

    def wait_for_nick(self, nick: str, timeout: int = 5) -> bool:
        """Poll until nick appears on IRC."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.nick_exists(nick):
                return True
            time.sleep(1)
        return False

    def wait_for_nick_gone(self, nick: str, timeout: int = 10) -> bool:
        """Poll until nick disappears from IRC."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.nick_exists(nick):
                return True
            time.sleep(1)
        return False

    def wait_for_message(self, pattern: str, timeout: int = 15) -> dict | None:
        """Wait for a message matching pattern. Returns the message dict or None."""
        import re
        deadline = time.time() + timeout
        seen = len(self.messages)
        while time.time() < deadline:
            for msg in self.messages[seen:]:
                if re.search(pattern, msg["text"], re.IGNORECASE):
                    return msg
            seen = len(self.messages)
            time.sleep(0.5)
        return None

    def _on_pubmsg(self, conn, event):
        self.messages.append({
            "nick": event.source.nick,
            "channel": event.target,
            "text": event.arguments[0],
        })

    def _on_privmsg(self, conn, event):
        self.messages.append({
            "nick": event.source.nick,
            "channel": None,
            "text": event.arguments[0],
        })
```

## Pytest Fixtures

```python
# tests/e2e/conftest.py

import os
import json
import shutil
import subprocess
import tempfile
import time
import pytest
from irc_probe import IrcProbe

WC_AGENT_HOME = None  # Set per-session


def wc_agent(*args):
    """Run wc-agent CLI command."""
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cmd = [
        "uv", "run", "--project", os.path.join(project_dir, "wc-agent"),
        "python", "-m", "wc_agent.cli",
        "--project", "e2e-test",
        *args,
    ]
    env = os.environ.copy()
    env["WC_AGENT_HOME"] = WC_AGENT_HOME
    if "WC_TMUX_SESSION" not in env:
        env["WC_TMUX_SESSION"] = tmux_session_name()
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def tmux_send_keys(pane_id: str, text: str):
    """Send keys to a tmux pane."""
    subprocess.run(["tmux", "send-keys", "-t", pane_id, text, "Enter"], capture_output=True)


@pytest.fixture(scope="session")
def e2e_port():
    """Unique IRC port for this test session."""
    return 16667 + (os.getpid() % 1000)


@pytest.fixture(scope="session")
def ergo_server(e2e_port):
    """Start ergo on unique port, yield config, stop on teardown."""
    ergo_dir = tempfile.mkdtemp(prefix="e2e-ergo-")
    # Copy languages
    system_langs = os.path.expanduser("~/.local/share/ergo/languages")
    if os.path.isdir(system_langs):
        shutil.copytree(system_langs, os.path.join(ergo_dir, "languages"))
    # Generate config
    result = subprocess.run(["ergo", "defaultconfig"], capture_output=True, text=True)
    config = result.stdout.replace('"127.0.0.1:6667":', f'"127.0.0.1:{e2e_port}":')
    config = "\n".join(l for l in config.split("\n") if "[::1]:6667" not in l)
    # Remove TLS listener
    import re
    config = re.sub(r'":6697":\s*\n.*?min-tls-version:.*?\n', '', config, flags=re.DOTALL)
    conf_path = os.path.join(ergo_dir, "ergo.yaml")
    with open(conf_path, "w") as f:
        f.write(config)
    # Start
    proc = subprocess.Popen(
        ["ergo", "run", "--conf", conf_path],
        cwd=ergo_dir,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    yield {"host": "127.0.0.1", "port": e2e_port, "proc": proc, "dir": ergo_dir}
    proc.terminate()
    proc.wait(timeout=5)
    shutil.rmtree(ergo_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def tmux_session():
    """Create headless tmux session, destroy on teardown."""
    name = f"e2e-pytest-{os.getpid()}"
    subprocess.run(["tmux", "new-session", "-d", "-s", name, "-x", "220", "-y", "60"])
    yield name
    subprocess.run(["tmux", "kill-session", "-t", name], capture_output=True)


@pytest.fixture(scope="session")
def project(ergo_server):
    """Create wc-agent project with test config."""
    global WC_AGENT_HOME
    WC_AGENT_HOME = tempfile.mkdtemp(prefix="e2e-wc-agent-")
    project_dir = os.path.join(WC_AGENT_HOME, "projects", "e2e-test")
    os.makedirs(project_dir)
    config = {
        "irc": {
            "server": ergo_server["host"],
            "port": ergo_server["port"],
            "tls": False,
            "password": "",
        },
        "agents": {
            "default_channels": ["#general"],
            "username": "alice",
        },
    }
    # Write TOML manually
    with open(os.path.join(project_dir, "config.toml"), "w") as f:
        f.write(f'[irc]\nserver = "{config["irc"]["server"]}"\n')
        f.write(f'port = {config["irc"]["port"]}\ntls = false\npassword = ""\n\n')
        f.write('[agents]\ndefault_channels = ["#general"]\nusername = "alice"\n')
    with open(os.path.join(WC_AGENT_HOME, "default"), "w") as f:
        f.write("e2e-test")
    yield "e2e-test"
    shutil.rmtree(WC_AGENT_HOME, ignore_errors=True)


@pytest.fixture(scope="session")
def irc_probe(ergo_server):
    """IRC client that joins #general and records messages."""
    probe = IrcProbe(ergo_server["host"], ergo_server["port"])
    probe.connect()
    time.sleep(1)
    probe.join("#general")
    time.sleep(1)
    yield probe
    probe.disconnect()


@pytest.fixture(scope="session")
def weechat_pane(ergo_server, tmux_session, project):
    """Start WeeChat in tmux via wc-agent irc start."""
    os.environ["WC_TMUX_SESSION"] = tmux_session
    result = wc_agent("irc", "start")
    time.sleep(3)
    # Read pane ID from state
    yield tmux_session  # Commands use the session
    wc_agent("irc", "stop")
```

## Test Cases

```python
# tests/e2e/test_e2e.py

import pytest
import time

class TestE2ELifecycle:
    """Full e2e test simulating real user operations."""

    def test_weechat_connects(self, weechat_pane, irc_probe):
        """wc-agent irc start → WeeChat connects to IRC."""
        assert irc_probe.wait_for_nick("alice", timeout=5)

    def test_agent_joins_irc(self, weechat_pane, irc_probe, project, tmux_session):
        """wc-agent agent create agent0 → agent joins IRC."""
        wc_agent("agent", "create", "agent0")
        assert irc_probe.wait_for_nick("alice-agent0", timeout=15)

    def test_agent_send_to_channel(self, irc_probe):
        """wc-agent agent send → agent replies to #general."""
        wc_agent("agent", "send", "agent0",
                 'Use the reply MCP tool to send "Hello from agent0!" to #general')
        msg = irc_probe.wait_for_message("Hello from agent0", timeout=15)
        assert msg is not None
        assert msg["nick"] == "alice-agent0"

    def test_mention_triggers_reply(self, weechat_pane, irc_probe, tmux_session):
        """@mention in WeeChat → agent auto-responds via IRC."""
        # Get WeeChat pane and send @mention
        # (read pane_id from state.json)
        tmux_send_keys(weechat_pane, "@alice-agent0 what is 2+2?")
        msg = irc_probe.wait_for_message("alice-agent0", timeout=15)
        assert msg is not None

    def test_second_agent(self, irc_probe, project, tmux_session):
        """wc-agent agent create agent1 → joins IRC, sends message."""
        wc_agent("agent", "create", "agent1")
        assert irc_probe.wait_for_nick("alice-agent1", timeout=15)

        wc_agent("agent", "send", "agent1",
                 'Use the reply MCP tool to send "hello from agent1" to #general')
        msg = irc_probe.wait_for_message("agent1", timeout=15)
        assert msg is not None

    def test_agent_stop(self, irc_probe):
        """wc-agent agent stop → agent leaves IRC."""
        wc_agent("agent", "stop", "agent1")
        assert irc_probe.wait_for_nick_gone("alice-agent1", timeout=10)

    def test_shutdown(self, irc_probe):
        """wc-agent shutdown → all agents + WeeChat gone."""
        wc_agent("shutdown")
        assert irc_probe.wait_for_nick_gone("alice-agent0", timeout=10)
```

## Manual Testing

### `tests/e2e/e2e-setup.sh`

Same as current `e2e-test-manual.sh` — sets up environment variables, creates project config, starts ergo. Does NOT run any tests.

### `docs/e2e-manual-test.md`

Step-by-step guide with expected results. Recreated after migration (was deleted earlier).

## Run Commands

```bash
# Automated (all e2e tests)
pytest tests/e2e/ -v --timeout=300

# Single test
pytest tests/e2e/test_e2e.py::TestE2ELifecycle::test_agent_joins_irc -v

# Manual
source tests/e2e/e2e-setup.sh
# Follow docs/e2e-manual-test.md
```

## Timeouts

| Check | Timeout |
|-------|---------|
| IRC connection (alice, ergo) | 5s |
| Agent IRC connection | 15s |
| Claude reply (agent send, @mention) | 15s |
| Agent gone after stop | 10s |

## Dependencies

Add to `weechat-channel-server/pyproject.toml` test deps:
```toml
[project.optional-dependencies]
test = ["pytest", "pytest-asyncio", "pytest-timeout"]
```

`irc` library is already a dependency of channel-server.
