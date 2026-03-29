"""Template loading: resolve, load, render environment variables."""

import os
from pathlib import Path

from zchat.cli.project import ZCHAT_DIR

_BUILTIN_DIR = Path(__file__).parent / "templates"


class TemplateNotFoundError(Exception):
    pass


def resolve_template_dir(name: str) -> str:
    """Resolve template directory. User dir takes priority over built-in."""
    user_dir = os.path.join(ZCHAT_DIR, "templates", name)
    if os.path.isdir(user_dir) and os.path.isfile(os.path.join(user_dir, "template.toml")):
        return user_dir
    builtin = _BUILTIN_DIR / name
    if builtin.is_dir() and (builtin / "template.toml").is_file():
        return str(builtin)
    raise TemplateNotFoundError(f"Template '{name}' not found")
