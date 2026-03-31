# tests/pre_release/test_07_self_update.py
"""Pre-release: self-update command (manual — actually updates binary)."""
import pytest


@pytest.mark.manual
@pytest.mark.order(1)
def test_self_update_check(cli):
    """self-update command is callable."""
    result = cli("self-update", check=False)
    assert isinstance(result.returncode, int)
