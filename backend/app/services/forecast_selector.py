from __future__ import annotations

"""Forecast vintage selection engine.

Implements the core domain logic: for each delivery interval, select
the most recent forecast published before the day-ahead decision cutoff.
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from app.schemas.elexon import (
    ActualWindRecord,
    ForecastWindRecord,
    SelectedForecast,
)

logger = logging.getLogger(__name__)


def _to_utc(dt: datetime) -> datetime:
    """Normalize datetime to timezone-aware UTC with zero seconds/microsecond."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc, second=0, microsecond=0)
    return dt.astimezone(timezone.utc).replace(second=0, microsecond=0)


class ForecastSelector:
    """Selects the appropriate forecast vintage for each delivery interval.

    For each delivery interval with start_time t on delivery date D:
    1. Compute cutoff c = (D - cutoff_days_before) at cutoff_hour:cutoff_min UTC.
    2. From all WINDFOR records with the same start_time t,
       select the one with max(publish_time) where publish_time <= c.
    3. Match with actual FUELHH wind generation for the same start_time.
    4. Compute error = forecast - actual (positive = overforecast).

    January 2026 is entirely in GMT (no DST), so UK time = UTC.
    The cutoff is configurable for different market conventions.
    """

    def __init__(
        self,
        cutoff_hour_utc: int = 9,
        cutoff_minutes_utc: int = 0,
        cutoff_days_before_delivery: int = 1,
    ):
        self.cutoff_hour = cutoff_hour_utc
        self.cutoff_minutes = cutoff_minutes_utc
        self.cutoff_days_before = cutoff_days_before_delivery

    def compute_cutoff(self, delivery_date: date) -> datetime:
        """Compute the decision cutoff time for a delivery date.

        Args:
            delivery_date: The date of the delivery period.

        Returns:
            UTC datetime of the decision cutoff (timezone-aware).
        """
        cutoff_date = delivery_date - timedelta(days=self.cutoff_days_before)
        return datetime(
            cutoff_date.year,
            cutoff_date.month,
            cutoff_date.day,
            self.cutoff_hour,
            self.cutoff_minutes,
            0,
            tzinfo=timezone.utc,
        )

    def select_forecasts(
        self,
        actuals: list[ActualWindRecord],
        forecasts: list[ForecastWindRecord],
        delivery_start: str,
        delivery_end: str,
        allow_hourly_fallback: bool = True,
    ) -> list[SelectedForecast]:
        """Select the eligible forecast vintage for each delivery interval.

        Args:
            actuals: List of actual wind generation records.
            forecasts: List of wind forecast records.
            delivery_start: Start date (YYYY-MM-DD) inclusive.
            delivery_end: End date (YYYY-MM-DD) inclusive.
            allow_hourly_fallback: Whether to map hourly WINDFOR forecasts
                to the half-hourly settlement periods within that hour.

        Returns:
            List of SelectedForecast records, one per expected interval.
        """
        # Index actuals by normalized start_time
        actuals_by_time: dict[datetime, ActualWindRecord] = {}
        for a in actuals:
            key = _to_utc(a.start_time)
            if key in actuals_by_time:
                # Duplicate actual — keep the one with non-None generation,
                # or the later one
                existing = actuals_by_time[key]
                if existing.generation_mw is None and a.generation_mw is not None:
                    actuals_by_time[key] = a
            else:
                actuals_by_time[key] = a

        # Index forecasts by normalized start_time
        forecasts_by_time: dict[datetime, list[ForecastWindRecord]] = defaultdict(list)
        for f in forecasts:
            key = _to_utc(f.start_time)
            forecasts_by_time[key].append(f)

        # Generate all expected 30-min intervals in the delivery period
        d_start = date.fromisoformat(delivery_start)
        d_end = date.fromisoformat(delivery_end)
        results: list[SelectedForecast] = []

        current_date = d_start
        while current_date <= d_end:
            cutoff = self.compute_cutoff(current_date)

            for sp in range(1, 49):  # 48 half-hour periods per day
                minutes_offset = (sp - 1) * 30
                hours = minutes_offset // 60
                mins = minutes_offset % 60
                start_time = datetime(
                    current_date.year,
                    current_date.month,
                    current_date.day,
                    hours,
                    mins,
                    0,
                    tzinfo=timezone.utc,
                )

                actual_record = actuals_by_time.get(start_time)
                actual_mw = actual_record.generation_mw if actual_record else None

                # Find eligible forecasts: publish_time <= cutoff
                candidates = forecasts_by_time.get(start_time, [])
                if not candidates and allow_hourly_fallback and mins == 30:
                    # Check top of the hour for hourly published forecasts
                    hour_start = start_time.replace(minute=0)
                    candidates = forecasts_by_time.get(hour_start, [])

                eligible = [
                    f for f in candidates
                    if f.publish_time is not None and _to_utc(f.publish_time) <= cutoff
                ]

                selected = None
                if eligible:
                    # Select the one with the latest publish_time
                    selected = max(eligible, key=lambda f: _to_utc(f.publish_time))

                forecast_mw = selected.generation_mw if selected else None
                publish_time = _to_utc(selected.publish_time) if selected else cutoff

                # Compute error
                error_mw = None
                abs_error_mw = None
                if forecast_mw is not None and actual_mw is not None:
                    error_mw = forecast_mw - actual_mw
                    abs_error_mw = abs(error_mw)

                # Forecast age: hours between publish and delivery start
                forecast_age_hours = None
                if selected and selected.publish_time:
                    delta = start_time - _to_utc(selected.publish_time)
                    forecast_age_hours = delta.total_seconds() / 3600

                results.append(SelectedForecast(
                    start_time=start_time,
                    settlement_date=current_date.isoformat(),
                    settlement_period=sp,
                    forecast_mw=forecast_mw,
                    actual_mw=actual_mw,
                    publish_time=publish_time,
                    cutoff_time=cutoff,
                    forecast_age_hours=forecast_age_hours,
                    error_mw=error_mw,
                    abs_error_mw=abs_error_mw,
                    has_actual=actual_mw is not None,
                    has_forecast=forecast_mw is not None,
                ))

            current_date += timedelta(days=1)

        logger.info(
            f"Forecast selection complete: {len(results)} intervals, "
            f"{sum(1 for r in results if r.has_forecast and r.has_actual)} matched"
        )
        return results

    def get_alternative_vintages(
        self,
        forecasts: list[ForecastWindRecord],
        start_time: datetime,
        cutoff: datetime,
        max_alternatives: int = 5,
    ) -> list[dict]:
        """Get alternative forecast vintages for a specific interval.

        Returns both eligible and ineligible vintages for inspection.
        """
        target = _to_utc(start_time)
        cutoff_utc = _to_utc(cutoff)
        candidates = [
            f for f in forecasts
            if _to_utc(f.start_time) == target
        ]
        if not candidates and target.minute == 30:
            target_hour = target.replace(minute=0)
            candidates = [
                f for f in forecasts
                if _to_utc(f.start_time) == target_hour
            ]

        candidates.sort(key=lambda f: _to_utc(f.publish_time), reverse=True)

        alternatives = []
        for f in candidates[:max_alternatives]:
            alternatives.append({
                "publish_time": _to_utc(f.publish_time).isoformat(),
                "generation_mw": f.generation_mw,
                "eligible": _to_utc(f.publish_time) <= cutoff_utc,
            })

        return alternatives

    def get_vintage_details(
        self,
        forecasts: list[ForecastWindRecord],
        start_time: datetime,
        cutoff: datetime,
        max_vintages: int = 100,
    ) -> list[dict]:
        """Return deterministic, explainable vintage records for one interval."""
        target = _to_utc(start_time)
        cutoff_utc = _to_utc(cutoff)
        candidates = [
            f for f in forecasts
            if _to_utc(f.start_time) == target
        ]
        if not candidates and target.minute == 30:
            target_hour = target.replace(minute=0)
            candidates = [
                f for f in forecasts
                if _to_utc(f.start_time) == target_hour
            ]

        # A repeated publication timestamp is one vintage. Prefer a populated,
        # then numerically greatest, value so API ordering cannot affect output.
        by_publish: dict[datetime, ForecastWindRecord] = {}
        duplicate_publishes: set[datetime] = set()
        for forecast in candidates:
            publish_time = _to_utc(forecast.publish_time)
            existing = by_publish.get(publish_time)
            if existing is not None:
                duplicate_publishes.add(publish_time)
                existing_key = (
                    existing.generation_mw is not None,
                    existing.generation_mw if existing.generation_mw is not None else float("-inf"),
                )
                current_key = (
                    forecast.generation_mw is not None,
                    forecast.generation_mw if forecast.generation_mw is not None else float("-inf"),
                )
                if current_key > existing_key:
                    by_publish[publish_time] = forecast
            else:
                by_publish[publish_time] = forecast

        ordered = sorted(
            by_publish.items(),
            key=lambda item: item[0],
        )
        eligible = [
            (publish_time, forecast)
            for publish_time, forecast in ordered
            if publish_time <= cutoff_utc
        ]
        selected_publish = eligible[-1][0] if eligible else None

        details = []
        for publish_time, forecast in ordered[:max_vintages]:
            is_eligible = publish_time <= cutoff_utc
            is_selected = publish_time == selected_publish
            if is_selected:
                reason = "Selected: latest eligible vintage at or before the cutoff."
            elif not is_eligible:
                reason = "Excluded: published after the decision cutoff."
            elif publish_time in duplicate_publishes:
                reason = "Eligible but not selected: duplicate publication timestamp was canonicalized."
            else:
                reason = "Eligible but not selected: a later eligible vintage was selected."
            details.append({
                "publish_time": publish_time.isoformat(),
                "generation_mw": forecast.generation_mw,
                "eligible": is_eligible,
                "selected": is_selected,
                "selection_reason": reason,
                "duplicate_publication": publish_time in duplicate_publishes,
            })
        return details
