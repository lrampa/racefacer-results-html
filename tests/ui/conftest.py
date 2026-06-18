"""UI test fixtures: http server, Playwright clock, and row-injection helper."""

import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = PROJECT_ROOT / "static"
HARNESS_DIR = Path(__file__).resolve().parent


class _Handler(SimpleHTTPRequestHandler):
    """Serves race.js from static/ and harness.html from tests/ui/."""

    def translate_path(self, path: str) -> str:
        if path == "/race.js" or path.startswith("/race.js?"):
            return str(STATIC_DIR / "race.js")
        # Everything else (e.g. /harness.html) from tests/ui/
        return str(HARNESS_DIR / path.lstrip("/"))

    def log_message(self, *args):
        pass  # silence request logs during tests


@pytest.fixture(scope="session")
def ui_server():
    """Start an HTTP server on a random port serving the harness + race.js."""
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture
def ui_page(page, ui_server):
    """A Playwright page with fake clock installed, navigated to the harness."""
    page.clock.install(time=0)
    page.goto(f"{ui_server}/harness.html")
    return page


def inject_rows(page, rows: list[dict]):
    """Insert rows into #kartTable tbody.

    Each row dict: {"kart": "kart 1", "timestamp": 1234567890}
    """
    page.evaluate(
        """(rows) => {
            const tbody = document.querySelector('#kartTable tbody');
            tbody.innerHTML = '';
            for (const r of rows) {
                const tr = document.createElement('tr');
                const tdKart = document.createElement('td');
                tdKart.textContent = r.kart;
                const tdElapsed = document.createElement('td');
                tdElapsed.setAttribute('data-timestamp', r.timestamp);
                tdElapsed.textContent = '00:00';
                tr.appendChild(tdKart);
                tr.appendChild(tdElapsed);
                tbody.appendChild(tr);
            }
        }""",
        rows,
    )
