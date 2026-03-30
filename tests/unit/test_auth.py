import json
import os
import time

from zchat.cli.auth import save_token, load_cached_token


def test_save_token_creates_file_with_restricted_perms(tmp_path):
    token_data = {
        "access_token": "test-token",
        "refresh_token": "test-refresh",
        "expires_at": time.time() + 3600,
        "username": "alice",
    }
    save_token(str(tmp_path), token_data)
    auth_file = tmp_path / "auth.json"
    assert auth_file.exists()
    assert oct(auth_file.stat().st_mode & 0o777) == "0o600"


def test_load_cached_token_returns_valid_token(tmp_path):
    token_data = {
        "access_token": "test-token",
        "refresh_token": "test-refresh",
        "expires_at": time.time() + 3600,
        "username": "alice",
    }
    save_token(str(tmp_path), token_data)
    result = load_cached_token(str(tmp_path))
    assert result is not None
    assert result["access_token"] == "test-token"
    assert result["username"] == "alice"


def test_load_cached_token_returns_none_when_expired(tmp_path):
    token_data = {
        "access_token": "expired-token",
        "refresh_token": "test-refresh",
        "expires_at": time.time() - 10,
        "username": "alice",
    }
    save_token(str(tmp_path), token_data)
    result = load_cached_token(str(tmp_path))
    assert result is None


def test_load_cached_token_returns_none_when_missing(tmp_path):
    result = load_cached_token(str(tmp_path))
    assert result is None
