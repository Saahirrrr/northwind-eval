from __future__ import annotations

"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.services.analysis_service import get_analysis_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle handler — preload data on startup."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(
        f"Evaluation period: {settings.delivery_start_date} to "
        f"{settings.delivery_end_date}"
    )
    logger.info(
        f"Cutoff policy: D-{settings.cutoff_days_before_delivery} at "
        f"{settings.cutoff_hour_utc:02d}:{settings.cutoff_minutes_utc:02d} UTC"
    )

    # Preload data
    service = get_analysis_service()
    try:
        await service.load_data()
        logger.info(f"Data loaded successfully (mode: {service.data_mode})")
    except Exception as e:
        logger.error(f"Failed to preload data: {e}")

    yield

    logger.info("Shutting down application")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Wind generation forecast evaluation tool for UK electricity "
            "procurement. Compares Elexon WINDFOR forecasts against FUELHH "
            "actual generation for January 2026 delivery periods."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


app = create_app()
