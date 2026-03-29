import os
import pytest
from zchat.cli.template_loader import resolve_template_dir, TemplateNotFoundError


def test_resolve_user_template(tmp_path, monkeypatch):
    """User template dir takes priority over built-in."""
    monkeypatch.setattr("zchat.cli.template_loader.ZCHAT_DIR", str(tmp_path))
    user_tpl = tmp_path / "templates" / "my-bot"
    user_tpl.mkdir(parents=True)
    (user_tpl / "template.toml").write_text('[template]\nname = "my-bot"\n')
    assert resolve_template_dir("my-bot") == str(user_tpl)


def test_resolve_builtin_template(tmp_path, monkeypatch):
    """Falls back to built-in template."""
    monkeypatch.setattr("zchat.cli.template_loader.ZCHAT_DIR", str(tmp_path))
    result = resolve_template_dir("claude")
    assert "templates/claude" in result
    assert os.path.isfile(os.path.join(result, "template.toml"))


def test_resolve_unknown_template_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("zchat.cli.template_loader.ZCHAT_DIR", str(tmp_path))
    with pytest.raises(TemplateNotFoundError):
        resolve_template_dir("nonexistent")
