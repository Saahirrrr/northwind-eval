from __future__ import annotations

"""Tests for API routes."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    """Create test app with use_fixtures=True (skip external network calls)."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.api.routes import router
    from app.services.analysis_service import get_analysis_service

    # Configure service to use local fixtures for deterministic fast testing
    service = get_analysis_service()
    service.settings.use_fixtures = True

    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    test_app.include_router(router)
    return test_app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data


class TestMetadataEndpoint:
    @pytest.mark.asyncio
    async def test_metadata(self, client):
        response = await client.get("/api/metadata")
        assert response.status_code == 200
        data = response.json()
        assert data["app_name"] == "Gridbricks Wind Intelligence"
        assert len(data["data_sources"]) == 2
        assert data["units"]["generation"] == "MW (megawatts, average over 30-minute settlement period)"
        assert "cutoff_policy" in data
        rationale = data["cutoff_policy"]["rationale"]
        assert "configurable project evaluation policy" in rationale
        assert "EPEX SPOT" not in rationale
        assert "Nord Pool" not in rationale
        assert "procurement analysts finalise" not in rationale


class TestOverviewEndpoint:
    @pytest.mark.asyncio
    async def test_overview(self, client):
        response = await client.get("/api/analysis/overview")
        assert response.status_code == 200
        data = response.json()
        assert "kpis" in data
        assert "coverage" in data
        assert "cutoff_policy" in data
        assert "evaluation_period_start" in data


class TestAccuracyEndpoint:
    @pytest.mark.asyncio
    async def test_accuracy(self, client):
        response = await client.get("/api/analysis/accuracy")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "daily_accuracy" in data
        assert "hourly_accuracy" in data
        assert "error_distribution" in data
        metrics = data["metrics"]
        assert {
            "mae_mw",
            "rmse_mw",
            "mbe_mw",
            "median_abs_error_mw",
            "max_abs_error_mw",
            "sample_size",
            "total_intervals",
            "coverage_pct",
        } <= metrics.keys()
        assert metrics["sample_size"] <= metrics["total_intervals"]


class TestSeriesEndpoint:
    @pytest.mark.asyncio
    async def test_series_with_date_filter(self, client):
        response = await client.get(
            "/api/analysis/series",
            params={"date_from": "2026-01-15", "date_to": "2026-01-15"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "series" in data
        assert "unit" in data
        assert data["unit"] == "MW"

    @pytest.mark.asyncio
    async def test_series_invalid_date_format(self, client):
        response = await client.get(
            "/api/analysis/series",
            params={"date_from": "invalid"},
        )
        assert response.status_code == 422  # Validation error


class TestVintagesEndpoint:
    @pytest.mark.asyncio
    async def test_vintages_pagination(self, client):
        response = await client.get(
            "/api/analysis/vintages",
            params={"page": 1, "page_size": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert "total_records" in data
        assert "cutoff_policy" in data
        assert "vintages" in data["records"][0]
        assert "selection_reason" in data["records"][0]

    @pytest.mark.asyncio
    async def test_vintages_date_filter_is_bounded(self, client):
        response = await client.get(
            "/api/analysis/vintages",
            params={"date": "2026-01-15", "page": 1, "page_size": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 48
        assert len(data["records"]) == 2
        assert all(record["settlement_date"] == "2026-01-15" for record in data["records"])


class TestProvenanceEndpoint:
    @pytest.mark.asyncio
    async def test_provenance_is_paginated_and_traceable(self, client):
        response = await client.get(
            "/api/analysis/provenance",
            params={"date": "2026-01-15", "settlement_period": 25, "page_size": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] >= 1
        assert len(data["records"]) <= 10
        assert data["timezone"] == "UTC"
        assert {record["dataset"] for record in data["records"]} <= {"FUELHH", "WINDFOR"}
        record = data["records"][0]
        assert record["source_id"]
        assert record["delivery_interval"].endswith(("Z", "+00:00"))
        assert "transformation_explanation" in record
        assert "raw_record" in record

    @pytest.mark.asyncio
    async def test_provenance_filter_can_return_empty_page(self, client):
        response = await client.get(
            "/api/analysis/provenance",
            params={"date": "2026-01-15", "settlement_period": 48, "page": 99},
        )
        assert response.status_code == 200
        assert response.json()["records"] == []
