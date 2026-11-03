from __future__ import annotations

"""Pydantic schemas for Elexon API responses and internal domain models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# ─── Elexon raw response models ───────────────────────────────────────────────

class ElexonFuelHHRecord(BaseModel):
    """Raw FUELHH record from Elexon API."""
    dataset: str = "FUELHH"
    publish_time: datetime = Field(alias="publishTime")
    settlement_date: str = Field(alias="settlementDate")
    settlement_period: int = Field(alias="settlementPeriod")
    fuel_type: str = Field(alias="fuelType")
    generation: Optional[float] = None

    model_config = {"populate_by_name": True}


class ElexonWindForRecord(BaseModel):
    """Raw WINDFOR record from Elexon API."""
    dataset: str = "WINDFOR"
    publish_time: datetime = Field(alias="publishTime")
    start_time: datetime = Field(alias="startTime")
    settlement_date: Optional[str] = Field(default=None, alias="settlementDate")
    settlement_period: Optional[int] = Field(default=None, alias="settlementPeriod")
    generation: Optional[float] = None

    model_config = {"populate_by_name": True}


# ─── Normalized internal models ───────────────────────────────────────────────

class ActualWindRecord(BaseModel):
    """Normalized actual wind generation record."""
    start_time: datetime  # Start of the 30-min interval (UTC)
    settlement_date: str
    settlement_period: int
    generation_mw: Optional[float]  # MW
    source_record: dict = Field(default_factory=dict)


class ForecastWindRecord(BaseModel):
    """Normalized wind forecast record."""
    start_time: datetime  # Target delivery interval start (UTC)
    publish_time: datetime  # When this forecast was published (UTC)
    settlement_date: str
    settlement_period: int
    generation_mw: Optional[float]  # MW
    source_record: dict = Field(default_factory=dict)


class SelectedForecast(BaseModel):
    """A forecast selected by the vintage selection algorithm."""
    start_time: datetime
    settlement_date: str
    settlement_period: int
    forecast_mw: Optional[float]
    actual_mw: Optional[float]
    publish_time: datetime  # Selected forecast's publish time
    cutoff_time: datetime  # Decision cutoff used
    forecast_age_hours: Optional[float]  # Hours between publish and start
    error_mw: Optional[float]  # forecast - actual (positive = overforecast)
    abs_error_mw: Optional[float]
    has_actual: bool
    has_forecast: bool


class MatchedInterval(BaseModel):
    """A fully matched delivery interval with forecast and actual."""
    start_time: datetime
    settlement_date: str
    settlement_period: int
    forecast_mw: float
    actual_mw: float
    publish_time: datetime
    cutoff_time: datetime
    forecast_age_hours: float
    error_mw: float
    abs_error_mw: float
