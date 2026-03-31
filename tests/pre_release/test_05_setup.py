# tests/pre_release/test_05_setup.py
"""Pre-release: WeeChat plugin installation."""
import pytest


@pytest.mark.order(1)
def test_setup_weechat(cli, project):
    """setup weechat --force installs the plugin."""
    result = cli("setup", "weechat", "--force", check=False)
    assert result.returncode == 0, f"setup weechat failed: {result.stderr}"
