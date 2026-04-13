"""Integration tests for non-interactive project and IRC daemon flows."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def integration_home(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("ZCHAT_HOME", str(tmp_path))
    return tmp_path


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _run_cli(repo_root: Path, home: Path, *args: str) -> subprocess.CompletedProcess:
    cmd = [
        "uv",
        "run",
        "--project",
        str(repo_root),
        "python",
        "-m",
        "zchat.cli",
        *args,
    ]
    env = os.environ.copy()
    env["ZCHAT_HOME"] = str(home)
    return subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)


def test_project_flow_non_interactive(repo_root, integration_home):
    """Create/show/set/use(remove attach)/remove works end-to-end."""
    project_name = "integration-project-flow"
    port = _free_port()

    create = _run_cli(
        repo_root,
        integration_home,
        "project",
        "create",
        project_name,
        "--server",
        "127.0.0.1",
        "--port",
        str(port),
        "--channels",
        "#general",
        "--agent-type",
        "claude",
        "--proxy",
        "",
    )
    assert create.returncode == 0, create.stderr or create.stdout

    show = _run_cli(repo_root, integration_home, "--project", project_name, "project", "show", project_name)
    assert show.returncode == 0, show.stderr or show.stdout
    assert f"Project: {project_name}" in show.stdout
    assert "127.0.0.1" in show.stdout

    set_user = _run_cli(repo_root, integration_home, "--project", project_name, "set", "username", "integ-user")
    assert set_user.returncode == 0, set_user.stderr or set_user.stdout
    show2 = _run_cli(repo_root, integration_home, "--project", project_name, "project", "show", project_name)
    assert "integ-user" in show2.stdout

    use = _run_cli(repo_root, integration_home, "project", "use", project_name, "--no-attach")
    assert use.returncode == 0, use.stderr or use.stdout
    assert "Skip attaching session." in use.stdout
    assert (integration_home / "default").read_text().strip() == project_name

    remove = _run_cli(repo_root, integration_home, "project", "remove", project_name)
    assert remove.returncode == 0, remove.stderr or remove.stdout


@pytest.mark.skipif(shutil.which("ergo") is None, reason="ergo not installed")
def test_irc_daemon_lifecycle(repo_root, integration_home):
    """irc daemon start/status/stop succeeds for a temporary project."""
    project_name = "integration-irc-daemon"
    port = _free_port()

    create = _run_cli(
        repo_root,
        integration_home,
        "project",
        "create",
        project_name,
        "--server",
        "127.0.0.1",
        "--port",
        str(port),
        "--channels",
        "#general",
        "--agent-type",
        "claude",
        "--proxy",
        "",
    )
    assert create.returncode == 0, create.stderr or create.stdout

    login = _run_cli(
        repo_root,
        integration_home,
        "--project",
        project_name,
        "auth",
        "login",
        "--method",
        "local",
        "--username",
        "integ-user",
    )
    assert login.returncode == 0, login.stderr or login.stdout

    start = _run_cli(repo_root, integration_home, "--project", project_name, "irc", "daemon", "start")
    assert start.returncode == 0, start.stderr or start.stdout

    status_running = _run_cli(repo_root, integration_home, "--project", project_name, "irc", "status")
    assert status_running.returncode == 0, status_running.stderr or status_running.stdout
    assert "running" in status_running.stdout.lower()

    stop = _run_cli(repo_root, integration_home, "--project", project_name, "irc", "daemon", "stop")
    assert stop.returncode == 0, stop.stderr or stop.stdout

    status_stopped = _run_cli(repo_root, integration_home, "--project", project_name, "irc", "status")
    assert status_stopped.returncode == 0, status_stopped.stderr or status_stopped.stdout
    assert "stopped" in status_stopped.stdout.lower() or "not running" in status_stopped.stdout.lower()
