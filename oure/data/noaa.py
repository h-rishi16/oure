"""
OURE Data Ingestion Layer - NOAA Solar Flux Fetcher
===================================================
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from oure.core.models import SolarFluxData

from .base import BaseDataFetcher
from .cache import CacheManager

logger = logging.getLogger("oure.data.noaa")


class NOAASolarFluxFetcher(BaseDataFetcher):
    """
    Downloads F10.7 solar flux data from NOAA's Space Weather Prediction Center.
    """

    FLUX_URL = "https://services.swpc.noaa.gov/products/summary/10cm-flux.json"
    FLUX_ARCHIVE_URL = (
        "https://services.swpc.noaa.gov/json/solar-geophysical-values.json"
    )

    def __init__(self, cache: CacheManager | None = None):
        self.cache = cache or CacheManager()

    def fetch(self, **kwargs: Any) -> list[SolarFluxData]:
        cache_key = "noaa_f107_current"
        cached_json = self.cache.get(cache_key)
        if cached_json:
            logger.debug("Solar flux cache HIT")
            data = json.loads(cached_json)
            return [self._parse_flux(data)]
        return self._fetch_from_network()

    def _fetch_from_network(self, **kwargs: Any) -> list[SolarFluxData]:
        """Synchronous wrapper for the async network call."""
        return asyncio.run(self._fetch_from_network_async())

    async def _fetch_from_network_async(self) -> list[SolarFluxData]:
        """Performs non-blocking async fetch from NOAA."""
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(self.FLUX_URL)
                resp.raise_for_status()
                data = resp.json()

                self.cache.set("noaa_f107_current", json.dumps(data), ttl_seconds=3600)
                result = self._parse_flux(data)

                # Initialize with defaults from current flux
                f10_7_81day_avg = result.f10_7
                ap_index = 15.0

                # Attempt to fetch archive data for 81-day avg and Ap
                try:
                    arch_resp = await client.get(self.FLUX_ARCHIVE_URL)
                    arch_resp.raise_for_status()
                    arch_data = arch_resp.json()
                    if arch_data and len(arch_data) > 0:
                        latest = arch_data[-1]
                        f10_7_81day_avg = float(
                            latest.get("f107_81day_avg", result.f10_7)
                        )
                        ap_index = float(latest.get("ap_index", 15.0))
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch NOAA archive data: {e}. Using defaults."
                    )

                final_result = SolarFluxData(
                    date=result.date,
                    f10_7=result.f10_7,
                    f10_7_81day_avg=f10_7_81day_avg,
                    ap_index=ap_index,
                )

                logger.info(f"Solar flux F10.7={final_result.f10_7} fetched from NOAA")
                return [final_result]

        except Exception as e:
            logger.warning(f"NOAA network fetch failed: {e}. Using default solar mean.")
            return [
                SolarFluxData(
                    date=datetime.now(UTC),
                    f10_7=150.0,
                    f10_7_81day_avg=150.0,
                    ap_index=15.0,
                )
            ]

    def _parse_flux(self, data: dict[str, Any] | list[dict[str, Any]]) -> SolarFluxData:
        # NOAA JSON format: {"Flux": "175", "TimeStamp": "2024-01-15 12:00:00"}
        # Sometimes returns a list of dictionaries.
        if isinstance(data, list):
            data_dict = data[-1] if len(data) > 0 else {}
        else:
            data_dict = data

        return SolarFluxData(
            date=datetime.now(UTC),
            f10_7=float(data_dict.get("Flux", 150.0)),
            f10_7_81day_avg=float(data_dict.get("Flux", 150.0)),
            ap_index=15.0,
        )

    def get_current_f107(self) -> float:
        """Convenience method — returns just the scalar F10.7 value."""
        records = self.fetch()
        return records[0].f10_7 if records else 150.0  # 150 = solar mean
