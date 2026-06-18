"""Tests for elapsed-time MM:SS formatting in the browser."""

import pytest

from tests.ui.conftest import inject_rows


@pytest.mark.parametrize(
    "clock_time, timestamp, expected",
    [
        (185, 0, "03:05"),     # 185s elapsed
        (5, 0, "00:05"),       # 5s
        (60, 0, "01:00"),      # exactly 1 min
        (3600, 0, "60:00"),    # 1 hour
        (180, 0, "03:00"),     # exactly 3 min (the pit threshold)
    ],
)
def test_elapsed_formatting(ui_page, clock_time, timestamp, expected):
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": timestamp}])
    ui_page.clock.fast_forward(clock_time * 1000)

    td = ui_page.locator("#kartTable tbody td[data-timestamp]")
    assert td.inner_text() == expected


def test_elapsed_zero(ui_page):
    """At time 0 with timestamp 0, elapsed is 0 → '00:00'."""
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": 0}])
    ui_page.evaluate("updateElapsedTimes()")

    td = ui_page.locator("#kartTable tbody td[data-timestamp]")
    assert td.inner_text() == "00:00"


def test_negative_elapsed_future_timestamp(ui_page):
    """Timestamp in the future: documents current (quirky) behavior."""
    # clock=0, timestamp=100 → elapsed = -100
    # JS: Math.floor(-100/60)=-2, (-100)%60=-40
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": 100}])
    ui_page.evaluate("updateElapsedTimes()")

    td = ui_page.locator("#kartTable tbody td[data-timestamp]")
    text = td.inner_text()
    # Negative elapsed produces a string with a minus sign.
    assert "-" in text, f"Expected negative indicator, got: {text}"
