# tests/pre_release/test_06_auth.py
"""Pre-release: authentication commands (manual — uses local tokens)."""
import pytest


@pytest.mark.manual
@pytest.mark.order(1)
def test_auth_status(cli, project):
    """auth status runs without error."""
    result = cli("auth", "status", check=False)
    assert result.returncode == 0


@pytest.mark.manual
@pytest.mark.order(2)
def test_auth_refresh(cli, project):
    """auth refresh is callable (may fail if no token)."""
    result = cli("auth", "refresh", check=False)
    assert result.returncode in (0, 1)


@pytest.mark.manual
@pytest.mark.order(3)
def test_auth_logout(cli, project):
    """auth logout runs without error."""
    result = cli("auth", "logout", check=False)
    assert result.returncode == 0
