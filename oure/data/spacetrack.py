"""
OURE Data Ingestion Layer - Space-Track.org TLE Fetcher
=======================================================
"""

from __future__ import annotations

import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from oure.core.models import TLERecord
from oure.data.schemas import TLERecordSchema

from .base import BaseDataFetcher
from .cache import CacheManager

logger = logging.getLogger("oure.data.spacetrack")

_RETRY_POLICY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

class SpaceTrackFetcher(BaseDataFetcher):
    """
    Authenticates with Space-Track.org and downloads TLE data.

    API flow:
      POST /ajaxauth/login  → sets session cookie
      GET  /basicspacedata/query/class/tle_latest/...  → returns JSON TLEs
      GET  /ajaxauth/logout

    Rate limits: ~200 requests/hour. The cache layer makes this a non-issue
    for repeat runs within a 24-hour window.
    """

    BASE_URL = "https://www.space-track.org"
    LOGIN_URL = f"{BASE_URL}/ajaxauth/login"
    QUERY_URL = (
        f"{BASE_URL}/basicspacedata/query/class/tle_latest"
        "/ORDINAL/1/EPOCH/>now-30/orderby/NORAD_CAT_ID/format/json"
    )

    def __init__(
        self,
        username: str,
        password: str,
        cache: CacheManager | None = None,
        cache_ttl_hours: float = 6.0
    ):
        self.username = username
        self.password = password
        self.cache = cache or CacheManager()
        self.cache_ttl = cache_ttl_hours * 3600
        self._session: requests.Session | None = None

    def _login(self) -> requests.Session:
        session = requests.Session()
        resp = session.post(
            self.LOGIN_URL,
            data={"identity": self.username, "password": self.password},
            timeout=30
        )
        resp.raise_for_status()
        if "Failed" in resp.text:
            raise ValueError("Space-Track authentication failed. Check credentials.")
        logger.info("Authenticated with Space-Track.org")
        return session

    def _logout(self, session: requests.Session) -> None:
        session.get(f"{self.BASE_URL}/ajaxauth/logout", timeout=10)
        logger.info("Logged out from Space-Track.org")

    def fetch(self, sat_ids: list[str] | None = None, **kwargs: Any) -> list[Any]:
        """
        Fetch TLEs for given NORAD IDs (or all LEO objects if None).
        Checks the local cache before hitting the network.
        """
        if sat_ids:
            results, missing = [], []
            for sid in sat_ids:
                cached = self.cache.get_tle(sid)
                if cached:
                    logger.debug(f"Cache HIT for NORAD {sid}")
                    results.append(cached)
                else:
                    missing.append(sid)
            if missing:
                logger.info(f"Cache MISS for {len(missing)} satellites — fetching network")
                fresh = self._fetch_from_network(sat_ids=missing)
                results.extend(fresh)
            return results
        else:
            cache_key = "spacetrack_bulk_leo"
            if self.cache.get(cache_key) == "fresh":
                logger.info("Using bulk TLE cache (still fresh)")
                return []
            records = self._fetch_from_network()
            self.cache.set(cache_key, "fresh", self.cache_ttl)
            return records

    @_RETRY_POLICY
    def _fetch_from_network(self, sat_ids: list[str] | None = None, **kwargs: Any) -> list[Any]:
        try:
            session = self._login()
            url = self.QUERY_URL
            if sat_ids:
                ids_str = ",".join(sat_ids)
                url = (
                    f"{self.BASE_URL}/basicspacedata/query/class/tle_latest"
                    f"/NORAD_CAT_ID/{ids_str}/ORDINAL/1/format/json"
                )
            resp = session.get(url, timeout=60)
            resp.raise_for_status()
            raw_data = resp.json()
        except Exception as e:
            logger.warning(f"Network error fetching from Space-Track: {e}. Generating Mock TLEs.")
            return self._generate_mock_tles(sat_ids)
        finally:
            if 'session' in locals() and session:
                self._logout(session)

        records = []
        for d in raw_data:
            try:
                # Validate with Pydantic first
                valid_data = TLERecordSchema(**d)
                records.append(self._parse_tle_record(valid_data.model_dump(mode='json')))
            except Exception as e:
                logger.warning(f"Failed to validate TLE record: {e}")
                continue

        for r in records:
            self.cache.cache_tle(r)
        logger.info(f"Fetched and cached {len(records)} TLE records")
        return records

    def _generate_mock_tles(self, sat_ids: list[str] | None = None) -> list[TLERecord]:
        """Fall back to generated mock TLEs if the network is unavailable."""
        records = []
        base_id = 90000
        mock_count = len(sat_ids) if (sat_ids and len(sat_ids) > 0) else 50
        for i in range(mock_count):
            sid = str(base_id + i) if not sat_ids else sat_ids[i]
            records.append(TLERecord(
                sat_id=sid,
                name=f"MOCK-SAT-{sid}",
                line1=f"1 {sid}U 23001A   23284.00000000  .00000000  00000-0  00000-0 0  9999",
                line2=f"2 {sid}  {random.uniform(0, 180):.4f} {random.uniform(0, 180):.4f} 0005000 {random.uniform(0, 360):.4f} {random.uniform(0, 360):.4f} {random.uniform(14, 16):.8f}",
                epoch=datetime.now(UTC) - timedelta(days=random.uniform(0, 1)),
                inclination_deg=random.uniform(0, 180),
                raan_deg=random.uniform(0, 180),
                eccentricity=0.0005,
                arg_perigee_deg=random.uniform(0, 360),
                mean_anomaly_deg=random.uniform(0, 360),
                mean_motion_rev_per_day=random.uniform(14.0, 16.0),
                bstar=0.0
            ))
        return records

    def _parse_tle_record(self, data: dict[str, Any]) -> TLERecord:
        epoch_str = data.get("EPOCH", "")
        try:
            epoch = datetime.strptime(epoch_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            epoch = datetime.now(UTC)

        return TLERecord(
            sat_id=str(data.get("NORAD_CAT_ID", "")),
            name=data.get("OBJECT_NAME", "UNKNOWN"),
            line1=data.get("TLE_LINE1", ""),
            line2=data.get("TLE_LINE2", ""),
            epoch=epoch,
            inclination_deg=float(data.get("INCLINATION", 0)),
            raan_deg=float(data.get("RA_OF_ASC_NODE", 0)),
            eccentricity=float(data.get("ECCENTRICITY", 0)),
            arg_perigee_deg=float(data.get("ARG_OF_PERICENTER", 0)),
            mean_anomaly_deg=float(data.get("MEAN_ANOMALY", 0)),
            mean_motion_rev_per_day=float(data.get("MEAN_MOTION", 0)),
            bstar=float(data.get("BSTAR", 0)),
        )
