import server


def test_import_has_no_side_effects():
    """Importing server must not create the Flask app or clients."""
    assert server.app is None
    assert server.turbo is None
    assert server.sio is None


def test_pure_functions_are_importable():
    assert callable(server.process_data)
    assert callable(server.elapsed_time_filter)
    assert callable(server.format_time_filter)
    assert callable(server.write_jsonl)
    assert callable(server.create_app)


class TestCreateApp:
    def test_returns_flask_app(self):
        from flask import Flask

        app = server.create_app()
        assert isinstance(app, Flask)

    def test_filters_registered(self):
        app = server.create_app()
        assert "elapsed_time" in app.jinja_env.filters
        assert "format_time" in app.jinja_env.filters

    def test_index_route_registered(self):
        app = server.create_app()
        assert any(rule.rule == "/" for rule in app.url_map.iter_rules())


class _ThreadingShim:
    """Stand-in for the threading module so index() never starts a real thread."""

    @staticmethod
    def enumerate():
        return []

    class Thread:
        def __init__(self, *args, **kwargs):
            self.name = kwargs.get("name")

        def start(self):
            pass


class TestIndexRoute:
    def test_get_index_renders(self, monkeypatch, sample_message):
        # Avoid real network, the background Socket.IO client, and real threads.
        monkeypatch.setattr(server, "fetch_data", lambda: sample_message)
        monkeypatch.setattr(server, "start_socketio_client", lambda: None)
        monkeypatch.setattr(server, "threading", _ThreadingShim)

        app = server.create_app()
        with app.test_client() as client:
            response = client.get("/")

        assert response.status_code == 200

