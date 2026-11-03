from __future__ import annotations

"""Tests for accuracy analytics module.

Uses small, hand-verifiable datasets with known expected values.
"""

import math
from datetime import datetime

from app.analytics.accuracy import AccuracyAnalyzer
from app.schemas.elexon import SelectedForecast


def _make_sf(
    forecast_mw: float | None,
    actual_mw: float | None,
    hour: int = 12,
    day: int = 15,
) -> SelectedForecast:
    """Helper to create a SelectedForecast with minimal required fields."""
    error = None
    abs_error = None
    if forecast_mw is not None and actual_mw is not None:
        error = forecast_mw - actual_mw
        abs_error = abs(error)

    return SelectedForecast(
        start_time=datetime(2026, 1, day, hour, 0, 0),
        settlement_date=f"2026-01-{day:02d}",
        settlement_period=hour * 2 + 1,
        forecast_mw=forecast_mw,
        actual_mw=actual_mw,
        publish_time=datetime(2026, 1, day - 1, 8, 0, 0),
        cutoff_time=datetime(2026, 1, day - 1, 9, 0, 0),
        forecast_age_hours=28.0 if forecast_mw is not None else None,
        error_mw=error,
        abs_error_mw=abs_error,
        has_actual=actual_mw is not None,
        has_forecast=forecast_mw is not None,
    )


class TestAccuracyMetrics:
    """Test metric calculations with known values."""

    def test_mae_simple(self):
        """MAE of [+100, -200, +300] = mean([100, 200, 300]) = 200."""
        records = [
            _make_sf(5100, 5000, hour=0),   # error = +100
            _make_sf(4800, 5000, hour=1),   # error = -200
            _make_sf(5300, 5000, hour=2),   # error = +300
        ]
        analyzer = AccuracyAnalyzer(records)
        assert analyzer.mae() == 200.0

    def test_rmse_simple(self):
        """RMSE of [+100, -200, +300] = sqrt(mean([10000, 40000, 90000]))."""
        records = [
            _make_sf(5100, 5000, hour=0),   # error = 100
            _make_sf(4800, 5000, hour=1),   # error = -200
            _make_sf(5300, 5000, hour=2),   # error = 300
        ]
        analyzer = AccuracyAnalyzer(records)
        expected = math.sqrt((10000 + 40000 + 90000) / 3)
        assert abs(analyzer.rmse() - round(expected, 2)) < 0.01

    def test_mbe_positive_overforecast(self):
        """MBE of [+100, +200, +300] = 200 (systematic overforecast)."""
        records = [
            _make_sf(5100, 5000, hour=0),
            _make_sf(5200, 5000, hour=1),
            _make_sf(5300, 5000, hour=2),
        ]
        analyzer = AccuracyAnalyzer(records)
        assert analyzer.mbe() == 200.0

    def test_mbe_negative_underforecast(self):
        """MBE of [-100, -200, -300] = -200 (systematic underforecast)."""
        records = [
            _make_sf(4900, 5000, hour=0),
            _make_sf(4800, 5000, hour=1),
            _make_sf(4700, 5000, hour=2),
        ]
        analyzer = AccuracyAnalyzer(records)
        assert analyzer.mbe() == -200.0

    def test_mbe_balanced(self):
        """MBE of [+100, -100] = 0 (no systematic bias)."""
        records = [
            _make_sf(5100, 5000, hour=0),
            _make_sf(4900, 5000, hour=1),
        ]
        analyzer = AccuracyAnalyzer(records)
        assert analyzer.mbe() == 0.0

    def test_max_abs_error(self):
        records = [
            _make_sf(5100, 5000, hour=0),   # |100|
            _make_sf(4500, 5000, hour=1),   # |500|
            _make_sf(5200, 5000, hour=2),   # |200|
        ]
        analyzer = AccuracyAnalyzer(records)
        assert analyzer.max_abs_error() == 500.0

    def test_median_abs_error(self):
        records = [
            _make_sf(5100, 5000, hour=0),   # |100|
            _make_sf(4500, 5000, hour=1),   # |500|
            _make_sf(5200, 5000, hour=2),   # |200|
        ]
        analyzer = AccuracyAnalyzer(records)
        assert analyzer.median_abs_error() == 200.0

    def test_zero_actual_generation(self):
        """Should handle zero actual without error."""
        records = [_make_sf(200, 0.0, hour=0)]
        analyzer = AccuracyAnalyzer(records)
        assert analyzer.mae() == 200.0
        assert analyzer.mbe() == 200.0

    def test_perfect_forecast(self):
        """All errors are zero."""
        records = [
            _make_sf(5000, 5000, hour=0),
            _make_sf(3000, 3000, hour=1),
        ]
        analyzer = AccuracyAnalyzer(records)
        assert analyzer.mae() == 0.0
        assert analyzer.rmse() == 0.0
        assert analyzer.mbe() == 0.0


class TestEmptyData:
    """Test edge cases with empty or partial data."""

    def test_empty_records(self):
        analyzer = AccuracyAnalyzer([])
        assert analyzer.mae() is None
        assert analyzer.rmse() is None
        assert analyzer.mbe() is None
        assert analyzer.max_abs_error() is None
        assert analyzer.median_abs_error() is None
        assert analyzer.sample_size == 0
        assert analyzer.coverage_pct is None

    def test_no_matched_records(self):
        """Records with missing forecast or actual should not be counted."""
        records = [
            _make_sf(None, 5000, hour=0),   # Missing forecast
            _make_sf(4900, None, hour=1),    # Missing actual
        ]
        analyzer = AccuracyAnalyzer(records)
        assert analyzer.sample_size == 0
        assert analyzer.mae() is None

    def test_coverage_calculation(self):
        """Coverage = matched / total."""
        records = [
            _make_sf(5000, 5000, hour=0),   # Matched
            _make_sf(None, 5000, hour=1),    # Unmatched
            _make_sf(4900, None, hour=2),    # Unmatched
            _make_sf(5100, 5000, hour=3),    # Matched
        ]
        analyzer = AccuracyAnalyzer(records)
        assert analyzer.sample_size == 2
        assert analyzer.total_intervals == 4
        assert analyzer.coverage_pct == 50.0

    def test_duplicate_intervals_are_counted_once(self):
        first = _make_sf(5100, 5000, hour=0)
        duplicate = _make_sf(5300, 5000, hour=0)

        analyzer = AccuracyAnalyzer([first, duplicate])

        assert analyzer.sample_size == 1
        assert analyzer.mae() == 100.0
        assert analyzer.rmse() == 100.0
        assert analyzer.mbe() == 100.0
        assert analyzer.median_abs_error() == 100.0
        assert analyzer.max_abs_error() == 100.0

    def test_missing_derived_error_is_recomputed_not_zero_filled(self):
        record = _make_sf(5100, 5000, hour=0)
        record.error_mw = None
        record.abs_error_mw = None

        analyzer = AccuracyAnalyzer([record])

        assert analyzer.sample_size == 1
        assert analyzer.mae() == 100.0
        assert analyzer.mbe() == 100.0

    def test_near_zero_actual_is_valid_without_percentage_error(self):
        analyzer = AccuracyAnalyzer([_make_sf(0.001, 0.0001, hour=0)])

        assert analyzer.sample_size == 1
        assert analyzer.mae() == 0.0
        assert analyzer.rmse() == 0.0
        assert analyzer.mbe() == 0.0


class TestBreakdowns:
    """Test daily and hourly accuracy breakdowns."""

    def test_daily_accuracy(self):
        records = [
            _make_sf(5100, 5000, hour=12, day=15),  # Jan 15: error=100
            _make_sf(5200, 5000, hour=12, day=16),  # Jan 16: error=200
        ]
        analyzer = AccuracyAnalyzer(records)
        daily = analyzer.daily_accuracy()
        assert len(daily) == 2
        assert daily[0]["date"] == "2026-01-15"
        assert daily[0]["mae_mw"] == 100.0
        assert daily[1]["date"] == "2026-01-16"
        assert daily[1]["mae_mw"] == 200.0

    def test_hourly_accuracy(self):
        records = [
            _make_sf(5100, 5000, hour=6, day=15),   # Hour 6: error=100
            _make_sf(5200, 5000, hour=6, day=16),   # Hour 6: error=200
            _make_sf(4800, 5000, hour=12, day=15),  # Hour 12: error=-200
        ]
        analyzer = AccuracyAnalyzer(records)
        hourly = analyzer.hourly_accuracy()
        assert len(hourly) == 24

        hour6 = next(h for h in hourly if h["hour"] == 6)
        assert hour6["mae_mw"] == 150.0  # mean(100, 200)
        assert hour6["sample_size"] == 2

        hour12 = next(h for h in hourly if h["hour"] == 12)
        assert hour12["mae_mw"] == 200.0
        assert hour12["sample_size"] == 1

    def test_error_distribution(self):
        records = [
            _make_sf(5100, 5000, hour=0),
            _make_sf(4800, 5000, hour=1),
            _make_sf(5300, 5000, hour=2),
            _make_sf(5000, 5000, hour=3),
        ]
        analyzer = AccuracyAnalyzer(records)
        dist = analyzer.error_distribution(num_bins=5)
        assert len(dist) == 5
        total_count = sum(b["count"] for b in dist)
        assert total_count == 4
