# RaceFacer Results HTML

Live karting race pit-stop timer display. Connects to [RaceFacer](https://live.racefacer.com) via Socket.IO and shows real-time elapsed lap times — designed for use on a screen in the pit/depot during endurance kart races with driver swaps.

## Purpose

During a race, drivers must spend a minimum of **3 minutes** in the pit lane when swapping karts (for safety). This display helps pit crews see:

- All karts currently on their "swap lap", sorted by how long they've been waiting
- **Highlighted row** — the first kart that has reached 3 minutes (ready to go)
- **Blink animation** — each kart flashes when it individually crosses the 3-minute threshold

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

In `server.py`, set the WebSocket channel to match your track:

```python
ws_url = 'https://live.racefacer.com:3123/socket.io/'
ws_channel = 'kartarenacheb'
```

## Run

```bash
python server.py
```

Then open http://localhost:5000 in a browser.

## How it works

1. On page load, fetches current race state from RaceFacer REST API
2. Connects to the RaceFacer Socket.IO server and subscribes to the track channel
3. On every kart passing (any kart crosses the finish line), receives updated data
4. Pushes updates to the browser via Turbo Streams (no page reload)
5. Client-side JS updates elapsed times every second and manages highlight/blink logic

## Post-race analysis

During the race, every Socket.IO message is logged as JSONL to `socketio/socketio.log`. After the race, you can:

**Convert to CSV** (denormalized — one row per kart per message):

```bash
python3 tools/convert_to_csv.py [input.log] [output.csv]
```

Defaults to `socketio/socketio.log` → `socketio/race_data_denormalized.csv`.

**Generate a race summary** (lap times per kart, sorted by position):

```bash
python3 tools/race_summary.py socketio/socketio.log
```

## Project layout

```
server.py              Flask app + Socket.IO client
templates/             Jinja2 templates for the live display
tools/                 Post-race analysis scripts
tests/                 Unit tests, mock WS server, and fixtures
socketio/              Race data output (gitignored)
```

## Running tests

Install the test dependencies (uses the `test` extra in `pyproject.toml`) and run pytest:

```bash
uv pip install -e ".[test]"
playwright install chromium
pytest
```

The suite covers the core logic in `server.py` (`process_data`, the Jinja
template filters, `write_jsonl`, and the `create_app` factory) plus UI/component
tests for the client-side JavaScript (elapsed-time formatting, highlight rule,
blink rule) using Playwright with fake timers.
