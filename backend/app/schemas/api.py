from __future__ import annotations

"""Pydantic schemas for API responses."""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    timestamp: datetime


class MetadataResponse(BaseModel):
    """Application and data source metadata."""
    app_name: str
    version: str
    data_sources: list[dict]
    evaluation_period: dict
    cutoff_policy: dict
    units: dict
    last_data_fetch: Optional[datetime] = None
    data_mode: str  # "live" or "fixture"


class OverviewKPI(BaseModel):
    label: str
    value: Optional[Union[float, int, str]] = None
    unit: str = ""
    description: str = ""


class OverviewResponse(BaseModel):
    """Dashboard overview KPIs."""
    evaluation_period_start: str
    evaluation_period_end: str
    cutoff_policy: str
    data_freshness: Optional[datetime] = None
    data_mode: str
    kpis: list[OverviewKPI]
    coverage: dict
    warnings: list[str] = Field(default_factory=list)


class SeriesPoint(BaseModel):
    """A single time-series data point."""
    start_time: datetime
    settlement_date: str
    settlement_period: int
    actual_mw: Optional[float] = None
    forecast_mw: Optional[float] = None
    error_mw: Optional[float] = None
    publish_time: Optional[datetime] = None


class SeriesResponse(BaseModel):
    """Time series data for charts."""
    series: list[SeriesPoint]
    total_points: int
    matched_points: int
    unit: str = "MW"
    timezone: str = "UTC"
    data_mode: str


class AccuracyMetrics(BaseModel):
    """Forecast accuracy metrics."""
    mae_mw: Optional[float] = None
    rmse_mw: Optional[float] = None
    mbe_mw: Optional[float] = None
    max_abs_error_mw: Optional[float] = None
    median_abs_error_mw: Optional[float] = None
    sample_size: int = 0
    total_intervals: int = 0
    coverage_pct: Optional[float] = None
    unit: str = "MW"
    bias_convention: str = "Positive = overforecast, Negative = underforecast"


class ErrorDistributionBucket(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class DailyAccuracy(BaseModel):
    date: str
    mae_mw: Optional[float] = None
    mbe_mw: Optional[float] = None
    rmse_mw: Optional[float] = None
    sample_size: int = 0


class HourlyAccuracy(BaseModel):
    hour: int
    mae_mw: Optional[float] = None
    mbe_mw: Optional[float] = None
    sample_size: int = 0


class AccuracyResponse(BaseModel):
    """Full accuracy analysis response."""
    metrics: AccuracyMetrics
    daily_accuracy: list[DailyAccuracy]
    hourly_accuracy: list[HourlyAccuracy]
    error_distribution: list[ErrorDistributionBucket]
    data_mode: str
    warnings: list[str] = Field(default_factory=list)


class VintageDetail(BaseModel):
    """One published forecast vintage for a delivery interval."""
    publish_time: datetime
    generation_mw: Optional[float] = None
    eligible: bool
    selected: bool = False
    selection_reason: str
    duplicate_publication: bool = False


class VintageRecord(BaseModel):
    """A single vintage inspection record."""
    start_time: datetime
    settlement_date: str
    settlement_period: int
    actual_mw: Optional[float] = None
    forecast_mw: Optional[float] = None
    publish_time: Optional[datetime] = None
    cutoff_time: datetime
    forecast_age_hours: Optional[float] = None
    error_mw: Optional[float] = None
    has_actual: bool
    has_forecast: bool
    eligible: bool = True
    alternative_vintages: list[VintageDetail] = Field(default_factory=list)
    vintages: list[VintageDetail] = Field(default_factory=list)
    selection_reason: Optional[str] = None


class VintagesResponse(BaseModel):
    """Forecast vintage inspection response."""
    records: list[VintageRecord]
    total_records: int
    page: int = 1
    page_size: int = 48
    data_mode: str
    cutoff_policy: str


class ProvenanceRecord(BaseModel):
    source_id: str
    dataset: str
    delivery_interval: datetime
    settlement_date: str
    settlement_period: int
    publication_time: Optional[datetime] = None
    cutoff_time: datetime
    raw_generation_mw: Optional[float] = None
    normalized_generation_mw: Optional[float] = None
    actual_generation_mw: Optional[float] = None
    forecast_error_mw: Optional[float] = None
    eligible: Optional[bool] = None
    selected: Optional[bool] = None
    matching_status: str
    duplicate: bool = False
    missing: bool = False
    transformation_explanation: str
    raw_record: dict = Field(default_factory=dict)


class ProvenanceResponse(BaseModel):
    records: list[ProvenanceRecord]
    total_records: int
    page: int = 1
    page_size: int = 50
    data_mode: str
    cutoff_policy: str
    timezone: str = "UTC"


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str
    status_code: int
