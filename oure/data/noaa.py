"""
OURE Data Ingestion Layer - NOAA Solar Flux Fetcher
===================================================
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import requests

from oure.core.models import SolarFluxData

from .base import BaseDataFetcher
from .cache import CacheManager

logger = logging.getLogger("oure.data.noaa")

class NOAASolarFluxFetcher(BaseDataFetcher):
    """
    Downloads F10.7 solar flux data from NOAA's Space Weather Prediction Center.

    Why F10.7 matters for orbit:
      Solar activity heats and expands the upper atmosphere. Higher F10.7
      → denser air at LEO altitudes → more drag → faster orbital decay.
      This directly affects where a satellite will be in 24-72 hours.
    """

    FLUX_URL = (
        "https://services.swpc.noaa.gov/products/summary/10cm-flux.json"
    )
    FLUX_ARCHIVE_URL = (
        "https://services.swpc.noaa.gov/json/solar-geophysical-values.json"
    )

    def __init__(self, cache: CacheManager | None = None):
        self.cache = cache or CacheManager()

    def fetch(self, **kwargs: Any) -> list[Any]:
        cache_key = "noaa_f107_current"
        cached_json = self.cache.get(cache_key)
        if cached_json:
            logger.debug("Solar flux cache HIT")
            data = json.loads(cached_json)
            return [self._parse_flux(data)]
        return self._fetch_from_network()

    def _fetch_from_network(self, **kwargs: Any) -> list[Any]:
        resp = requests.get(self.FLUX_URL, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        self.cache.set("noaa_f107_current", json.dumps(data), ttl_seconds=3600)
        result = self._parse_flux(data)
        logger.info(f"Solar flux F10.7={result.f10_7} fetched from NOAA")
        return [result]

    def _parse_flux(self, data: dict[str, Any]) -> SolarFluxData:
        # NOAA JSON format: {"Flux": "175", "TimeStamp": "2024-01-15 12:00:00"}
        return SolarFluxData(
            date=datetime.now(UTC),
            f10_7=float(data.get("Flux", 150.0)),
            f10_7_81day_avg=float(data.get("Flux", 150.0)),  # Simplified
            ap_index=15.0   # Default moderate activity
        )

    def get_current_f107(self) -> float:
        """Convenience method — returns just the scalar F10.7 value."""
        records = self.fetch()
        return records[0].f10_7 if records else 150.0  # 150 = solar mean
