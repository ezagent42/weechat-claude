# tests/pre_release/test_00_doctor.py
"""Pre-release: environment check (no external dependencies needed)."""
import pytest


@pytest.mark.order(1)
def test_doctor_shows_status(cli):
    """zchat doctor runs successfully."""
    result = cli("doctor", check=False)
    assert result.returncode == 0, f"doctor failed: {result.stderr}"


@pytest.mark.order(2)
def test_doctor_checks_dependencies(cli):
    """doctor output mentions key dependencies."""
    result = cli("doctor", check=False)
    output = result.stdout.lower()
    for dep in ["zellij", "ergo", "weechat"]:
        assert dep in output, f"doctor output missing '{dep}' check"
