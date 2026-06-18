# Unit Tests Implementation Plan

## Problem Statement

The core live-display logic in `server.py` has no automated tests. After the `create_app()` refactor, the pure functions are importable without side effects, so we can add a deterministic unit test suite.

## Scope

- **In scope:** `server.py` logic — `process_data`, `elapsed_time_filter`, `format_time_filter`, `write_jsonl`, `create_app` wiring, `index()` route behavior (mocked network).
- **Out of scope:** `fetch_data` (thin network wrapper), `tools/` scripts, UI/E2E tests (planned separately), `message()` handler inside `start_socketio_client` (tightly coupled to runtime state).

## Design Decisions

- **Time handling:** Inject an optional `now` parameter into `elapsed_time_filter` and `process_data` (default `None` → use real time). This is backward-compatible — Jinja calls filters with one positional arg, so `now` defaults to `None` and falls through to `datetime.now().timestamp()` / `time.time()`. In `process_data`, the injected `now` replaces `time.time()` for the diff calculation.
- **Timezone:** `format_time_filter` uses local tz; tests assert output shape (`HH:MM:SS`) rather than exact values.
- **JSONL tests:** `monkeypatch.setattr(server, 'JSONL_LOG', tmp_path/'out.log')` to isolate file writes.
- **Global state isolation:** Tests that call `create_app()` must reset module globals (`server.app = None`, `server.turbo = None`, `server.sio = None`) after each test via a fixture. `configure_logging()` writes to `DEBUG_LOG` in CWD — monkeypatch `server.DEBUG_LOG` to a temp path.
- **Negative timestamps:** Test and document current behavior (negative elapsed → negative `MM:SS`). No fix in this iteration.
- **Framework:** pytest (already in `pyproject.toml` test extra).

## Test Structure

```
tests/
├── conftest.py                 # sample_message fixture, app cleanup fixture
├── test_filters.py             # elapsed_time_filter, format_time_filter
├── test_process_data.py        # mapping, defaults, empty input, sorting, diff
├── test_write_jsonl.py         # JSONL output, append, dir creation, unwrapping
└── test_app_factory.py         # create_app wiring, side-effect-free import, index route
```

## Tasks

### Task 1: Establish the test harness

**Objective:** Confirm pytest runs against the project and that importing `server` has no side effects.

**Guidance:** Add `tests/conftest.py` with:
- A `sample_message` fixture that loads `tests/fixtures/sample_message.json`.
- A `reset_app` autouse fixture for `test_app_factory.py` that resets `server.app`, `server.turbo`, `server.sio` to `None` after each test, and monkeypatches `server.DEBUG_LOG` to a temp path to avoid creating `socketio.log` in the project root.

Add a smoke test asserting `import server` succeeds and `server.app is None` before `create_app()`.

**Test:** `pytest -q` collects and passes the smoke test.

### Task 2: Inject `now` and test `elapsed_time_filter`

**Objective:** Make elapsed-time formatting deterministic and cover it.

**Guidance:** Refactor signature to `elapsed_time_filter(timestamp, now=None)`. Implementation:
```python
def elapsed_time_filter(timestamp, now=None):
    if timestamp is None:
        return "N/A"
    if now is None:
        now = datetime.now().timestamp()
    elapsed = now - timestamp
    minutes, seconds = divmod(int(elapsed), 60)
    return f"{minutes:02d}:{seconds:02d}"
```

Tests (parametrized in `test_filters.py`):
- `None` → `"N/A"`
- `now=1000, timestamp=815` → 185s → `"03:05"`
- `now=1000, timestamp=1000` → 0s → `"00:00"`
- `now=6000, timestamp=0` → 6000s → `"100:00"` (>99 min)
- `now=100, timestamp=200` → -100s → document current behavior (negative divmod)

**Demo:** `pytest tests/test_filters.py` passes; live page still renders (Jinja calls with 1 arg).

### Task 3: Test `format_time_filter`

**Objective:** Cover the timestamp→clock formatter without tz flakiness.

**Guidance:** Tests in `test_filters.py`:
- `None` → `"N/A"`
- A real timestamp (e.g. `1700000000`) returns a string matching `^\d{2}:\d{2}:\d{2}$`

### Task 4: Test `process_data` mapping and edge cases

**Objective:** Verify run extraction, field defaults, and empty inputs.

**Guidance:** Refactor signature to `process_data(data, now=None)`. When `now` is provided, use it instead of `time.time()` for the diff calculation:
```python
def process_data(data, now=None):
    ...
    current_timestamp = now if now is not None else time.time()
    ...
```

Tests in `test_process_data.py`:
- Each result dict has expected keys: `kart`, `total_laps`, `last_time`, `last_time_raw`, `last_passing`, `current_lap_start_timestamp`, `current_lap_start_microtimestamp`, `diff_formatted`.
- Missing optional run fields fall back to defaults (`''`, `0`, `-1`).
- `data = {'data': {}}` (no `runs` key) → `[]`.
- `data = {'data': {'runs': []}}` → `[]`.
- Non-"kart" names are currently included (kart filter disabled) — assert and comment as filter-dependent.

### Task 5: Test `process_data` sorting and `diff_formatted`

**Objective:** Lock in ordering and the elapsed-since-lap-start calculation.

**Guidance:** Tests in `test_process_data.py`:
- Results are sorted ascending by `current_lap_start_timestamp`.
- With `now=1000` and known timestamps (e.g. `815`, `900`), assert `diff_formatted` equals `"03:05"` and `"01:40"` respectively.
- Verify the >3-minute pit case: timestamp 180+ seconds old → diff shows `"03:00"` or more.

### Task 6: Test `write_jsonl`

**Objective:** Verify JSONL output, appending, and directory creation.

**Guidance:** Use `monkeypatch.setattr(server, 'JSONL_LOG', tmp_path / 'out.log')`. Tests in `test_write_jsonl.py`:
- One call writes exactly one line parseable as JSON with `log_ts` (string) and `data` keys.
- Two calls append (file has two lines).
- If parent dir doesn't exist, it's auto-created.
- Input `{'data': {'foo': 1}}` → record's `data` field is `{'foo': 1}` (unwrapped via `.get('data', data)`).
- Input `{'foo': 1}` (no `data` key) → record's `data` field is `{'foo': 1}` (fallback to whole dict).
- Input is a non-dict (e.g. a list) → record's `data` field is the input as-is.

### Task 7: Wire up — `create_app` test, `index()` route, full suite, and docs

**Objective:** Cover app assembly, route behavior, and finalize.

**Guidance:** In `test_app_factory.py`:
- `create_app()` returns a Flask app instance.
- `elapsed_time` and `format_time` filters are registered.
- `/` route is mapped.
- `index()` route test: monkeypatch `server.fetch_data` to return the `sample_message` fixture, then use Flask test client `GET /` — assert 200 response.

Finalize:
- Run entire suite to confirm all green.
- Add a "Running tests" section to `README.md`:
  ```
  uv pip install -e ".[test]"
  pytest
  ```

**Test:** Full `pytest` run all green.
