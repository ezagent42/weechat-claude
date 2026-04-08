"""Load built-in default configuration from data/defaults.toml."""
from __future__ import annotations

import tomllib
from pathlib import Path

_DEFAULTS_PATH = Path(__file__).parent / "data" / "defaults.toml"
_cache: dict | None = None


def load_defaults() -> dict:
    """Load and cache the defaults.toml file."""
    global _cache
    if _cache is None:
        with open(_DEFAULTS_PATH, "rb") as f:
            _cache = tomllib.load(f)
    return _cache


def default_channels() -> list[str]:
    return load_defaults()["defaults"]["channels"]


def default_runner() -> str:
    return load_defaults()["defaults"]["runner"]


def default_mcp_server_cmd() -> list[str]:
    return load_defaults()["defaults"]["mcp_server_cmd"]


def server_presets() -> dict[str, dict]:
    """Return server presets as {name: {host, port, tls, label}}."""
    return load_defaults().get("server_presets", {})
