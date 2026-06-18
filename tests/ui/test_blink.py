"""Tests for the blink rule: each row blinks when it individually crosses 180s."""

from tests.ui.conftest import inject_rows


def test_blink_on_crossing_180(ui_page):
    """Row gains .blink when crossing from <180 to >=180."""
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": 0}])
    # Advance to 179s — not yet crossing.
    ui_page.clock.fast_forward(179 * 1000)
    row = ui_page.locator("#kartTable tbody tr").first
    assert "blink" not in (row.get_attribute("class") or "")

    # Advance 1 more second → elapsed=180, crosses threshold.
    ui_page.clock.fast_forward(1000)
    assert "blink" in row.get_attribute("class")


def test_blink_removed_after_1000ms(ui_page):
    """The .blink class is removed after the setTimeout(1000) fires."""
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": 0}])
    # Cross the threshold.
    ui_page.clock.fast_forward(180 * 1000)
    row = ui_page.locator("#kartTable tbody tr").first
    assert "blink" in row.get_attribute("class")

    # Advance enough for the setTimeout(1000) to fire.
    ui_page.clock.fast_forward(1000)
    assert "blink" not in (row.get_attribute("class") or "")


def test_no_reblink_on_subsequent_ticks(ui_page):
    """A row that's already >= 180 does not re-blink on the next interval tick."""
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": 0}])
    # Cross threshold and wait for blink to be removed.
    ui_page.clock.fast_forward(180 * 1000)
    ui_page.clock.fast_forward(1000)  # blink removal timeout fires
    row = ui_page.locator("#kartTable tbody tr").first
    assert "blink" not in (row.get_attribute("class") or "")

    # Next interval tick (1s later) — should NOT re-add blink.
    ui_page.clock.fast_forward(1000)
    assert "blink" not in (row.get_attribute("class") or "")


def test_simultaneous_crossing_both_blink(ui_page):
    """Two rows crossing 180 in the same tick: both get .blink, only first .highlight."""
    # Both karts started at timestamp 0.
    inject_rows(ui_page, [
        {"kart": "kart 1", "timestamp": 0},
        {"kart": "kart 2", "timestamp": 0},
    ])
    # Advance to 180s — both cross simultaneously.
    ui_page.clock.fast_forward(180 * 1000)

    rows = ui_page.locator("#kartTable tbody tr")
    # Both blink.
    assert "blink" in rows.nth(0).get_attribute("class")
    assert "blink" in rows.nth(1).get_attribute("class")
    # Only first is highlighted.
    assert "highlight" in rows.nth(0).get_attribute("class")
    assert "highlight" not in (rows.nth(1).get_attribute("class") or "")


def test_readded_row_blinks_again(ui_page):
    """A row removed and re-added with a fresh timestamp blinks on crossing 180 again."""
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": 0}])
    # Cross threshold, let blink expire.
    ui_page.clock.fast_forward(180 * 1000)
    ui_page.clock.fast_forward(1000)

    # Remove and re-add the row with a new timestamp (simulating a new pit stop).
    # New timestamp: current clock time (181s) — so elapsed starts at 0.
    ui_page.evaluate("""() => {
        const tbody = document.querySelector('#kartTable tbody');
        tbody.innerHTML = '';
        const tr = document.createElement('tr');
        const td1 = document.createElement('td');
        td1.textContent = 'kart 1';
        const td2 = document.createElement('td');
        td2.setAttribute('data-timestamp', '181');
        td2.textContent = '00:00';
        tr.appendChild(td1);
        tr.appendChild(td2);
        tbody.appendChild(tr);
    }""")

    # Advance to when this new row crosses 180 (181 + 180 = 361s total clock).
    # Current clock is at 181s (180+1). Need to advance another 180s.
    ui_page.clock.fast_forward(180 * 1000)

    row = ui_page.locator("#kartTable tbody tr").first
    assert "blink" in row.get_attribute("class")
