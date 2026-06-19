import pytest

from server import process_data

EXPECTED_KEYS = {
    "kart",
    "total_laps",
    "last_time",
    "last_time_raw",
    "last_passing",
    "current_lap_start_timestamp",
    "current_lap_start_microtimestamp",
    "diff_formatted",
}


def make_data(runs):
    return {"data": {"runs": runs}}


class TestMapping:
    def test_sample_message_returns_results(self, sample_message):
        # Use a now far enough after the fixture timestamps for all to pass the filter.
        now = 1721900755 + 200  # 200s after first kart's timestamp
        results = process_data(sample_message, now=now)
        assert len(results) > 0

    def test_result_has_expected_keys(self, sample_message):
        now = 1721900755 + 200
        results = process_data(sample_message, now=now)
        assert set(results[0].keys()) == EXPECTED_KEYS

    def test_missing_optional_fields_use_defaults(self):
        # A run with only 'kart' present; everything else should default.
        data = make_data([{"kart": "kart 7"}])
        result = process_data(data, now=1000)[0]
        assert result["kart"] == "kart 7"
        assert result["total_laps"] == ""
        assert result["last_time"] == 0
        assert result["last_time_raw"] == 0
        assert result["last_passing"] == 0
        assert result["current_lap_start_timestamp"] == -1
        assert result["current_lap_start_microtimestamp"] == -1

    def test_default_lap_start_timestamp_diff(self):
        # Real scenario: a kart that hasn't started a lap yet defaults
        # current_lap_start_timestamp to -1. diff = now - (-1).
        # now=1000 -> 1001s -> divmod(1001, 60) == (16, 41) -> "16:41".
        data = make_data([{"kart": "kart 7"}])
        result = process_data(data, now=1000)[0]
        assert result["diff_formatted"] == "16:41"


class TestEdgeCases:
    def test_no_runs_key_returns_empty(self):
        assert process_data({"data": {}}, now=1000) == []

    def test_empty_runs_returns_empty(self):
        assert process_data(make_data([]), now=1000) == []

    def test_non_kart_names_currently_included(self):
        # Filter-dependent: the KART_NAME_PREFIX filter is currently disabled,
        # so runs whose name does not start with 'kart' are still included.
        # If the filter is re-enabled, update this test.
        data = make_data(
            [
                {"kart": "kart 1", "current_lap_start_timestamp": 100},
                {"kart": "electric 9", "current_lap_start_timestamp": 200},
            ]
        )
        results = process_data(data, now=1000)
        karts = {r["kart"] for r in results}
        assert karts == {"kart 1", "electric 9"}

    def test_short_laps_filtered_out(self):
        # Laps shorter than MIN_LAP_SECONDS (70s) are excluded from results.
        data = make_data(
            [
                {"kart": "kart 1", "current_lap_start_timestamp": 800},   # diff=200 (shown)
                {"kart": "kart 2", "current_lap_start_timestamp": 950},   # diff=50 (filtered)
                {"kart": "kart 3", "current_lap_start_timestamp": 925},   # diff=75 (shown)
            ]
        )
        results = process_data(data, now=1000)
        karts = [r["kart"] for r in results]
        assert "kart 1" in karts
        assert "kart 3" in karts
        assert "kart 2" not in karts


class TestSortingAndDiff:
    def test_sorted_ascending_by_lap_start(self):
        data = make_data(
            [
                {"kart": "kart 3", "current_lap_start_timestamp": 300},
                {"kart": "kart 1", "current_lap_start_timestamp": 100},
                {"kart": "kart 2", "current_lap_start_timestamp": 200},
            ]
        )
        results = process_data(data, now=1000)
        order = [r["current_lap_start_timestamp"] for r in results]
        assert order == [100, 200, 300]

    @pytest.mark.parametrize(
        "lap_start, expected_diff",
        [
            (815, "03:05"),   # 185s -> 3:05 (the >3-minute pit case)
            (900, "01:40"),   # 100s
            (820, "03:00"),   # exactly 3 minutes
            (925, "01:15"),   # 75s (just above MIN_LAP_SECONDS)
        ],
    )
    def test_diff_formatted(self, lap_start, expected_diff):
        data = make_data([{"kart": "kart 1", "current_lap_start_timestamp": lap_start}])
        result = process_data(data, now=1000)[0]
        assert result["diff_formatted"] == expected_diff

