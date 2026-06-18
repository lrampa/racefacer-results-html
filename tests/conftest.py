import json
from pathlib import Path

import pytest

import server

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_message():
    """A captured RaceFacer Socket.IO message (full live-data payload)."""
    with open(FIXTURES / "sample_message.json") as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def reset_app(monkeypatch, tmp_path):
    """Isolate every test from create_app()'s global side effects.

    Autouse so ordering can never leak state: resets the module-level globals
    create_app() mutates and redirects the debug log to a temp path so no
    socketio.log is created in the project root.
    """
    monkeypatch.setattr(server, "DEBUG_LOG", str(tmp_path / "debug.log"))
    yield
    server.app = None
    server.turbo = None
    server.sio = None
    server.latest_message = None
