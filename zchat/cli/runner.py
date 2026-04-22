"""Runner module: template environment rendering for agent startup.

Currently exposes only ``render_env`` plus internal helpers
(``_resolve_template_dir`` / ``_parse_env_file`` / ``_load_template_toml``).
``agent_manager`` calls these directly when launching an agent.

REMOVED 2026-04-22: the public runner-resolution surface — ``resolve_runner()``
and ``list_runners()`` — together with the ``[runners.<name>]`` global-config
section those functions consumed.

  Reason : 0 production callers. agent_manager uses ``_resolve_template_dir``
           directly; ``zchat template list`` uses ``template_loader.list_templates``.
           ``list_runners`` was never registered as a Typer command. This was a
           designed-but-never-wired extension point for user-defined runners
           (e.g. ``[runners.local-llama] command = "ollama"``).

  Restore plan (V7+ if custom-runner support is needed):
    1. Re-add ``resolve_runner(name, global_config, user_template_dirs)`` —
       merges ``global_config['runners'][name]`` (command/args/hooks override)
       on top of the resolved template directory and returns a runner spec
       dict consumed by agent_manager.
    2. Re-add ``list_runners(global_config, user_template_dirs)`` — enumerates
       config-defined + template-discovered + builtin runners.
    3. Register a Typer subcommand ``zchat runner add/list/remove`` in app.py
       (Allen never did this step).
    4. Refactor ``agent_manager._spawn_tab`` to call ``resolve_runner`` instead
       of ``_resolve_template_dir`` directly so global-config overrides take
       effect.

  See git blame for ``03ef642 feat: add runner module`` for the original design.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from dotenv import dotenv_values

from zchat.cli import paths

_BUILTIN_DIR = Path(__file__).parent / "templates"


class RunnerNotFoundError(Exception):
    pass


# ---------------------------------------------------------------------------
# Internal helpers (shared with / ported from template_loader)
# ---------------------------------------------------------------------------

def _parse_env_file(path: str) -> dict[str, str]:
    """Parse a .env file into a dict. Skips comments and blank lines."""
    if not Path(path).is_file():
        return {}
    return {k: v for k, v in dotenv_values(path).items() if v is not None}


def _resolve_template_dir(name: str, user_template_dirs: list[str] | None = None) -> str | None:
    """Resolve a template directory by name.  Returns *None* when not found."""
    # Check extra user dirs first
    if user_template_dirs:
        for base in user_template_dirs:
            candidate = Path(base) / name
            if candidate.is_dir() and (candidate / "template.toml").is_file():
                return str(candidate)

    # Default user dir
    user_dir = paths.templates_dir() / name
    if user_dir.is_dir() and (user_dir / "template.toml").is_file():
        return str(user_dir)

    # Built-in
    builtin = _BUILTIN_DIR / name
    if builtin.is_dir() and (builtin / "template.toml").is_file():
        return str(builtin)

    return None


def _load_template_toml(template_dir: str) -> dict:
    """Load template.toml from a directory."""
    toml_path = Path(template_dir) / "template.toml"
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    data.setdefault("hooks", {})
    data["hooks"].setdefault("pre_stop", "")
    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_env(template_dir_or_name: str, context: dict) -> dict[str, str]:
    """Render .env.example with *context*, overlay .env user overrides.

    *template_dir_or_name* can be either an absolute directory path or a
    template name (resolved via ``_resolve_template_dir``).
    """
    tpl_path = Path(template_dir_or_name)
    if tpl_path.is_dir():
        tpl_dir = template_dir_or_name
        name = tpl_path.name
    else:
        name = template_dir_or_name
        resolved = _resolve_template_dir(name)
        if resolved is None:
            raise RunnerNotFoundError(f"Template '{name}' not found")
        tpl_dir = resolved
        tpl_path = Path(tpl_dir)

    example = _parse_env_file(str(tpl_path / ".env.example"))
    rendered: dict[str, str] = {}
    placeholder_re = re.compile(r"\{\{(\w+)\}\}")
    for key, value in example.items():
        rendered[key] = placeholder_re.sub(
            lambda m: str(context.get(m.group(1), "")), value
        )

    # Overlay .env from template dir
    user_env = _parse_env_file(str(tpl_path / ".env"))
    # Also check user-scoped dir (for built-in templates)
    user_dir = paths.templates_dir() / name
    if str(user_dir) != tpl_dir:
        user_env.update(_parse_env_file(str(user_dir / ".env")))
    rendered.update(user_env)

    return rendered
