from __future__ import annotations

"""Elexon BMRS API client with retry, timeout, and validation."""

import logging
from datetime import date, datetime, timezone
from typing import Optional

import httpx

from app.core.config import Settings, get_settings
from app.schemas.elexon import (
    ActualWindRecord,
    ElexonFuelHHRecord,
    ElexonWindForRecord,
    ForecastWindRecord,
)

logger = logging.getLogger(__name__)


class ElexonClientError(Exception):
    """Raised when the Elexon API returns an error."""
    pass


class ElexonClient:
    """Async client for the Elexon Insights Solution API.

    Fetches FUELHH (actual generation by fuel type) and WINDFOR
    (wind generation forecasts) datasets via the streaming endpoints.
    No API key is required for public read-only access.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.elexon_base_url.rstrip("/")
        self.timeout = self.settings.elexon_timeout_seconds
        self.max_retries = self.settings.elexon_max_retries

    async def _request_with_retry(
        self, url: str, params: dict
    ) -> list[dict]:
        """Make a GET request with bounded exponential backoff."""
        import asyncio

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.info(
                        f"Elexon API request (attempt {attempt + 1}): "
                        f"GET {url} params={params}"
                    )
                    response = await client.get(url, params=params)

                    if response.status_code == 429:
                        # Rate limited — wait and retry
                        last_error = ElexonClientError("Elexon API rate limited (429)")
                        if attempt < self.max_retries:
                            wait = min(2 ** attempt * 2, 30)
                            logger.warning(f"Rate limited, waiting {wait}s")
                            await asyncio.sleep(wait)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    # Stream endpoints return a flat JSON array
                    if isinstance(data, list):
                        return data
                    # Paginated endpoints return {data: [...]}
                    if isinstance(data, dict) and "data" in data:
                        return data["data"]
                    # Unexpected format
                    logger.warning(f"Unexpected response format: {type(data)}")
                    return data if isinstance(data, list) else []

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.max_retries:
                    wait = min(2 ** attempt * 2, 30)
                    logger.warning(f"Timeout on attempt {attempt + 1}, waiting {wait}s")
                    await asyncio.sleep(wait)
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    last_error = e
                    if attempt < self.max_retries:
                        wait = min(2 ** attempt * 2, 30)
                        logger.warning(
                            f"Server error {e.response.status_code} on attempt "
                            f"{attempt + 1}, waiting {wait}s"
                        )
                        await asyncio.sleep(wait)
                else:
                    raise ElexonClientError(
                        f"Elexon API error {e.response.status_code}: "
                        f"{e.response.text[:500]}"
                    ) from e
            except httpx.HTTPError as e:
                last_error = e
                if attempt < self.max_retries:
                    wait = min(2 ** attempt * 2, 30)
                    logger.warning(
                        f"HTTP error on attempt {attempt + 1}: {e}, waiting {wait}s"
                    )
                    await asyncio.sleep(wait)

        raise ElexonClientError(
            f"Failed after {self.max_retries + 1} attempts: {last_error}"
        )

    async def fetch_actual_wind(
        self,
        settlement_date_from: str,
        settlement_date_to: str,
    ) -> list[ActualWindRecord]:
        """Fetch FUELHH actual wind generation records.

        Args:
            settlement_date_from: Start date (YYYY-MM-DD).
            settlement_date_to: End date (YYYY-MM-DD).

        Returns:
            List of normalized ActualWindRecord.
        """
        url = f"{self.base_url}/datasets/FUELHH/stream"
        params = {
            "settlementDateFrom": settlement_date_from,
            "settlementDateTo": settlement_date_to,
            "fuelType": "WIND",
        }

        raw_records = await self._request_with_retry(url, params)
        logger.info(f"Received {len(raw_records)} FUELHH WIND records")

        results = []
        for raw in raw_records:
            try:
                record = ElexonFuelHHRecord.model_validate(raw)
                # Convert settlement date + period to start_time
                start_time = self._settlement_to_utc(
                    record.settlement_date, record.settlement_period
                )
                results.append(ActualWindRecord(
                    start_time=start_time,
                    settlement_date=record.settlement_date,
                    settlement_period=record.settlement_period,
                    generation_mw=record.generation,
                    source_record=record.model_dump(by_alias=True),
                ))
            except Exception as e:
                logger.warning(f"Skipping invalid FUELHH record: {e} — {raw}")

        return results

    async def fetch_wind_forecasts(
        self,
        publish_from: str,
        publish_to: str,
    ) -> list[ForecastWindRecord]:
        """Fetch WINDFOR wind generation forecast records.

        Args:
            publish_from: Publish datetime from (ISO 8601).
            publish_to: Publish datetime to (ISO 8601).

        Returns:
            List of normalized ForecastWindRecord.
        """
        url = f"{self.base_url}/datasets/WINDFOR/stream"
        params = {
            "publishDateTimeFrom": publish_from,
            "publishDateTimeTo": publish_to,
        }

        raw_records = await self._request_with_retry(url, params)
        logger.info(f"Received {len(raw_records)} WINDFOR records")

        results = []
        for raw in raw_records:
            try:
                record = ElexonWindForRecord.model_validate(raw)
                s_date = record.settlement_date or record.start_time.strftime("%Y-%m-%d")
                s_period = record.settlement_period or (
                    (record.start_time.hour * 60 + record.start_time.minute) // 30 + 1
                )
                start_t = record.start_time if record.start_time.tzinfo else record.start_time.replace(tzinfo=timezone.utc)
                pub_t = record.publish_time if record.publish_time.tzinfo else record.publish_time.replace(tzinfo=timezone.utc)
                results.append(ForecastWindRecord(
                    start_time=start_t,
                    publish_time=pub_t,
                    settlement_date=s_date,
                    settlement_period=s_period,
                    generation_mw=record.generation,
                    source_record=record.model_dump(by_alias=True),
                ))
            except Exception as e:
                logger.warning(f"Skipping invalid WINDFOR record: {e} — {raw}")

        return results

    @staticmethod
    def _settlement_to_utc(settlement_date: str, settlement_period: int) -> datetime:
        """Convert settlement date + period to UTC start time.

        Settlement periods are 1-indexed, each 30 minutes.
        Period 1 starts at 00:00 UTC on the settlement date.
        (In January, UK local time = UTC — no DST offset.)
        """
        d = date.fromisoformat(settlement_date)
        minutes_offset = (settlement_period - 1) * 30
        hours = minutes_offset // 60
        mins = minutes_offset % 60
        return datetime(d.year, d.month, d.day, hours, mins, 0, tzinfo=timezone.utc)
