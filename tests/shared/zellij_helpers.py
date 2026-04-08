# tests/shared/zellij_helpers.py
"""Zellij helper functions shared across test suites."""
import re
import time

from zchat.cli import zellij


def send_keys(session_name: str, target: str, text: str, enter: bool = True) -> None:
    """Send keys to a Zellij tab (by name).

    Args:
        session_name: Zellij session name
        target: Tab name to send to
        text: Text to type
        enter: Whether to press Enter after typing
    """
    pane_id = zellij.get_pane_id(session_name, target)
    if not pane_id:
        return
    if enter:
        zellij.send_command(session_name, pane_id, text)
    else:
        # paste without Enter
        from zchat.cli.zellij import _run
        _run(["paste", "--pane-id", pane_id, text], session=session_name)


def capture_pane(session_name: str, target: str) -> str:
    """Capture the visible content of a Zellij tab."""
    pane_id = zellij.get_pane_id(session_name, target)
    if not pane_id:
        return ""
    return zellij.dump_screen(session_name, pane_id)


def wait_for_content(session_name: str, target: str, pattern: str,
                     timeout: float = 10.0) -> bool:
    """Wait until pane content matches a regex pattern."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        content = capture_pane(session_name, target)
        if re.search(pattern, content):
            return True
        time.sleep(0.5)
    return False
