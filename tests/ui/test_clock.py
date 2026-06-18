"""Tests for the updateClock() function — fills #clock with HH:MM:SS."""

import re


def test_clock_displays_time_on_load(ui_page):
    """After page load, #clock should show HH:MM:SS (clock installed at epoch 0)."""
    text = ui_page.locator("#clock").inner_text()
    assert re.match(r"^\d{2}:\d{2}:\d{2}$", text)


def test_clock_advances_on_tick(ui_page):
    """After fast-forwarding 1 second, #clock text should change."""
    before = ui_page.locator("#clock").inner_text()
    ui_page.clock.fast_forward(1000)
    after = ui_page.locator("#clock").inner_text()
    assert re.match(r"^\d{2}:\d{2}:\d{2}$", after)
    assert after != before
