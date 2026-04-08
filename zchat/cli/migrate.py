"""Config and state migration from tmux to Zellij format."""
from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

import tomli_w


def migrate_config_if_needed(project_dir: str) -> bool:
    """Detect old config format ([tmux] section) and migrate to new format.

    Returns True if migration was performed.
    """
    config_path = Path(project_dir) / "config.toml"
    if not config_path.is_file():
        return False

    with open(config_path, "rb") as f:
        cfg = tomllib.load(f)

    if "tmux" not in cfg:
        return False  # Already new format or no tmux section

    # Backup original
    backup_path = str(config_path) + ".bak"
    shutil.copy2(config_path, backup_path)

    # Extract old values
    irc = cfg.pop("irc", {})
    tmux = cfg.pop("tmux", {})
    agents = cfg.pop("agents", {})

    # Build new config
    new_cfg = {
        "server": irc.get("server", "127.0.0.1"),
        "default_runner": agents.get("default_type", "claude"),
        "default_channels": agents.get("default_channels", ["#general"]),
        "username": agents.get("username", ""),
        "env_file": agents.get("env_file", ""),
        "mcp_server_cmd": agents.get("mcp_server_cmd", ["zchat-channel"]),
        "zellij": {
            # Simplify session name: zchat-{uuid}-{name} → zchat-{name}
            "session": _simplify_session_name(
                tmux.get("session", ""),
                Path(project_dir).name,
            ),
        },
    }

    with open(config_path, "wb") as f:
        tomli_w.dump(new_cfg, f)

    return True


def migrate_state_if_needed(project_dir: str) -> bool:
    """Migrate state.json: window_name → tab_name, remove legacy pane_id.

    Returns True if migration was performed.
    """
    state_path = Path(project_dir) / "state.json"
    if not state_path.is_file():
        return False

    with open(state_path) as f:
        try:
            state = json.load(f)
        except json.JSONDecodeError:
            return False

    changed = False

    # Migrate agent entries
    for name, agent in state.get("agents", {}).items():
        if "window_name" in agent and "tab_name" not in agent:
            agent["tab_name"] = agent.pop("window_name")
            changed = True
        elif "window_name" in agent:
            agent.pop("window_name")
            changed = True
        if "pane_id" in agent:
            agent.pop("pane_id")
            changed = True

    # Migrate IRC state
    irc = state.get("irc", {})
    if "weechat_window" in irc and "weechat_tab" not in irc:
        irc["weechat_tab"] = irc.pop("weechat_window")
        changed = True
    elif "weechat_window" in irc:
        irc.pop("weechat_window")
        changed = True
    if "weechat_pane_id" in irc:
        irc.pop("weechat_pane_id")
        changed = True

    if changed:
        backup_path = str(state_path) + ".bak"
        shutil.copy2(state_path, backup_path)
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)

    return changed


def _simplify_session_name(old_name: str, project_name: str) -> str:
    """Convert zchat-{uuid}-{name} → zchat-{name}."""
    if old_name.startswith("zchat-") and old_name.count("-") >= 2:
        # Strip the UUID part
        return f"zchat-{project_name}"
    return old_name or f"zchat-{project_name}"
