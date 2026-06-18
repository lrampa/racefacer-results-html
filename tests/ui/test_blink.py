"""Tests for the flash rule: each row gets .flash for 2s when crossing 180s, then .released."""

from tests.ui.conftest import inject_rows


def test_flash_on_crossing_180(ui_page):
    """Row gains .flash when crossing from <180 to >=180."""
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": 0}])
    ui_page.clock.fast_forward(179 * 1000)
    row = ui_page.locator("#kartTable tbody tr").first
    assert "flash" not in (row.get_attribute("class") or "")

    ui_page.clock.fast_forward(1000)
    assert "flash" in row.get_attribute("class")


def test_flash_replaced_by_released(ui_page):
    """After 2s the .flash is removed and .released is added."""
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": 0}])
    ui_page.clock.fast_forward(180 * 1000)
    row = ui_page.locator("#kartTable tbody tr").first
    assert "flash" in row.get_attribute("class")

    ui_page.clock.fast_forward(2000)
    cls = row.get_attribute("class") or ""
    assert "flash" not in cls
    assert "released" in cls


def test_no_reflash_on_subsequent_ticks(ui_page):
    """A row that's already >= 180 does not re-flash on the next interval tick."""
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": 0}])
    ui_page.clock.fast_forward(180 * 1000)
    ui_page.clock.fast_forward(2000)  # flash -> released
    row = ui_page.locator("#kartTable tbody tr").first
    assert "released" in row.get_attribute("class")

    ui_page.clock.fast_forward(1000)
    cls = row.get_attribute("class") or ""
    assert "flash" not in cls
    assert "released" in cls


def test_simultaneous_crossing_both_flash(ui_page):
    """Two rows crossing 180 in the same tick: both get .flash."""
    inject_rows(ui_page, [
        {"kart": "kart 1", "timestamp": 0},
        {"kart": "kart 2", "timestamp": 0},
    ])
    ui_page.clock.fast_forward(180 * 1000)

    rows = ui_page.locator("#kartTable tbody tr")
    assert "flash" in rows.nth(0).get_attribute("class")
    assert "flash" in rows.nth(1).get_attribute("class")


def test_readded_row_flashes_again(ui_page):
    """A row removed and re-added with a fresh timestamp flashes on crossing 180 again."""
    inject_rows(ui_page, [{"kart": "kart 1", "timestamp": 0}])
    ui_page.clock.fast_forward(180 * 1000)
    ui_page.clock.fast_forward(2000)  # flash -> released

    # Re-add row with new timestamp (simulating new pit stop)
    ui_page.evaluate("""() => {
        const tbody = document.querySelector('#kartTable tbody');
        tbody.innerHTML = '';
        const tr = document.createElement('tr');
        const td1 = document.createElement('td');
        td1.textContent = 'kart 1';
        const td2 = document.createElement('td');
        td2.setAttribute('data-timestamp', '182');
        td2.textContent = '00:00';
        tr.appendChild(td1);
        tr.appendChild(td2);
        tbody.appendChild(tr);
    }""")

    # Advance to cross 180 again (182 + 180 = 362s total)
    ui_page.clock.fast_forward(180 * 1000)
    row = ui_page.locator("#kartTable tbody tr").first
    assert "flash" in row.get_attribute("class")
