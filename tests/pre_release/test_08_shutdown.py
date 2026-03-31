# tests/pre_release/test_08_shutdown.py
"""Pre-release: ergo daemon stop + full shutdown verification.

ergo daemon stop/restart is tested here (not in test_03_irc.py) because
stopping ergo kills the session-scoped irc_probe's persistent connection,
which would break agent tests that depend on wait_for_message().
"""
import socket
import time

import pytest


@pytest.mark.order(1)
def test_irc_daemon_stop(cli, e2e_port):
    """Stop ergo daemon directly, verify port released."""
    cli("irc", "daemon", "stop")
    time.sleep(1)
    with pytest.raises(OSError):
        with socket.create_connection(("127.0.0.1", e2e_port), timeout=1):
            pass


@pytest.mark.order(2)
def test_irc_daemon_restart(cli, e2e_port):
    """Restart ergo daemon to verify start-after-stop works."""
    cli("irc", "daemon", "start")
    time.sleep(2)
    with socket.create_connection(("127.0.0.1", e2e_port), timeout=2):
        pass


@pytest.mark.order(3)
def test_shutdown(cli):
    """zchat shutdown stops all agents and infrastructure."""
    result = cli("shutdown", check=False)
    assert result.returncode == 0, f"shutdown failed: {result.stderr}"


@pytest.mark.order(4)
def test_irc_status_after_shutdown(cli):
    """irc status confirms everything is stopped."""
    result = cli("irc", "status", check=False)
    if result.returncode == 0:
        assert "stopped" in result.stdout.lower() or "not running" in result.stdout.lower()
