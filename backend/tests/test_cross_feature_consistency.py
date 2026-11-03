from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.analytics.accuracy import AccuracyAnalyzer
from app.clients.elexon_client import ElexonClient
from app.core.config import Settings
from app.schemas.elexon import ActualWindRecord, ForecastWindRecord
from app.services.analysis_service import AnalysisService


def _actual(hour: int, value: float | None) -> ActualWindRecord:
    return ActualWindRecord(
        start_time=datetime(2026, 1, 15, hour, tzinfo=timezone.utc),
        settlement_date="2026-01-15",
        settlement_period=hour * 2 + 1,
        generation_mw=value,
        source_record={
            "dataset": "FUELHH",
            "publishTime": "2026-01-15T12:30:00Z",
            "settlementDate": "2026-01-15",
            "settlementPeriod": hour * 2 + 1,
            "fuelType": "WIND",
            "generation": value,
        },
    )


def _forecast(hour: int, publish_hour: int, value: float) -> ForecastWindRecord:
    return ForecastWindRecord(
        start_time=datetime(2026, 1, 15, hour, tzinfo=timezone.utc),
        publish_time=datetime(2026, 1, 14, publish_hour, tzinfo=timezone.utc),
        settlement_date="2026-01-15",
        settlement_period=hour * 2 + 1,
        generation_mw=value,
        source_record={
            "dataset": "WINDFOR",
            "publishTime": f"2026-01-14T{publish_hour:02d}:00:00Z",
            "startTime": f"2026-01-15T{hour:02d}:00:00Z",
            "settlementDate": "2026-01-15",
            "settlementPeriod": hour * 2 + 1,
            "generation": value,
        },
    )


@pytest.mark.asyncio
async def test_accuracy_vintages_and_provenance_share_selected_observation():
    settings = Settings(use_fixtures=False, cache_ttl_seconds=300)
    service = AnalysisService(settings)
    service._actuals = [_actual(12, 5000.0), _actual(13, None)]
    service._forecasts = [
        _forecast(12, 8, 4900.0),
        _forecast(12, 10, 5100.0),
        _forecast(13, 8, 3000.0),
    ]
    service._selected = service.selector.select_forecasts(
        service._actuals, service._forecasts, "2026-01-15", "2026-01-15"
    )
    service._analyzer = AccuracyAnalyzer(service._selected)
    service._data_mode = "live"
    service._last_fetch_ts = datetime.now(timezone.utc).timestamp()

    accuracy = await service.get_analyzer()
    vintages = await service.get_vintages(date="2026-01-15", page=1, page_size=48)
    provenance = await service.get_provenance(
        date="2026-01-15", settlement_period=25, page=1, page_size=50
    )

    selected_interval = next(item for item in service._selected if item.settlement_period == 25)
    vintage_interval = next(
        item for item in vintages["records"] if item["settlement_period"] == 25
    )
    forecast_rows = [item for item in provenance["records"] if item["dataset"] == "WINDFOR"]
    selected_row = next(item for item in forecast_rows if item["selected"])

    assert accuracy.sample_size == 1
    assert vintage_interval["forecast_mw"] == 4900.0
    assert selected_row["normalized_generation_mw"] == vintage_interval["forecast_mw"]
    assert selected_row["actual_generation_mw"] == selected_interval.actual_mw
    assert selected_row["forecast_error_mw"] == -100.0
    assert selected_row["publication_time"] == datetime(2026, 1, 14, 8, tzinfo=timezone.utc)
    assert all(
        row["publication_time"] <= row["cutoff_time"]
        for row in forecast_rows
        if row["selected"]
    )


def test_settlement_mapping_is_utc():
    assert ElexonClient._settlement_to_utc("2026-01-15", 1) == datetime(
        2026, 1, 15, 0, tzinfo=timezone.utc
    )
    assert ElexonClient._settlement_to_utc("2026-01-15", 48) == datetime(
        2026, 1, 15, 23, 30, tzinfo=timezone.utc
    )
