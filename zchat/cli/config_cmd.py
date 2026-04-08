"""Global configuration management (~/.zchat/config.toml)."""
from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w

from zchat.cli import paths

_DEFAULTS = {
    "update": {
        "channel": "main",
        "auto_upgrade": True,
    },
}


def load_global_config(path: str | None = None) -> dict:
    """Load global config, filling defaults for missing keys."""
    p = Path(path) if path else paths.global_config_path()
    data: dict = {}
    if p.is_file():
        with open(p, "rb") as f:
            data = tomllib.load(f)
    for section, defaults in _DEFAULTS.items():
        data.setdefault(section, {})
        for key, value in defaults.items():
            data[section].setdefault(key, value)
    return data


def save_global_config(config: dict, path: str | None = None) -> None:
    """Write global config to TOML file."""
    p = Path(path) if path else paths.global_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        tomli_w.dump(config, f)


def resolve_server(server_ref: str, global_config: dict | None = None) -> dict:
    """Resolve a server reference to connection details.

    *server_ref* can be a name in ``[servers.<name>]`` or a raw hostname.
    Returns dict with keys: host, port, tls, password.
    """
    if global_config is None:
        global_config = load_global_config()
    servers = global_config.get("servers", {})
    if server_ref in servers:
        srv = servers[server_ref]
        return {
            "host": srv.get("host", "127.0.0.1"),
            "port": srv.get("port", 6667),
            "tls": srv.get("tls", False),
            "password": srv.get("password", ""),
        }
    # Check if it matches a known preset by hostname
    from zchat.cli.defaults import server_presets
    for _name, preset in server_presets().items():
        if preset["host"] == server_ref:
            return {"host": server_ref, "port": preset["port"],
                    "tls": preset.get("tls", False), "password": ""}
    # Unknown hostname — use plain defaults
    return {"host": server_ref, "port": 6667, "tls": False, "password": ""}


def ensure_server_in_global(name: str, host: str, port: int, tls: bool,
                            password: str = "", global_config: dict | None = None) -> dict:
    """Add a server entry to global config if it doesn't exist. Returns the global config."""
    if global_config is None:
        global_config = load_global_config()
    servers = global_config.setdefault("servers", {})
    if name not in servers:
        servers[name] = {"host": host, "port": port, "tls": tls}
        if password:
            servers[name]["password"] = password
        save_global_config(global_config)
    return global_config


def get_config_value(config: dict, dotted_key: str):
    """Get a value from config by dotted key (e.g. 'update.channel')."""
    parts = dotted_key.split(".")
    node = config
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def set_config_value(config: dict, dotted_key: str, value: str | int | bool | list) -> None:
    """Set a value in config by dotted key. Auto-converts 'true'/'false' to bool when value is str."""
    parts = dotted_key.split(".")
    node = config
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    if isinstance(value, str):
        if value.lower() in ("true", "false"):
            node[parts[-1]] = value.lower() == "true"
        else:
            node[parts[-1]] = value
    else:
        node[parts[-1]] = value
