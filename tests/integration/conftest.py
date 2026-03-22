"""Shared fixtures for integration tests requiring real Zenoh sessions.

Uses client mode connecting to zenohd (tcp/127.0.0.1:7447).
Start zenohd before running: `zenohd &`
"""

import pytest


def _make_zenoh_config():
    """Create a Zenoh config in client mode connecting to local zenohd."""
    import zenoh
    config = zenoh.Config()
    config.insert_json5("mode", '"client"')
    config.insert_json5("connect/endpoints", '["tcp/127.0.0.1:7447"]')
    return config


@pytest.fixture
def zenoh_session():
    """Single Zenoh client session connected to local zenohd."""
    import zenoh
    session = zenoh.open(_make_zenoh_config())
    yield session
    session.close()


@pytest.fixture
def zenoh_sessions():
    """Two Zenoh client sessions for pub/sub testing."""
    import zenoh
    session_a = zenoh.open(_make_zenoh_config())
    session_b = zenoh.open(_make_zenoh_config())
    yield session_a, session_b
    session_a.close()
    session_b.close()
