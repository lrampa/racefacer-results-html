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
    def test_returns_flask_app(self, reset_app):
        from flask import Flask

        app = server.create_app()
        assert isinstance(app, Flask)

    def test_filters_registered(self, reset_app):
        app = server.create_app()
        assert "elapsed_time" in app.jinja_env.filters
        assert "format_time" in app.jinja_env.filters

    def test_index_route_registered(self, reset_app):
        app = server.create_app()
        assert any(rule.rule == "/" for rule in app.url_map.iter_rules())


class TestIndexRoute:
    def test_get_index_renders(self, reset_app, monkeypatch, sample_message):
        # Avoid real network and the background Socket.IO client.
        monkeypatch.setattr(server, "fetch_data", lambda: sample_message)
        monkeypatch.setattr(server, "start_socketio_client", lambda: None)

        app = server.create_app()
        with app.test_client() as client:
            response = client.get("/")

        assert response.status_code == 200

