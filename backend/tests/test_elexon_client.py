from __future__ import annotations

"""Tests for Elexon API client with mocked HTTP responses."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.clients.elexon_client import ElexonClient, ElexonClientError
from app.core.config import Settings


@pytest.fixture
def test_settings():
    return Settings(
        elexon_base_url="https://data.elexon.co.uk/bmrs/api/v1",
        elexon_timeout_seconds=5.0,
        elexon_max_retries=1,
    )


@pytest.fixture
def client(test_settings):
    return ElexonClient(test_settings)


class TestFetchActualWind:
    """Test FUELHH data fetching and normalization."""

    @pytest.mark.asyncio
    async def test_parse_valid_response(self, client, httpx_mock):
        """Should parse and normalize valid FUELHH records."""
        mock_data = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-15T12:30:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 25,
                "fuelType": "WIND",
                "generation": 5000.5,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-15T12:30:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 26,
                "fuelType": "WIND",
                "generation": 4800.0,
            },
        ]
        httpx_mock.add_response(json=mock_data)

        results = await client.fetch_actual_wind("2026-01-15", "2026-01-15")
        assert len(results) == 2
        assert results[0].generation_mw == 5000.5
        assert results[0].source_record["dataset"] == "FUELHH"
        assert results[0].settlement_period == 25
        assert results[0].start_time == datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_empty_response(self, client, httpx_mock):
        """Should handle empty API response."""
        httpx_mock.add_response(json=[])
        results = await client.fetch_actual_wind("2026-01-15", "2026-01-15")
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_invalid_records(self, client, httpx_mock):
        """Should skip records that fail validation."""
        mock_data = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-15T12:30:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 25,
                "fuelType": "WIND",
                "generation": 5000.0,
            },
            {
                "bad_field": "invalid",
            },
        ]
        httpx_mock.add_response(json=mock_data)

        results = await client.fetch_actual_wind("2026-01-15", "2026-01-15")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_null_generation(self, client, httpx_mock):
        """Should accept records with null generation."""
        mock_data = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-15T12:30:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 25,
                "fuelType": "WIND",
                "generation": None,
            },
        ]
        httpx_mock.add_response(json=mock_data)

        results = await client.fetch_actual_wind("2026-01-15", "2026-01-15")
        assert len(results) == 1
        assert results[0].generation_mw is None


class TestFetchWindForecasts:
    """Test WINDFOR data fetching and normalization."""

    @pytest.mark.asyncio
    async def test_parse_valid_response(self, client, httpx_mock):
        """Should parse and normalize valid WINDFOR records."""
        mock_data = [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-14T08:30:00Z",
                "startTime": "2026-01-15T12:00:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 25,
                "generation": 4900,
            },
        ]
        httpx_mock.add_response(json=mock_data)

        results = await client.fetch_wind_forecasts(
            "2025-12-30T00:00:00Z",
            "2026-02-01T00:00:00Z",
        )
        assert len(results) == 1
        assert results[0].generation_mw == 4900
        assert results[0].start_time == datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert results[0].publish_time == datetime(2026, 1, 14, 8, 30, 0, tzinfo=timezone.utc)
        assert results[0].source_record["dataset"] == "WINDFOR"


class TestSettlementToUTC:
    """Test settlement period to UTC conversion."""

    def test_period_1(self):
        result = ElexonClient._settlement_to_utc("2026-01-15", 1)
        assert result == datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc)

    def test_period_2(self):
        result = ElexonClient._settlement_to_utc("2026-01-15", 2)
        assert result == datetime(2026, 1, 15, 0, 30, 0, tzinfo=timezone.utc)

    def test_period_48(self):
        result = ElexonClient._settlement_to_utc("2026-01-15", 48)
        assert result == datetime(2026, 1, 15, 23, 30, 0, tzinfo=timezone.utc)

    def test_period_25(self):
        """Period 25 = 12:00."""
        result = ElexonClient._settlement_to_utc("2026-01-15", 25)
        assert result == datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


class TestRetryBehavior:
    """Test retry and error handling."""

    @pytest.mark.asyncio
    async def test_client_error_raises(self, client, httpx_mock):
        """4xx errors should raise without retry."""
        httpx_mock.add_response(status_code=400, text="Bad request")

        with pytest.raises(ElexonClientError, match="400"):
            await client.fetch_actual_wind("2026-01-15", "2026-01-15")

    @pytest.mark.asyncio
    async def test_retry_exhaustion_does_not_sleep_after_final_attempt(
        self, client, httpx_mock, monkeypatch
    ):
        """Retry backoff is applied only between attempts."""
        httpx_mock.add_response(status_code=500, text="first failure")
        httpx_mock.add_response(status_code=500, text="second failure")
        sleep = AsyncMock()
        monkeypatch.setattr(asyncio, "sleep", sleep)

        with pytest.raises(ElexonClientError, match="after 2 attempts"):
            await client.fetch_actual_wind("2026-01-15", "2026-01-15")

        sleep.assert_awaited_once_with(2)

    def test_vercel_retry_budget_can_be_configured(self):
        settings = Settings(
            elexon_timeout_seconds=20.0,
            elexon_max_retries=1,
        )
        configured_client = ElexonClient(settings)

        assert configured_client.timeout == 20.0
        assert configured_client.max_retries == 1
