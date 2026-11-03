from __future__ import annotations

"""API route handlers."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.schemas.api import AccuracyResponse, ProvenanceResponse, VintagesResponse
from app.services.analysis_service import get_analysis_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metadata")
async def metadata():
    """Application and data source metadata."""
    settings = get_settings()
    service = get_analysis_service()

    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "data_sources": [
            {
                "name": "FUELHH",
                "description": "Half-Hourly Generation Outturn by Fuel Type",
                "provider": "Elexon BMRS",
                "url": "https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream",
                "filter": "fuelType=WIND",
                "unit": "MW",
            },
            {
                "name": "WINDFOR",
                "description": "Wind Generation Forecast",
                "provider": "Elexon BMRS",
                "url": "https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream",
                "unit": "MW",
            },
        ],
        "evaluation_period": {
            "start": settings.delivery_start_date,
            "end": settings.delivery_end_date,
        },
        "cutoff_policy": {
            "description": (
                f"D-{settings.cutoff_days_before_delivery} at "
                f"{settings.cutoff_hour_utc:02d}:{settings.cutoff_minutes_utc:02d} UTC"
            ),
            "days_before_delivery": settings.cutoff_days_before_delivery,
            "hour_utc": settings.cutoff_hour_utc,
            "minutes_utc": settings.cutoff_minutes_utc,
            "rationale": (
                "This is a configurable project evaluation policy used to define the "
                "information boundary for the January 2026 no-lookahead comparison. "
                "It is not an official or universal UK electricity procurement deadline "
                "and does not claim to represent every participant's information state. "
                "January 2026 is entirely in GMT, so UK time = UTC."
            ),
        },
        "units": {
            "generation": "MW (megawatts, average over 30-minute settlement period)",
            "time_resolution": "30 minutes (half-hourly settlement periods)",
            "timezone": "UTC (= UK local time in January, no DST)",
        },
        "last_data_fetch": service.last_fetch.isoformat() if service.last_fetch else None,
        "data_mode": service.data_mode,
    }


@router.get("/analysis/overview")
async def analysis_overview():
    """Dashboard overview KPIs."""
    service = get_analysis_service()
    try:
        return await service.get_overview()
    except Exception as e:
        logger.error(f"Error computing overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@router.get("/analysis/series")
async def analysis_series(
    date_from: Optional[str] = Query(
        None,
        description="Start date filter (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    date_to: Optional[str] = Query(
        None,
        description="End date filter (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
):
    """Forecast vs actual time series data."""
    service = get_analysis_service()
    try:
        return await service.get_series(date_from=date_from, date_to=date_to)
    except Exception as e:
        logger.error(f"Error computing series: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@router.get("/analysis/accuracy", response_model=AccuracyResponse)
async def analysis_accuracy():
    """Forecast accuracy analysis with metrics and breakdowns."""
    service = get_analysis_service()
    try:
        return await service.get_accuracy()
    except Exception as e:
        logger.error(f"Error computing accuracy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@router.get("/analysis/vintages", response_model=VintagesResponse)
async def analysis_vintages(
    date: Optional[str] = Query(
        None,
        description="Filter by settlement date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(48, ge=1, le=1488, description="Records per page"),
):
    """Forecast vintage inspection with alternative vintages."""
    service = get_analysis_service()
    try:
        return await service.get_vintages(date=date, page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"Error computing vintages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@router.get("/analysis/provenance", response_model=ProvenanceResponse)
async def analysis_provenance(
    date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    settlement_period: Optional[int] = Query(None, ge=1, le=48),
    delivery_interval: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Return bounded source-to-analysis provenance records."""
    service = get_analysis_service()
    try:
        return await service.get_provenance(
            date=date,
            settlement_period=settlement_period,
            delivery_interval=delivery_interval,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error(f"Error computing provenance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")
