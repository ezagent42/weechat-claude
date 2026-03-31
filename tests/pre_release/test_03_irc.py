# tests/pre_release/test_03_irc.py
"""Pre-release: IRC daemon and WeeChat lifecycle.

NOTE: ergo daemon stop/restart tests are in test_08_shutdown.py, NOT here.
Stopping ergo mid-session kills the irc_probe's persistent connection,
which would break all subsequent tests that use irc_probe.wait_for_message().
"""
import socket
import time

import pytest


@pytest.mark.order(1)
def test_irc_daemon_start(ergo_server, e2e_port):
    """ergo daemon is started (by fixture) and listening."""
    with socket.create_connection(("127.0.0.1", e2e_port), timeout=2):
        pass


@pytest.mark.order(2)
def test_irc_status_daemon_running(cli, ergo_server):
    """irc status shows daemon running."""
    result = cli("irc", "status")
    assert "running" in result.stdout.lower()


@pytest.mark.order(3)
def test_irc_start_weechat(cli, ergo_server, irc_probe):
    """Start WeeChat via CLI."""
    cli("irc", "start")
    time.sleep(5)


@pytest.mark.order(4)
def test_irc_status_all_running(cli):
    """irc status shows both daemon and weechat running."""
    result = cli("irc", "status")
    output = result.stdout.lower()
    assert output.count("running") >= 2, f"Expected 2+ 'running' in: {result.stdout}"


@pytest.mark.order(5)
def test_irc_stop_weechat(cli):
    """Stop WeeChat via CLI."""
    cli("irc", "stop")
    time.sleep(2)


@pytest.mark.order(6)
def test_irc_status_weechat_stopped(cli):
    """irc status confirms weechat stopped."""
    result = cli("irc", "status")
    lines = result.stdout.lower().split("\n")
    in_weechat = False
    for line in lines:
        if "weechat" in line or "client" in line:
            in_weechat = True
        if in_weechat and "stopped" in line:
            break
    else:
        pytest.fail(f"WeeChat not shown as stopped: {result.stdout}")


@pytest.mark.order(7)
def test_irc_start_weechat_again(cli):
    """Restart WeeChat for subsequent agent tests."""
    cli("irc", "start")
    time.sleep(5)
