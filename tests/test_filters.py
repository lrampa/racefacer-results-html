import re

import pytest

from server import elapsed_time_filter, format_time_filter


class TestElapsedTimeFilter:
    def test_none_returns_na(self):
        assert elapsed_time_filter(None) == "N/A"

    @pytest.mark.parametrize(
        "now, timestamp, expected",
        [
            (1000, 815, "03:05"),    # 185s elapsed -> 3 min 5 s
            (1000, 1000, "00:00"),   # zero elapsed
            (1000, 940, "01:00"),    # exactly 60s
            (6000, 0, "100:00"),     # > 99 minutes
            (1000, 999, "00:01"),    # 1 second
        ],
    )
    def test_known_elapsed(self, now, timestamp, expected):
        assert elapsed_time_filter(timestamp, now=now) == expected

    def test_future_timestamp_negative_behavior(self):
        # Characterization test: documents CURRENT (not desired) behavior.
        # A future timestamp yields a negative divmod result rather than being
        # clamped. now=100, timestamp=200 -> elapsed=-100 -> divmod(-100, 60)
        # == (-2, 20) -> "-2:20". Update this if the behavior is ever fixed.
        assert elapsed_time_filter(200, now=100) == "-2:20"


class TestFormatTimeFilter:
    def test_none_returns_na(self):
        assert format_time_filter(None) == "N/A"

    def test_returns_hh_mm_ss_shape(self):
        # Timezone-dependent value, so assert the shape rather than exact time.
        result = format_time_filter(1700000000)
        assert re.match(r"^\d{2}:\d{2}:\d{2}$", result)

