"""Unit tests for project create CLI parameterization."""
import os
import tomllib
import pytest
from typer.testing import CliRunner
from zchat.cli.app import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Redirect ZCHAT_HOME to temp dir for each test."""
    monkeypatch.setattr("zchat.cli.project.ZCHAT_DIR", str(tmp_path))
    monkeypatch.setattr("zchat.cli.config_cmd.ZCHAT_DIR", str(tmp_path))
    monkeypatch.setattr("zchat.cli.runner.ZCHAT_DIR", str(tmp_path))
    return tmp_path


def _load_config(home, name):
    with open(os.path.join(str(home), "projects", name, "config.toml"), "rb") as f:
        return tomllib.load(f)


def _load_global_config(home):
    path = os.path.join(str(home), "config.toml")
    if os.path.isfile(path):
        with open(path, "rb") as f:
            return tomllib.load(f)
    return {}


def test_create_with_all_params(isolated_home):
    """All CLI options provided → no interactive prompts."""
    result = runner.invoke(app, [
        "project", "create", "test-proj",
        "--server", "127.0.0.1",
        "--port", "6667",
        "--channels", "#general",
        "--agent-type", "claude",
        "--proxy", "",
    ])
    assert result.exit_code == 0, result.output
    cfg = _load_config(isolated_home, "test-proj")
    # Server stored as reference name
    assert cfg["server"] == "local"
    assert "#general" in cfg["default_channels"]
    assert "zellij" in cfg
    assert cfg["zellij"]["session"].startswith("zchat-")
    # Global config should have the server definition
    gcfg = _load_global_config(isolated_home)
    assert "local" in gcfg.get("servers", {})
    assert gcfg["servers"]["local"]["host"] == "127.0.0.1"


def test_create_with_zchat_inside_server(isolated_home):
    """--server zchat.inside.h2os.cloud → auto-creates 'cloud' server in global config."""
    result = runner.invoke(app, [
        "project", "create", "tls-proj",
        "--server", "zchat.inside.h2os.cloud",
        "--channels", "#general",
        "--agent-type", "claude",
        "--proxy", "",
    ])
    assert result.exit_code == 0, result.output
    cfg = _load_config(isolated_home, "tls-proj")
    # The server name is derived from hostname
    assert cfg["server"] in ("cloud", "zchat-inside-h2os-cloud")
    gcfg = _load_global_config(isolated_home)
    srv_name = cfg["server"]
    assert gcfg["servers"][srv_name]["host"] == "zchat.inside.h2os.cloud"
    assert gcfg["servers"][srv_name]["tls"] is True


def test_create_with_explicit_port_tls(isolated_home):
    """Explicit --port and --tls → server stored with those settings."""
    result = runner.invoke(app, [
        "project", "create", "custom-proj",
        "--server", "127.0.0.1",
        "--port", "7000",
        "--tls",
        "--channels", "#dev",
        "--agent-type", "claude",
        "--proxy", "",
    ])
    assert result.exit_code == 0, result.output
    cfg = _load_config(isolated_home, "custom-proj")
    assert cfg["server"] == "local"
    assert "#dev" in cfg["default_channels"]
    gcfg = _load_global_config(isolated_home)
    assert gcfg["servers"]["local"]["port"] == 7000
    assert gcfg["servers"]["local"]["tls"] is True


def test_create_with_proxy(isolated_home):
    """--proxy creates claude.local.env with proxy settings."""
    result = runner.invoke(app, [
        "project", "create", "proxy-proj",
        "--server", "127.0.0.1",
        "--channels", "#general",
        "--agent-type", "claude",
        "--proxy", "10.0.0.1:8080",
    ])
    assert result.exit_code == 0, result.output
    env_path = os.path.join(str(isolated_home), "projects", "proxy-proj", "claude.local.env")
    assert os.path.isfile(env_path)
    content = open(env_path).read()
    assert "HTTP_PROXY=http://10.0.0.1:8080" in content


def test_create_invalid_agent_type(isolated_home):
    """--agent-type with nonexistent template → exit 1."""
    result = runner.invoke(app, [
        "project", "create", "bad-proj",
        "--server", "127.0.0.1",
        "--channels", "#general",
        "--agent-type", "nonexistent-type",
    ])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "error" in result.output.lower()
