"""Tests for the highlight rule: first row with elapsed >= 180s gets .highlight."""

from tests.ui.conftest import inject_rows


def test_no_highlight_when_all_below_180(ui_page):
    inject_rows(ui_page, [
        {"kart": "kart 1", "timestamp": 0},
        {"kart": "kart 2", "timestamp": 0},
    ])
    # At clock=0, elapsed=0 for both. Advance to 179s — still below threshold.
    ui_page.clock.fast_forward(179 * 1000)

    rows = ui_page.locator("#kartTable tbody tr")
    assert rows.nth(0).get_attribute("class") is None or "highlight" not in rows.nth(0).get_attribute("class")
    assert rows.nth(1).get_attribute("class") is None or "highlight" not in rows.nth(1).get_attribute("class")


def test_first_qualifying_row_gets_highlight(ui_page):
    # kart 1 started at 0 (oldest), kart 2 at 100.
    inject_rows(ui_page, [
        {"kart": "kart 1", "timestamp": 0},
        {"kart": "kart 2", "timestamp": 100},
    ])
    # Advance to 180s → kart 1 elapsed=180 (qualifies), kart 2 elapsed=80 (no).
    ui_page.clock.fast_forward(180 * 1000)

    rows = ui_page.locator("#kartTable tbody tr")
    assert "highlight" in rows.nth(0).get_attribute("class")
    cls1 = rows.nth(1).get_attribute("class") or ""
    assert "highlight" not in cls1


def test_only_first_row_highlighted_when_multiple_qualify(ui_page):
    # Both rows have been waiting > 180s.
    inject_rows(ui_page, [
        {"kart": "kart 1", "timestamp": 0},
        {"kart": "kart 2", "timestamp": 0},
    ])
    ui_page.clock.fast_forward(200 * 1000)

    rows = ui_page.locator("#kartTable tbody tr")
    assert "highlight" in rows.nth(0).get_attribute("class")
    cls1 = rows.nth(1).get_attribute("class") or ""
    assert "highlight" not in cls1


def test_highlight_moves_when_first_row_timestamp_changes(ui_page):
    # Initially kart 1 qualifies (oldest).
    inject_rows(ui_page, [
        {"kart": "kart 1", "timestamp": 0},
        {"kart": "kart 2", "timestamp": 10},
    ])
    ui_page.clock.fast_forward(200 * 1000)

    rows = ui_page.locator("#kartTable tbody tr")
    assert "highlight" in rows.nth(0).get_attribute("class")

    # Simulate kart 1 leaving (new lap) by updating its timestamp to "just now".
    ui_page.evaluate("""() => {
        const td = document.querySelector('#kartTable tbody tr:first-child td[data-timestamp]');
        td.setAttribute('data-timestamp', '200');
        td.removeAttribute('data-prev-elapsed');
    }""")
    # Tick once more to re-evaluate.
    ui_page.clock.fast_forward(1000)

    # Now kart 1 elapsed=1 (no longer qualifies), kart 2 elapsed=191 (qualifies).
    assert "highlight" not in (rows.nth(0).get_attribute("class") or "")
    assert "highlight" in rows.nth(1).get_attribute("class")
