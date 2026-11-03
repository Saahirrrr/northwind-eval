from __future__ import annotations

"""Tests for forecast vintage selection logic.

These tests verify the core domain logic:
- Cutoff computation
- Forecast eligibility based on publish time
- Selection of most recent eligible forecast
- Handling of duplicates, missing data, and edge cases
"""

from datetime import date, datetime, timezone

import pytest

from app.schemas.elexon import ActualWindRecord, ForecastWindRecord
from app.services.forecast_selector import ForecastSelector


@pytest.fixture
def selector():
    """Default selector: D-1 at 09:00 UTC."""
    return ForecastSelector(
        cutoff_hour_utc=9,
        cutoff_minutes_utc=0,
        cutoff_days_before_delivery=1,
    )


class TestCutoffComputation:
    """Test decision cutoff calculation."""

    def test_standard_cutoff(self, selector):
        """D-1 at 09:00 for Jan 15 delivery = Jan 14 09:00."""
        cutoff = selector.compute_cutoff(date(2026, 1, 15))
        assert cutoff == datetime(2026, 1, 14, 9, 0, 0, tzinfo=timezone.utc)

    def test_first_day_cutoff(self, selector):
        """D-1 at 09:00 for Jan 1 delivery = Dec 31 09:00."""
        cutoff = selector.compute_cutoff(date(2026, 1, 1))
        assert cutoff == datetime(2025, 12, 31, 9, 0, 0, tzinfo=timezone.utc)

    def test_custom_cutoff(self):
        """Custom cutoff: D-1 at 11:30."""
        sel = ForecastSelector(
            cutoff_hour_utc=11,
            cutoff_minutes_utc=30,
            cutoff_days_before_delivery=1,
        )
        cutoff = sel.compute_cutoff(date(2026, 1, 5))
        assert cutoff == datetime(2026, 1, 4, 11, 30, 0, tzinfo=timezone.utc)

    def test_same_day_cutoff(self):
        """D-0 cutoff (same day)."""
        sel = ForecastSelector(
            cutoff_hour_utc=6,
            cutoff_minutes_utc=0,
            cutoff_days_before_delivery=0,
        )
        cutoff = sel.compute_cutoff(date(2026, 1, 10))
        assert cutoff == datetime(2026, 1, 10, 6, 0, 0, tzinfo=timezone.utc)


class TestForecastSelection:
    """Test the core forecast vintage selection algorithm."""

    def _make_actual(self, hour: int, mw: float, day: int = 15) -> ActualWindRecord:
        return ActualWindRecord(
            start_time=datetime(2026, 1, day, hour, 0, 0),
            settlement_date=f"2026-01-{day:02d}",
            settlement_period=hour * 2 + 1,
            generation_mw=mw,
        )

    def _make_forecast(
        self, target_hour: int, mw: float, pub_hour: int,
        pub_day: int = 14, target_day: int = 15,
    ) -> ForecastWindRecord:
        return ForecastWindRecord(
            start_time=datetime(2026, 1, target_day, target_hour, 0, 0),
            publish_time=datetime(2026, 1, pub_day, pub_hour, 0, 0),
            settlement_date=f"2026-01-{target_day:02d}",
            settlement_period=target_hour * 2 + 1,
            generation_mw=mw,
        )

    def test_selects_most_recent_eligible(self, selector):
        """Should select the forecast with the latest publishTime <= cutoff."""
        actuals = [self._make_actual(12, 5000.0)]
        forecasts = [
            self._make_forecast(12, 4800.0, pub_hour=3, pub_day=14),   # 03:00 D-1
            self._make_forecast(12, 4900.0, pub_hour=8, pub_day=14),   # 08:00 D-1 ← latest eligible
            self._make_forecast(12, 5100.0, pub_hour=10, pub_day=14),  # 10:00 D-1 — after cutoff
        ]
        # Cutoff is D-1 at 09:00 = Jan 14 09:00

        results = selector.select_forecasts(
            actuals, forecasts, "2026-01-15", "2026-01-15"
        )

        # Find the result for SP 25 (hour 12)
        sp25 = [r for r in results if r.settlement_period == 25]
        assert len(sp25) == 1
        r = sp25[0]
        assert r.has_forecast is True
        assert r.has_actual is True
        assert r.forecast_mw == 4900.0  # The 08:00 forecast
        assert r.actual_mw == 5000.0
        assert r.publish_time == datetime(2026, 1, 14, 8, 0, 0, tzinfo=timezone.utc)
        assert r.error_mw == -100.0  # 4900 - 5000 = underforecast

    def test_excludes_post_cutoff_forecast(self, selector):
        """Must never select a forecast published after the cutoff."""
        actuals = [self._make_actual(6, 3000.0)]
        forecasts = [
            self._make_forecast(6, 3500.0, pub_hour=12, pub_day=14),  # After cutoff
        ]

        results = selector.select_forecasts(
            actuals, forecasts, "2026-01-15", "2026-01-15"
        )

        sp13 = [r for r in results if r.settlement_period == 13]
        assert len(sp13) == 1
        r = sp13[0]
        assert r.has_forecast is False
        assert r.forecast_mw is None

    def test_exactly_at_cutoff_is_eligible(self, selector):
        """A forecast published exactly at the cutoff time IS eligible."""
        actuals = [self._make_actual(6, 3000.0)]
        forecasts = [
            self._make_forecast(6, 3200.0, pub_hour=9, pub_day=14),  # Exactly at cutoff
        ]

        results = selector.select_forecasts(
            actuals, forecasts, "2026-01-15", "2026-01-15"
        )

        sp13 = [r for r in results if r.settlement_period == 13]
        r = sp13[0]
        assert r.has_forecast is True
        assert r.forecast_mw == 3200.0

    def test_missing_actual(self, selector):
        """Should still select forecast when actual is missing."""
        actuals = []  # No actuals
        forecasts = [
            self._make_forecast(6, 3200.0, pub_hour=8, pub_day=14),
        ]

        results = selector.select_forecasts(
            actuals, forecasts, "2026-01-15", "2026-01-15"
        )

        sp13 = [r for r in results if r.settlement_period == 13]
        r = sp13[0]
        assert r.has_forecast is True
        assert r.has_actual is False
        assert r.actual_mw is None
        assert r.error_mw is None

    def test_missing_forecast(self, selector):
        """Should handle interval with actual but no eligible forecast."""
        actuals = [self._make_actual(6, 3000.0)]
        forecasts = []  # No forecasts

        results = selector.select_forecasts(
            actuals, forecasts, "2026-01-15", "2026-01-15"
        )

        sp13 = [r for r in results if r.settlement_period == 13]
        r = sp13[0]
        assert r.has_forecast is False
        assert r.has_actual is True
        assert r.forecast_mw is None
        assert r.error_mw is None

    def test_48_intervals_per_day(self, selector):
        """Should generate exactly 48 intervals per day."""
        results = selector.select_forecasts([], [], "2026-01-15", "2026-01-15")
        assert len(results) == 48

    def test_multi_day(self, selector):
        """Should generate 48 intervals × number of days."""
        results = selector.select_forecasts([], [], "2026-01-15", "2026-01-17")
        assert len(results) == 48 * 3

    def test_error_sign_convention(self, selector):
        """Positive error = overforecast, negative = underforecast."""
        actuals = [self._make_actual(12, 5000.0)]

        # Overforecast
        forecasts_over = [self._make_forecast(12, 6000.0, pub_hour=8, pub_day=14)]
        results = selector.select_forecasts(
            actuals, forecasts_over, "2026-01-15", "2026-01-15"
        )
        sp25 = [r for r in results if r.settlement_period == 25][0]
        assert sp25.error_mw == 1000.0  # Overforecast

        # Underforecast
        forecasts_under = [self._make_forecast(12, 4000.0, pub_hour=8, pub_day=14)]
        results = selector.select_forecasts(
            actuals, forecasts_under, "2026-01-15", "2026-01-15"
        )
        sp25 = [r for r in results if r.settlement_period == 25][0]
        assert sp25.error_mw == -1000.0  # Underforecast

    def test_zero_actual_generation(self, selector):
        """Should handle zero actual generation correctly."""
        actuals = [self._make_actual(3, 0.0)]
        forecasts = [self._make_forecast(3, 200.0, pub_hour=8, pub_day=14)]

        results = selector.select_forecasts(
            actuals, forecasts, "2026-01-15", "2026-01-15"
        )

        sp7 = [r for r in results if r.settlement_period == 7][0]
        assert sp7.actual_mw == 0.0
        assert sp7.forecast_mw == 200.0
        assert sp7.error_mw == 200.0  # Overforecast of 200 MW

    def test_duplicate_actuals_keeps_non_none(self, selector):
        """When duplicates exist, prefer the one with non-None generation."""
        actuals = [
            ActualWindRecord(
                start_time=datetime(2026, 1, 15, 12, 0, 0),
                settlement_date="2026-01-15",
                settlement_period=25,
                generation_mw=None,
            ),
            ActualWindRecord(
                start_time=datetime(2026, 1, 15, 12, 0, 0),
                settlement_date="2026-01-15",
                settlement_period=25,
                generation_mw=5000.0,
            ),
        ]
        forecasts = [self._make_forecast(12, 4900.0, pub_hour=8, pub_day=14)]

        results = selector.select_forecasts(
            actuals, forecasts, "2026-01-15", "2026-01-15"
        )

        sp25 = [r for r in results if r.settlement_period == 25][0]
        assert sp25.actual_mw == 5000.0

    def test_forecast_age_calculation(self, selector):
        """Forecast age should be hours between publish and delivery start."""
        actuals = [self._make_actual(12, 5000.0)]
        # Published at Jan 14 08:00, delivery at Jan 15 12:00 = 28 hours
        forecasts = [self._make_forecast(12, 4900.0, pub_hour=8, pub_day=14)]

        results = selector.select_forecasts(
            actuals, forecasts, "2026-01-15", "2026-01-15"
        )

        sp25 = [r for r in results if r.settlement_period == 25][0]
        assert sp25.forecast_age_hours == 28.0


class TestAlternativeVintages:
    """Test vintage inspection helper."""

    def test_returns_alternatives(self, selector):
        cutoff = datetime(2026, 1, 14, 9, 0, 0)
        target = datetime(2026, 1, 15, 12, 0, 0)
        forecasts = [
            ForecastWindRecord(
                start_time=target,
                publish_time=datetime(2026, 1, 14, 3, 0, 0),
                settlement_date="2026-01-15",
                settlement_period=25,
                generation_mw=4800.0,
            ),
            ForecastWindRecord(
                start_time=target,
                publish_time=datetime(2026, 1, 14, 8, 0, 0),
                settlement_date="2026-01-15",
                settlement_period=25,
                generation_mw=4900.0,
            ),
            ForecastWindRecord(
                start_time=target,
                publish_time=datetime(2026, 1, 14, 12, 0, 0),
                settlement_date="2026-01-15",
                settlement_period=25,
                generation_mw=5100.0,
            ),
        ]

        alts = selector.get_alternative_vintages(forecasts, target, cutoff)
        assert len(alts) == 3
        # Most recent first
        assert alts[0]["eligible"] is False  # 12:00 > cutoff
        assert alts[1]["eligible"] is True   # 08:00 <= cutoff
        assert alts[2]["eligible"] is True   # 03:00 <= cutoff

    def test_details_explain_cutoff_and_select_latest_eligible(self, selector):
        cutoff = datetime(2026, 1, 14, 9, 0, tzinfo=timezone.utc)
        target = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        forecasts = [
            ForecastWindRecord(
                start_time=target,
                publish_time=datetime(2026, 1, 14, hour, 0, tzinfo=timezone.utc),
                settlement_date="2026-01-15",
                settlement_period=25,
                generation_mw=value,
            )
            for hour, value in ((3, 4800), (9, 4900), (10, 5100))
        ]

        details = selector.get_vintage_details(forecasts, target, cutoff)

        assert [item["publish_time"] for item in details] == [
            "2026-01-14T03:00:00+00:00",
            "2026-01-14T09:00:00+00:00",
            "2026-01-14T10:00:00+00:00",
        ]
        assert details[1]["selected"] is True
        assert details[1]["eligible"] is True
        assert details[2]["eligible"] is False
        assert "after the decision cutoff" in details[2]["selection_reason"]

    def test_duplicate_publication_is_deterministic(self, selector):
        cutoff = datetime(2026, 1, 14, 9, 0, tzinfo=timezone.utc)
        target = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        duplicate = [
            ForecastWindRecord(
                start_time=target,
                publish_time=datetime(2026, 1, 14, 8, 0, tzinfo=timezone.utc),
                settlement_date="2026-01-15",
                settlement_period=25,
                generation_mw=value,
            )
            for value in (4900, 4950)
        ]

        details = selector.get_vintage_details(duplicate, target, cutoff)

        assert len(details) == 1
        assert details[0]["generation_mw"] == 4950
        assert details[0]["selected"] is True
        assert details[0]["duplicate_publication"] is True
