"""Integration checks for repository bootstrap scripts."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_start_sh_has_valid_bash_syntax():
    """`start.sh` should pass shell syntax check."""
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["bash", "-n", "start.sh"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_start_sh_fails_fast_when_required_tools_missing():
    """Script should fail early and print missing dependency hints."""
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    # Keep common system bins for bash internals, but drop user-installed tools.
    env["PATH"] = "/usr/bin:/bin"
    result = subprocess.run(
        ["bash", "start.sh"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    assert result.returncode != 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "Missing:" in combined or "not found" in combined.lower()


def test_start_sh_launch_flow_attaches_expected_session(tmp_path):
    """Script should run launch flow and attach to `zchat-<project>` session."""
    repo_root = Path(__file__).resolve().parents[2]
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True)
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True)

    uv_log = logs_dir / "uv.log"
    zellij_log = logs_dir / "zellij.log"

    _write_executable(
        fake_bin / "uv",
        """#!/bin/bash
set -euo pipefail
echo "uv $*" >> "$FAKE_UV_LOG"
if [[ "$*" == *"project show"* ]]; then
  exit "${FAKE_UV_SHOW_EXIT_CODE:-0}"
fi
exit 0
""",
    )
    _write_executable(
        fake_bin / "zellij",
        """#!/bin/bash
set -euo pipefail
echo "zellij $*" >> "$FAKE_ZELLIJ_LOG"
exit 0
""",
    )
    # Dependency checks only need these commands to exist in PATH.
    _write_executable(fake_bin / "claude", "#!/bin/bash\nexit 0\n")
    _write_executable(fake_bin / "weechat", "#!/bin/bash\nexit 0\n")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:/usr/bin:/bin"
    env["FAKE_UV_LOG"] = str(uv_log)
    env["FAKE_ZELLIJ_LOG"] = str(zellij_log)
    # Force project show to fail once so start.sh executes project create.
    env["FAKE_UV_SHOW_EXIT_CODE"] = "1"

    workspace = tmp_path / "ws"
    workspace.mkdir(parents=True)

    result = subprocess.run(
        ["bash", "start.sh", str(workspace), "demo"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout

    uv_calls = uv_log.read_text(encoding="utf-8")
    assert "project show" in uv_calls
    assert "project create demo" in uv_calls
    assert "irc daemon start" in uv_calls
    assert "irc start" in uv_calls
    assert f"agent create agent0 --workspace {workspace}" in uv_calls

    zellij_calls = zellij_log.read_text(encoding="utf-8")
    assert "attach zchat-demo" in zellij_calls
