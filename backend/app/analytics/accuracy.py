from __future__ import annotations

"""Forecast accuracy analytics module.

Computes MAE, RMSE, MBE, and other accuracy metrics from matched
forecast-actual pairs. All calculations use explicit sample sizes
and handle edge cases (empty data, zero actuals).
"""

import logging
import math
from collections import defaultdict
from typing import Optional

import numpy as np

from app.schemas.elexon import MatchedInterval, SelectedForecast

logger = logging.getLogger(__name__)


class AccuracyAnalyzer:
    """Computes forecast accuracy metrics from selected forecast records."""

    def __init__(self, selected_forecasts: list[SelectedForecast]):
        unique_records: dict[object, SelectedForecast] = {}
        for sf in selected_forecasts:
            unique_records.setdefault(sf.start_time, sf)
        self.all_records = list(unique_records.values())
        self.matched: list[MatchedInterval] = self._extract_matched()

    def _extract_matched(self) -> list[MatchedInterval]:
        """Extract fully matched intervals (both forecast and actual present)."""
        matched_by_time: dict[object, MatchedInterval] = {}
        for sf in self.all_records:
            if (
                sf.has_forecast
                and sf.has_actual
                and sf.forecast_mw is not None
                and sf.actual_mw is not None
            ):
                error_mw = sf.forecast_mw - sf.actual_mw
                interval = MatchedInterval(
                    start_time=sf.start_time,
                    settlement_date=sf.settlement_date,
                    settlement_period=sf.settlement_period,
                    forecast_mw=sf.forecast_mw,
                    actual_mw=sf.actual_mw,
                    publish_time=sf.publish_time,
                    cutoff_time=sf.cutoff_time,
                    forecast_age_hours=sf.forecast_age_hours or 0.0,
                    error_mw=error_mw,
                    abs_error_mw=abs(error_mw),
                )
                matched_by_time.setdefault(sf.start_time, interval)
        return list(matched_by_time.values())

    @property
    def sample_size(self) -> int:
        return len(self.matched)

    @property
    def total_intervals(self) -> int:
        return len(self.all_records)

    @property
    def coverage_pct(self) -> Optional[float]:
        if self.total_intervals == 0:
            return None
        return round(100.0 * self.sample_size / self.total_intervals, 2)

    def mae(self) -> Optional[float]:
        """Mean Absolute Error (MW)."""
        if not self.matched:
            return None
        errors = [m.abs_error_mw for m in self.matched]
        return round(float(np.mean(errors)), 2)

    def rmse(self) -> Optional[float]:
        """Root Mean Squared Error (MW)."""
        if not self.matched:
            return None
        squared_errors = [m.error_mw ** 2 for m in self.matched]
        return round(float(math.sqrt(np.mean(squared_errors))), 2)

    def mbe(self) -> Optional[float]:
        """Mean Bias Error (MW).

        Positive = overforecasting (forecast > actual).
        Negative = underforecasting (forecast < actual).
        """
        if not self.matched:
            return None
        errors = [m.error_mw for m in self.matched]
        return round(float(np.mean(errors)), 2)

    def max_abs_error(self) -> Optional[float]:
        """Maximum absolute error (MW)."""
        if not self.matched:
            return None
        return round(float(max(m.abs_error_mw for m in self.matched)), 2)

    def median_abs_error(self) -> Optional[float]:
        """Median absolute error (MW)."""
        if not self.matched:
            return None
        errors = sorted(m.abs_error_mw for m in self.matched)
        return round(float(np.median(errors)), 2)

    def error_distribution(
        self, num_bins: int = 20
    ) -> list[dict]:
        """Compute error distribution histogram.

        Returns list of {bin_start, bin_end, count}.
        """
        if not self.matched:
            return []

        errors = [m.error_mw for m in self.matched]
        min_err = min(errors)
        max_err = max(errors)

        if min_err == max_err:
            return [{"bin_start": min_err, "bin_end": max_err, "count": len(errors)}]

        bin_width = (max_err - min_err) / num_bins
        buckets = []
        for i in range(num_bins):
            bin_start = min_err + i * bin_width
            bin_end = min_err + (i + 1) * bin_width
            count = sum(
                1 for e in errors
                if (bin_start <= e < bin_end) or (i == num_bins - 1 and e == bin_end)
            )
            buckets.append({
                "bin_start": round(bin_start, 2),
                "bin_end": round(bin_end, 2),
                "count": count,
            })

        return buckets

    def daily_accuracy(self) -> list[dict]:
        """Compute accuracy metrics grouped by settlement date."""
        by_date: dict[str, list[MatchedInterval]] = defaultdict(list)
        for m in self.matched:
            by_date[m.settlement_date].append(m)

        results = []
        for d in sorted(by_date.keys()):
            records = by_date[d]
            errors = [r.error_mw for r in records]
            abs_errors = [r.abs_error_mw for r in records]
            results.append({
                "date": d,
                "mae_mw": round(float(np.mean(abs_errors)), 2),
                "mbe_mw": round(float(np.mean(errors)), 2),
                "rmse_mw": round(float(math.sqrt(np.mean([e**2 for e in errors]))), 2),
                "sample_size": len(records),
            })

        return results

    def hourly_accuracy(self) -> list[dict]:
        """Compute accuracy metrics grouped by hour of day."""
        by_hour: dict[int, list[MatchedInterval]] = defaultdict(list)
        for m in self.matched:
            by_hour[m.start_time.hour].append(m)

        results = []
        for h in range(24):
            records = by_hour.get(h, [])
            if not records:
                results.append({
                    "hour": h,
                    "mae_mw": None,
                    "mbe_mw": None,
                    "sample_size": 0,
                })
                continue

            errors = [r.error_mw for r in records]
            abs_errors = [r.abs_error_mw for r in records]
            results.append({
                "hour": h,
                "mae_mw": round(float(np.mean(abs_errors)), 2),
                "mbe_mw": round(float(np.mean(errors)), 2),
                "sample_size": len(records),
            })

        return results

    def compute_all(self) -> dict:
        """Compute all accuracy metrics and breakdowns."""
        return {
            "metrics": {
                "mae_mw": self.mae(),
                "rmse_mw": self.rmse(),
                "mbe_mw": self.mbe(),
                "max_abs_error_mw": self.max_abs_error(),
                "median_abs_error_mw": self.median_abs_error(),
                "sample_size": self.sample_size,
                "total_intervals": self.total_intervals,
                "coverage_pct": self.coverage_pct,
                "unit": "MW",
                "bias_convention": (
                    "Positive = overforecast, Negative = underforecast"
                ),
            },
            "daily_accuracy": self.daily_accuracy(),
            "hourly_accuracy": self.hourly_accuracy(),
            "error_distribution": self.error_distribution(),
        }
