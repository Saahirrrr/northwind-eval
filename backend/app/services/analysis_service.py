from __future__ import annotations

"""Analysis service — coordinates data fetching, forecast selection, and analytics.

Provides a shared analysis cache so all endpoints use consistent data.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from app.analytics.accuracy import AccuracyAnalyzer
from app.clients.elexon_client import ElexonClient, ElexonClientError
from app.core.config import Settings, get_settings
from app.schemas.elexon import (
    ActualWindRecord,
    ElexonFuelHHRecord,
    ElexonWindForRecord,
    ForecastWindRecord,
    SelectedForecast,
)
from app.services.forecast_selector import ForecastSelector

logger = logging.getLogger(__name__)


class AnalysisService:
    """Orchestrates data retrieval, forecast selection, and accuracy analysis.

    Maintains an in-memory cache with configurable TTL to avoid
    redundant API calls. All endpoints draw from the same analysis
    result to ensure metric consistency.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.client = ElexonClient(self.settings)
        self.selector = ForecastSelector(
            cutoff_hour_utc=self.settings.cutoff_hour_utc,
            cutoff_minutes_utc=self.settings.cutoff_minutes_utc,
            cutoff_days_before_delivery=self.settings.cutoff_days_before_delivery,
        )

        # Cache
        self._actuals: Optional[list[ActualWindRecord]] = None
        self._forecasts: Optional[list[ForecastWindRecord]] = None
        self._selected: Optional[list[SelectedForecast]] = None
        self._analyzer: Optional[AccuracyAnalyzer] = None
        self._last_fetch: Optional[datetime] = None
        self._last_fetch_ts: float = 0
        self._data_mode: str = "not_loaded"
        self._fetch_errors: list[str] = []
        self._load_lock = asyncio.Lock()

    def _cache_valid(self) -> bool:
        if self._selected is None:
            return False
        if self.settings.cache_ttl_seconds <= 0:
            return False
        return (time.time() - self._last_fetch_ts) < self.settings.cache_ttl_seconds

    def _load_fixtures(self) -> bool:
        """Attempt to load verified sample fixtures from disk."""
        import json
        from pathlib import Path
        fixtures_dir = Path(__file__).resolve().parent.parent / "data"
        fuelhh_path = fixtures_dir / "sample_fuelhh.json"
        windfor_path = fixtures_dir / "sample_windfor.json"

        if not fuelhh_path.exists() or not windfor_path.exists():
            return False

        try:
            with open(fuelhh_path) as f:
                fuelhh_raw = json.load(f)
            with open(windfor_path) as f:
                windfor_raw = json.load(f)

            actuals = []
            for raw in fuelhh_raw:
                try:
                    record = ElexonFuelHHRecord.model_validate(raw)
                    st = self.client._settlement_to_utc(record.settlement_date, record.settlement_period)
                    actuals.append(ActualWindRecord(
                        start_time=st,
                        settlement_date=record.settlement_date,
                        settlement_period=record.settlement_period,
                        generation_mw=record.generation,
                        source_record=record.model_dump(by_alias=True),
                    ))
                except Exception:
                    pass

            forecasts = []
            for raw in windfor_raw:
                try:
                    record = ElexonWindForRecord.model_validate(raw)
                    s_date = record.settlement_date or record.start_time.strftime("%Y-%m-%d")
                    s_period = record.settlement_period or (
                        (record.start_time.hour * 60 + record.start_time.minute) // 30 + 1
                    )
                    start_t = record.start_time if record.start_time.tzinfo else record.start_time.replace(tzinfo=timezone.utc)
                    pub_t = record.publish_time if record.publish_time.tzinfo else record.publish_time.replace(tzinfo=timezone.utc)
                    forecasts.append(ForecastWindRecord(
                        start_time=start_t,
                        publish_time=pub_t,
                        settlement_date=s_date,
                        settlement_period=s_period,
                        generation_mw=record.generation,
                        source_record=record.model_dump(by_alias=True),
                    ))
                except Exception:
                    pass

            self._actuals = actuals
            self._forecasts = forecasts
            self._data_mode = "fixture"
            self._fetch_errors.append("Operating in offline fixture mode using verified January 2026 Elexon extract.")
            logger.info(f"Loaded {len(actuals)} actuals and {len(forecasts)} forecasts from local fixtures.")
            return True
        except Exception as ex:
            logger.error(f"Failed to load fixtures: {ex}")
            return False

    async def load_data(self, force: bool = False) -> None:
        """Fetch data from Elexon and run analysis."""
        if self._cache_valid() and not force:
            return

        async with self._load_lock:
            if self._cache_valid() and not force:
                return

            self._fetch_errors = []

            if self.settings.use_fixtures:
                logger.info("Configuration requested fixture mode. Loading local fixtures...")
                if not self._load_fixtures():
                    self._actuals = []
                    self._forecasts = []
                    self._data_mode = "error"
            else:
                try:
                    logger.info("Fetching actual wind generation from Elexon FUELHH...")
                    actuals, forecasts = await asyncio.gather(
                        self.client.fetch_actual_wind(
                            self.settings.delivery_start_date,
                            self.settings.delivery_end_date,
                        ),
                        self.client.fetch_wind_forecasts(
                            self.settings.forecast_fetch_start,
                            self.settings.forecast_fetch_end,
                        ),
                    )
                    self._actuals = actuals
                    self._forecasts = forecasts
                    logger.info(f"Fetched {len(actuals)} FUELHH records")
                    logger.info(f"Fetched {len(forecasts)} forecast records")
                    self._data_mode = "live"

                except ElexonClientError as e:
                    logger.error("Live Elexon fetch failed: %s", e)
                    self._actuals = []
                    self._forecasts = []
                    self._data_mode = "error"
                    self._fetch_errors.append(str(e))

            self._selected = self.selector.select_forecasts(
                self._actuals,
                self._forecasts,
                self.settings.delivery_start_date,
                self.settings.delivery_end_date,
            )

            self._analyzer = AccuracyAnalyzer(self._selected)
            self._last_fetch = datetime.now(timezone.utc)
            self._last_fetch_ts = time.time()

            logger.info(
                f"Analysis complete: {self._analyzer.sample_size} matched intervals "
                f"out of {self._analyzer.total_intervals} total "
                f"({self._analyzer.coverage_pct}% coverage)"
            )

    @property
    def data_mode(self) -> str:
        return self._data_mode

    @property
    def last_fetch(self) -> Optional[datetime]:
        return self._last_fetch

    @property
    def fetch_errors(self) -> list[str]:
        return list(self._fetch_errors)

    async def get_selected(self) -> list[SelectedForecast]:
        await self.load_data()
        return self._selected or []

    async def get_analyzer(self) -> AccuracyAnalyzer:
        await self.load_data()
        if self._analyzer is None:
            return AccuracyAnalyzer([])
        return self._analyzer

    async def get_forecasts(self) -> list[ForecastWindRecord]:
        await self.load_data()
        return self._forecasts or []

    async def get_overview(self) -> dict:
        """Get overview KPIs."""
        await self.load_data()
        analyzer = self._analyzer or AccuracyAnalyzer([])

        cutoff_desc = (
            f"D-{self.settings.cutoff_days_before_delivery} at "
            f"{self.settings.cutoff_hour_utc:02d}:"
            f"{self.settings.cutoff_minutes_utc:02d} UTC"
        )

        kpis = [
            {
                "label": "Mean Absolute Error",
                "value": analyzer.mae(),
                "unit": "MW",
                "description": "Average absolute difference between forecast and actual wind generation",
            },
            {
                "label": "Root Mean Squared Error",
                "value": analyzer.rmse(),
                "unit": "MW",
                "description": "Square root of mean squared errors — penalises large errors more heavily",
            },
            {
                "label": "Mean Bias Error",
                "value": analyzer.mbe(),
                "unit": "MW",
                "description": "Average signed error. Positive = overforecasting, Negative = underforecasting",
            },
            {
                "label": "Max Absolute Error",
                "value": analyzer.max_abs_error(),
                "unit": "MW",
                "description": "Largest single-interval absolute forecast error",
            },
            {
                "label": "Median Absolute Error",
                "value": analyzer.median_abs_error(),
                "unit": "MW",
                "description": "Median absolute error — robust to outliers",
            },
            {
                "label": "Matched Intervals",
                "value": analyzer.sample_size,
                "unit": "",
                "description": "Number of intervals with both forecast and actual data",
            },
        ]

        warnings = list(self._fetch_errors)
        if analyzer.coverage_pct is not None and analyzer.coverage_pct < 90:
            warnings.append(
                f"Data coverage is {analyzer.coverage_pct}% — "
                "some intervals may be missing"
            )

        return {
            "evaluation_period_start": self.settings.delivery_start_date,
            "evaluation_period_end": self.settings.delivery_end_date,
            "cutoff_policy": cutoff_desc,
            "data_freshness": self._last_fetch.isoformat() if self._last_fetch else None,
            "data_mode": self._data_mode,
            "kpis": kpis,
            "coverage": {
                "matched": analyzer.sample_size,
                "total": analyzer.total_intervals,
                "percentage": analyzer.coverage_pct,
            },
            "warnings": warnings,
        }

    async def get_series(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> dict:
        """Get time series data for charts."""
        selected = await self.get_selected()

        # Apply date filter
        if date_from:
            selected = [s for s in selected if s.settlement_date >= date_from]
        if date_to:
            selected = [s for s in selected if s.settlement_date <= date_to]

        series = []
        for s in selected:
            series.append({
                "start_time": s.start_time.isoformat(),
                "settlement_date": s.settlement_date,
                "settlement_period": s.settlement_period,
                "actual_mw": s.actual_mw,
                "forecast_mw": s.forecast_mw,
                "error_mw": s.error_mw,
                "publish_time": s.publish_time.isoformat() if s.publish_time else None,
            })

        matched = sum(1 for s in selected if s.has_forecast and s.has_actual)
        return {
            "series": series,
            "total_points": len(series),
            "matched_points": matched,
            "unit": "MW",
            "timezone": "UTC",
            "data_mode": self._data_mode,
        }

    async def get_accuracy(self) -> dict:
        """Get accuracy analysis."""
        analyzer = await self.get_analyzer()
        result = analyzer.compute_all()
        result["data_mode"] = self._data_mode
        result["warnings"] = list(self._fetch_errors)
        return result

    async def get_vintages(
        self,
        date: Optional[str] = None,
        page: int = 1,
        page_size: int = 48,
    ) -> dict:
        """Get vintage inspection data."""
        selected = await self.get_selected()
        forecasts = await self.get_forecasts()

        if date:
            selected = [s for s in selected if s.settlement_date == date]

        # Pagination
        total = len(selected)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_records = selected[start_idx:end_idx]

        records = []
        for sf in page_records:
            vintages = self.selector.get_vintage_details(
                forecasts, sf.start_time, sf.cutoff_time
            )
            selected_vintage = next((v for v in vintages if v["selected"]), None)
            records.append({
                "start_time": sf.start_time.isoformat(),
                "settlement_date": sf.settlement_date,
                "settlement_period": sf.settlement_period,
                "actual_mw": sf.actual_mw,
                "forecast_mw": sf.forecast_mw,
                "publish_time": (
                    sf.publish_time.isoformat() if sf.has_forecast else None
                ),
                "cutoff_time": sf.cutoff_time.isoformat(),
                "forecast_age_hours": (
                    round(sf.forecast_age_hours, 2)
                    if sf.forecast_age_hours is not None
                    else None
                ),
                "error_mw": sf.error_mw,
                "has_actual": sf.has_actual,
                "has_forecast": sf.has_forecast,
                "eligible": sf.has_forecast,
                "alternative_vintages": vintages,
                "vintages": vintages,
                "selection_reason": (
                    selected_vintage["selection_reason"]
                    if selected_vintage
                    else "No eligible forecast was available at the decision cutoff."
                ),
            })

        cutoff_desc = (
            f"D-{self.settings.cutoff_days_before_delivery} at "
            f"{self.settings.cutoff_hour_utc:02d}:"
            f"{self.settings.cutoff_minutes_utc:02d} UTC"
        )

        return {
            "records": records,
            "total_records": total,
            "page": page,
            "page_size": page_size,
            "data_mode": self._data_mode,
            "cutoff_policy": cutoff_desc,
        }

    async def get_provenance(
        self,
        date: Optional[str] = None,
        settlement_period: Optional[int] = None,
        delivery_interval: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Return source records and the transformations applied to them."""
        await self.load_data()
        actuals = self._actuals or []
        forecasts = self._forecasts or []
        selected = self._selected or []

        def utc(dt: datetime) -> datetime:
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        def source_id(dataset: str, values: dict) -> str:
            payload = json.dumps(values, sort_keys=True, default=str, separators=(",", ":"))
            digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
            return f"{dataset}-{digest}"

        actual_by_time: dict[datetime, list[ActualWindRecord]] = {}
        for actual in actuals:
            actual_by_time.setdefault(utc(actual.start_time), []).append(actual)
        forecast_by_time: dict[datetime, list[ForecastWindRecord]] = {}
        for forecast in forecasts:
            forecast_by_time.setdefault(utc(forecast.start_time), []).append(forecast)

        intervals = [
            item for item in selected
            if (date is None or item.settlement_date == date)
            and (settlement_period is None or item.settlement_period == settlement_period)
            and (delivery_interval is None or item.start_time.isoformat() == delivery_interval)
        ]
        rows: list[dict] = []
        for item in intervals:
            target = utc(item.start_time)
            cutoff = utc(item.cutoff_time)
            actual_candidates = actual_by_time.get(target, [])
            actual_value = item.actual_mw
            actual_duplicate = len(actual_candidates) > 1
            if actual_candidates:
                actual = next(
                    (candidate for candidate in actual_candidates
                     if candidate.generation_mw is not None),
                    actual_candidates[0],
                )
                raw = actual.source_record
                rows.append({
                    "source_id": source_id("FUELHH", raw or {
                        "settlementDate": actual.settlement_date,
                        "settlementPeriod": actual.settlement_period,
                        "generation": actual.generation_mw,
                    }),
                    "dataset": "FUELHH",
                    "delivery_interval": target,
                    "settlement_date": item.settlement_date,
                    "settlement_period": item.settlement_period,
                    "publication_time": utc(raw["publishTime"]) if raw.get("publishTime") else None,
                    "cutoff_time": cutoff,
                    "raw_generation_mw": actual.generation_mw,
                    "normalized_generation_mw": actual.generation_mw,
                    "actual_generation_mw": actual_value,
                    "matching_status": "matched" if actual_value is not None else "missing_value",
                    "duplicate": actual_duplicate,
                    "transformation_explanation": (
                        "FUELHH settlementDate and settlementPeriod were converted to a UTC "
                        "30-minute interval start; generation was retained in MW."
                    ),
                    "raw_record": raw,
                })
            else:
                rows.append({
                    "source_id": f"FUELHH-missing-{target.isoformat()}",
                    "dataset": "FUELHH",
                    "delivery_interval": target,
                    "settlement_date": item.settlement_date,
                    "settlement_period": item.settlement_period,
                    "publication_time": None,
                    "cutoff_time": cutoff,
                    "actual_generation_mw": None,
                    "matching_status": "missing_record",
                    "missing": True,
                    "transformation_explanation": (
                        "No FUELHH source record matched this UTC delivery interval."
                    ),
                })

            candidates = list(forecast_by_time.get(target, []))
            if not candidates and target.minute == 30:
                candidates = list(forecast_by_time.get(target.replace(minute=0), []))
            details = self.selector.get_vintage_details(forecasts, target, cutoff, max_vintages=100)
            detail_by_publish = {d["publish_time"]: d for d in details}
            duplicate_keys = {
                utc(f.publish_time) for f in candidates
                if sum(1 for candidate in candidates if utc(candidate.publish_time) == utc(f.publish_time)) > 1
            }
            seen_forecast_ids: set[str] = set()
            for forecast in sorted(candidates, key=lambda value: utc(value.publish_time)):
                raw = forecast.source_record
                publish = utc(forecast.publish_time)
                detail = detail_by_publish.get(publish.isoformat())
                record_id = source_id("WINDFOR", raw or {
                    "startTime": forecast.start_time,
                    "publishTime": publish,
                    "generation": forecast.generation_mw,
                })
                duplicate = publish in duplicate_keys or record_id in seen_forecast_ids
                seen_forecast_ids.add(record_id)
                rows.append({
                    "source_id": record_id,
                    "dataset": "WINDFOR",
                    "delivery_interval": target,
                    "settlement_date": item.settlement_date,
                    "settlement_period": item.settlement_period,
                    "publication_time": publish,
                    "cutoff_time": cutoff,
                    "raw_generation_mw": forecast.generation_mw,
                    "normalized_generation_mw": forecast.generation_mw,
                    "actual_generation_mw": actual_value,
                    "forecast_error_mw": (
                        forecast.generation_mw - actual_value
                        if forecast.generation_mw is not None and actual_value is not None
                        else None
                    ),
                    "eligible": detail["eligible"] if detail else publish <= cutoff,
                    "selected": detail["selected"] if detail else False,
                    "matching_status": (
                        "matched" if actual_value is not None else "missing_actual"
                    ),
                    "duplicate": duplicate,
                    "transformation_explanation": (
                        "WINDFOR startTime was normalized to a UTC delivery interval; "
                        "publishTime was compared with the D-1 cutoff. "
                        "The forecast value was retained in MW."
                    ),
                    "raw_record": raw,
                })
            if not candidates:
                rows.append({
                    "source_id": f"WINDFOR-missing-{target.isoformat()}",
                    "dataset": "WINDFOR",
                    "delivery_interval": target,
                    "settlement_date": item.settlement_date,
                    "settlement_period": item.settlement_period,
                    "publication_time": None,
                    "cutoff_time": cutoff,
                    "actual_generation_mw": actual_value,
                    "matching_status": "missing_record",
                    "missing": True,
                    "transformation_explanation": (
                        "No WINDFOR source record matched this UTC delivery interval."
                    ),
                })

        rows.sort(key=lambda row: (
            row["delivery_interval"],
            row["dataset"],
            row["publication_time"] or datetime.min.replace(tzinfo=timezone.utc),
        ))
        total = len(rows)
        start = (page - 1) * page_size
        cutoff_desc = (
            f"D-{self.settings.cutoff_days_before_delivery} at "
            f"{self.settings.cutoff_hour_utc:02d}:{self.settings.cutoff_minutes_utc:02d} UTC"
        )
        return {
            "records": rows[start:start + page_size],
            "total_records": total,
            "page": page,
            "page_size": page_size,
            "data_mode": self._data_mode,
            "cutoff_policy": cutoff_desc,
            "timezone": "UTC",
        }


# Singleton service instance
_service: Optional[AnalysisService] = None


def get_analysis_service() -> AnalysisService:
    """Get or create the singleton analysis service."""
    global _service
    if _service is None:
        _service = AnalysisService()
    return _service
