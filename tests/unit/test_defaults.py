"""Tests for defaults.toml loading."""
from zchat.cli.defaults import (
    load_defaults, default_channels, default_runner,
    default_mcp_server_cmd, server_presets,
)


def test_load_defaults_has_required_sections():
    d = load_defaults()
    assert "defaults" in d
    assert "server_presets" in d


def test_default_channels():
    assert isinstance(default_channels(), list)
    assert len(default_channels()) > 0


def test_default_runner():
    assert isinstance(default_runner(), str)
    assert len(default_runner()) > 0


def test_default_mcp_server_cmd():
    assert isinstance(default_mcp_server_cmd(), list)
    assert len(default_mcp_server_cmd()) > 0


def test_server_presets_not_empty():
    presets = server_presets()
    assert len(presets) >= 2  # at least cloud + local


def test_server_presets_have_required_fields():
    for name, preset in server_presets().items():
        assert "host" in preset, f"preset '{name}' missing 'host'"
        assert "port" in preset, f"preset '{name}' missing 'port'"
        assert "label" in preset, f"preset '{name}' missing 'label'"
