import asyncio
from unittest.mock import AsyncMock

import pytest

from app.clients.elexon_client import ElexonClientError
from app.core.config import Settings
from app.services.analysis_service import AnalysisService


@pytest.mark.asyncio
async def test_live_fetch_failure_does_not_fall_back_to_fixtures(monkeypatch):
    settings = Settings(use_fixtures=False, cache_ttl_seconds=0)
    service = AnalysisService(settings)
    service.client.fetch_actual_wind = AsyncMock(
        side_effect=ElexonClientError("Elexon unavailable")
    )
    load_fixtures = AsyncMock(side_effect=AssertionError("fixtures must not load"))
    monkeypatch.setattr(service, "_load_fixtures", load_fixtures)

    await service.load_data()

    assert service.data_mode == "error"
    assert service.fetch_errors == ["Elexon unavailable"]
    assert service._actuals == []
    assert service._forecasts == []
    load_fixtures.assert_not_awaited()


@pytest.mark.asyncio
async def test_live_datasets_are_fetched_concurrently():
    settings = Settings(use_fixtures=False, cache_ttl_seconds=300)
    service = AnalysisService(settings)
    actual_started = asyncio.Event()
    forecast_started = asyncio.Event()
    release = asyncio.Event()
    actual_fetch = AsyncMock()
    forecast_fetch = AsyncMock()

    async def fetch_actuals(*args):
        actual_started.set()
        await release.wait()
        return []

    async def fetch_forecasts(*args):
        forecast_started.set()
        await release.wait()
        return []

    actual_fetch.side_effect = fetch_actuals
    forecast_fetch.side_effect = fetch_forecasts
    service.client.fetch_actual_wind = actual_fetch
    service.client.fetch_wind_forecasts = forecast_fetch

    task = asyncio.create_task(service.load_data())
    await asyncio.wait_for(
        asyncio.gather(actual_started.wait(), forecast_started.wait()),
        timeout=1,
    )
    release.set()
    await task

    assert actual_fetch.await_count == 1
    assert forecast_fetch.await_count == 1
    assert service.data_mode == "live"


@pytest.mark.asyncio
async def test_concurrent_initialization_fetches_once():
    settings = Settings(use_fixtures=False, cache_ttl_seconds=300)
    service = AnalysisService(settings)
    first_fetch_started = asyncio.Event()
    release = asyncio.Event()
    second_acquire_attempted = asyncio.Event()
    actual_fetch = AsyncMock()
    forecast_fetch = AsyncMock()

    async def fetch(*args):
        first_fetch_started.set()
        await release.wait()
        return []

    actual_fetch.side_effect = fetch
    forecast_fetch.side_effect = fetch
    service.client.fetch_actual_wind = actual_fetch
    service.client.fetch_wind_forecasts = forecast_fetch

    class TrackingLock:
        def __init__(self):
            self._lock = asyncio.Lock()
            self._acquire_count = 0

        async def __aenter__(self):
            self._acquire_count += 1
            if self._acquire_count == 2:
                second_acquire_attempted.set()
            await self._lock.acquire()
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            self._lock.release()

    service._load_lock = TrackingLock()
    first = asyncio.create_task(service.load_data())
    await asyncio.wait_for(first_fetch_started.wait(), timeout=1)
    second = asyncio.create_task(service.load_data())
    await asyncio.wait_for(second_acquire_attempted.wait(), timeout=1)
    release.set()
    await asyncio.gather(first, second)

    assert actual_fetch.await_count == 1
    assert forecast_fetch.await_count == 1


@pytest.mark.asyncio
async def test_one_live_fetch_failure_keeps_analysis_in_explicit_error_state():
    settings = Settings(use_fixtures=False, cache_ttl_seconds=0)
    service = AnalysisService(settings)
    service.client.fetch_actual_wind = AsyncMock(
        side_effect=ElexonClientError("FUELHH unavailable")
    )
    service.client.fetch_wind_forecasts = AsyncMock(return_value=[])
    service._load_fixtures = AsyncMock(side_effect=AssertionError("fixtures must not load"))

    await service.load_data()

    assert service.data_mode == "error"
    assert service.fetch_errors == ["FUELHH unavailable"]
    assert service._actuals == []
    assert service._forecasts == []
    service._load_fixtures.assert_not_awaited()


@pytest.mark.asyncio
async def test_cache_reuse_and_forced_reload():
    settings = Settings(use_fixtures=False, cache_ttl_seconds=300)
    service = AnalysisService(settings)
    service.client.fetch_actual_wind = AsyncMock(return_value=[])
    service.client.fetch_wind_forecasts = AsyncMock(return_value=[])

    await service.load_data()
    await service.load_data()
    assert service.client.fetch_actual_wind.await_count == 1
    assert service.client.fetch_wind_forecasts.await_count == 1

    await service.load_data(force=True)
    assert service.client.fetch_actual_wind.await_count == 2
    assert service.client.fetch_wind_forecasts.await_count == 2
