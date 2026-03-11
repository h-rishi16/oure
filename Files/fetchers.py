"""
OURE Data Ingestion Layer
=========================
Two responsibilities, cleanly separated:
  1. Fetch raw data from external APIs (Space-Track, NOAA)
  2. Cache results locally to avoid hammering rate-limited endpoints

The physics engine never calls these classes directly — it only sees
the core.models types. This is the "Anti-Corruption Layer" pattern.
"""

from __future__ import annotations
import sqlite3
import json
import logging
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import requests

from oure.core.models import TLERecord, SolarFluxData

logger = logging.getLogger("oure.data")


# ---------------------------------------------------------------------------
# Abstract Base: every fetcher must honour this contract
# ---------------------------------------------------------------------------

class BaseDataFetcher(ABC):
    """
    Forces all fetchers to implement the same interface.
    The CLI and higher layers only talk to this abstraction,
    making it trivial to swap in test stubs or future data sources.
    """

    @abstractmethod
    def fetch(self, **kwargs) -> list:
        """Fetch data, hitting cache first, network second."""
        ...

    @abstractmethod
    def _fetch_from_network(self, **kwargs) -> list:
        """Raw network call — no caching logic here."""
        ...


# ---------------------------------------------------------------------------
# SQLite Cache Manager  (shared by all fetchers)
# ---------------------------------------------------------------------------

class CacheManager:
    """
    A lightweight key-value cache backed by SQLite.

    Schema
    ------
    cache_entries(key TEXT PK, value TEXT, fetched_at REAL, ttl_seconds REAL)

    Why SQLite instead of Redis?
    → Zero external dependencies. A CLI tool should work offline after
      the first fetch. SQLite is fast enough for <10,000 satellite records.
    """

    DEFAULT_DB_PATH = Path.home() / ".oure" / "cache.db"

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key          TEXT    PRIMARY KEY,
                    value        TEXT    NOT NULL,
                    fetched_at   REAL    NOT NULL,
                    ttl_seconds  REAL    NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tle_records (
                    sat_id              TEXT PRIMARY KEY,
                    name                TEXT,
                    line1               TEXT NOT NULL,
                    line2               TEXT NOT NULL,
                    tle_epoch           TEXT NOT NULL,
                    fetched_at          TEXT NOT NULL,
                    inclination_deg     REAL,
                    raan_deg            REAL,
                    eccentricity        REAL,
                    arg_perigee_deg     REAL,
                    mean_anomaly_deg    REAL,
                    mean_motion         REAL,
                    bstar               REAL
                )
            """)

    def get(self, key: str) -> Optional[str]:
        """Return cached value if it exists and hasn't expired."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value, fetched_at, ttl_seconds FROM cache_entries WHERE key=?",
                (key,)
            ).fetchone()
        if row is None:
            return None
        value, fetched_at, ttl = row
        age = datetime.utcnow().timestamp() - fetched_at
        if age > ttl:
            logger.debug(f"Cache expired for key={key} (age={age:.0f}s)")
            return None
        return value

    def set(self, key: str, value: str, ttl_seconds: float = 3600.0):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache_entries (key, value, fetched_at, ttl_seconds)
                VALUES (?, ?, ?, ?)
            """, (key, value, datetime.utcnow().timestamp(), ttl_seconds))

    def cache_tle(self, record: TLERecord):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tle_records
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                record.sat_id, record.name, record.line1, record.line2,
                record.epoch.isoformat(), record.fetched_at.isoformat(),
                record.inclination_deg, record.raan_deg, record.eccentricity,
                record.arg_perigee_deg, record.mean_anomaly_deg,
                record.mean_motion_rev_per_day, record.bstar
            ))

    def get_tle(self, sat_id: str, max_age_hours: float = 24.0) -> Optional[TLERecord]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tle_records WHERE sat_id=?", (sat_id,)
            ).fetchone()
        if row is None:
            return None
        fetched_at = datetime.fromisoformat(row[5])
        if (datetime.utcnow() - fetched_at).total_seconds() > max_age_hours * 3600:
            return None
        return TLERecord(
            sat_id=row[0], name=row[1], line1=row[2], line2=row[3],
            epoch=datetime.fromisoformat(row[4]),
            fetched_at=fetched_at,
            inclination_deg=row[6], raan_deg=row[7], eccentricity=row[8],
            arg_perigee_deg=row[9], mean_anomaly_deg=row[10],
            mean_motion_rev_per_day=row[11], bstar=row[12]
        )


# ---------------------------------------------------------------------------
# Space-Track.org TLE Fetcher
# ---------------------------------------------------------------------------

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
        cache: Optional[CacheManager] = None,
        cache_ttl_hours: float = 6.0
    ):
        self.username = username
        self.password = password
        self.cache = cache or CacheManager()
        self.cache_ttl = cache_ttl_hours * 3600
        self._session: Optional[requests.Session] = None

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

    def _logout(self, session: requests.Session):
        session.get(f"{self.BASE_URL}/ajaxauth/logout", timeout=10)
        logger.info("Logged out from Space-Track.org")

    def fetch(self, sat_ids: Optional[list[str]] = None, **kwargs) -> list[TLERecord]:
        """
        Fetch TLEs for given NORAD IDs (or all LEO objects if None).
        Checks the local cache before hitting the network.
        """
        if sat_ids:
            # Check cache for each ID individually
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
            # Bulk fetch — check a sentinel key
            cache_key = "spacetrack_bulk_leo"
            if self.cache.get(cache_key) == "fresh":
                logger.info("Using bulk TLE cache (still fresh)")
                # In practice, load all from DB here
                return []
            records = self._fetch_from_network()
            self.cache.set(cache_key, "fresh", self.cache_ttl)
            return records

    def _fetch_from_network(self, sat_ids: Optional[list[str]] = None) -> list[TLERecord]:
        session = self._login()
        try:
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
        finally:
            self._logout(session)

        records = [self._parse_tle_record(d) for d in raw_data]
        for r in records:
            self.cache.cache_tle(r)
        logger.info(f"Fetched and cached {len(records)} TLE records")
        return records

    def _parse_tle_record(self, data: dict) -> TLERecord:
        epoch_str = data.get("EPOCH", "")
        try:
            epoch = datetime.strptime(epoch_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            epoch = datetime.utcnow()

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


# ---------------------------------------------------------------------------
# NOAA Solar Flux Fetcher
# ---------------------------------------------------------------------------

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

    def __init__(self, cache: Optional[CacheManager] = None):
        self.cache = cache or CacheManager()

    def fetch(self, **kwargs) -> list[SolarFluxData]:
        cache_key = "noaa_f107_current"
        cached_json = self.cache.get(cache_key)
        if cached_json:
            logger.debug("Solar flux cache HIT")
            data = json.loads(cached_json)
            return [self._parse_flux(data)]
        return self._fetch_from_network()

    def _fetch_from_network(self, **kwargs) -> list[SolarFluxData]:
        resp = requests.get(self.FLUX_URL, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        self.cache.set("noaa_f107_current", json.dumps(data), ttl_seconds=3600)
        result = self._parse_flux(data)
        logger.info(f"Solar flux F10.7={result.f10_7} fetched from NOAA")
        return [result]

    def _parse_flux(self, data: dict) -> SolarFluxData:
        # NOAA JSON format: {"Flux": "175", "TimeStamp": "2024-01-15 12:00:00"}
        return SolarFluxData(
            date=datetime.utcnow(),
            f10_7=float(data.get("Flux", 150.0)),
            f10_7_81day_avg=float(data.get("Flux", 150.0)),  # Simplified
            ap_index=15.0   # Default moderate activity
        )

    def get_current_f107(self) -> float:
        """Convenience method — returns just the scalar F10.7 value."""
        records = self.fetch()
        return records[0].f10_7 if records else 150.0  # 150 = solar mean
