"""Smoke test: harness loads race.js and intervals fire under fake clock."""

from tests.ui.conftest import inject_rows


def test_harness_loads_and_interval_fires(ui_page):
    # Inject a row with timestamp = 0. At clock time 0, elapsed is 0.
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": 0}])

    # Fast-forward 1s to trigger the setInterval callback.
    ui_page.clock.fast_forward(1000)

    # After 1s elapsed since epoch 0, elapsed = 1 → "00:01"
    td = ui_page.locator("#kartTable tbody td[data-timestamp]")
    assert td.inner_text() == "00:01"
