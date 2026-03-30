"""OIDC authentication: device code flow, token caching, credential management."""
import json
import os
import time


AUTH_FILE = "auth.json"


def save_token(project_dir: str, token_data: dict):
    """Save token data to auth.json with restricted permissions (0600)."""
    auth_path = os.path.join(project_dir, AUTH_FILE)
    fd = os.open(auth_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(token_data, f, indent=2)


def load_cached_token(project_dir: str) -> dict | None:
    """Load cached token if it exists and is not expired. Returns None otherwise."""
    auth_path = os.path.join(project_dir, AUTH_FILE)
    if not os.path.isfile(auth_path):
        return None
    try:
        with open(auth_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("expires_at", 0) < time.time():
        return None
    return data
