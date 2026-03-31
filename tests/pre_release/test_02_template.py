# tests/pre_release/test_02_template.py
"""Pre-release: template management."""
import pytest

TEST_TEMPLATE = "prerelease-test-tpl"


@pytest.mark.order(1)
def test_template_list(cli, project):
    """template list includes built-in 'claude' template."""
    result = cli("template", "list")
    assert "claude" in result.stdout


@pytest.mark.order(2)
def test_template_show(cli, project):
    """template show displays claude template details."""
    result = cli("template", "show", "claude")
    assert "claude" in result.stdout.lower()


@pytest.mark.order(3)
def test_template_create(cli, project):
    """template create scaffolds a new template directory."""
    result = cli("template", "create", TEST_TEMPLATE)
    assert result.returncode == 0
    assert "scaffold" in result.stdout.lower() or TEST_TEMPLATE in result.stdout


@pytest.mark.order(4)
def test_template_set(cli, project):
    """template set writes .env variable."""
    result = cli("template", "set", TEST_TEMPLATE, "MY_VAR", "my_value")
    assert result.returncode == 0
