"""
OURE Data Ingestion Layer - Cache
=================================
A lightweight key-value cache backed by SQLite.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from oure.core.models import TLERecord

logger = logging.getLogger("oure.data.cache")

class CacheManager:
    """
    A lightweight key-value cache backed by SQLite.

    Schema
    ------
    cache_entries(key TEXT PK, value TEXT, fetched_at REAL, ttl_seconds REAL)
    tle_records(...)

    Why SQLite instead of Redis?
    → Zero external dependencies. A CLI tool should work offline after
      the first fetch. SQLite is fast enough for <10,000 satellite records.
    """

    DEFAULT_DB_PATH = Path.home() / ".oure" / "cache.db"

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
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

    def get(self, key: str) -> str | None:
        """Return cached value if it exists and hasn't expired."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value, fetched_at, ttl_seconds FROM cache_entries WHERE key=?",
                (key,)
            ).fetchone()
        if row is None:
            return None
        value, fetched_at, ttl = row
        age = datetime.now(UTC).timestamp() - fetched_at
        if age > ttl:
            logger.debug(f"Cache expired for key={key} (age={age:.0f}s)")
            return None
        return str(value)

    def set(self, key: str, value: str, ttl_seconds: float = 3600.0) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache_entries (key, value, fetched_at, ttl_seconds)
                VALUES (?, ?, ?, ?)
            """, (key, value, datetime.now(UTC).timestamp(), ttl_seconds))

    def cache_tle(self, record: TLERecord) -> None:
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

    def get_tle(self, sat_id: str, max_age_hours: float = 48.0) -> TLERecord | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tle_records WHERE sat_id=?", (sat_id,)
            ).fetchone()
        if row is None:
            return None
        fetched_at = datetime.fromisoformat(row[5])
        if (datetime.now(UTC) - fetched_at).total_seconds() > max_age_hours * 3600:
            return None
        return TLERecord(
            sat_id=row[0], name=row[1], line1=row[2], line2=row[3],
            epoch=datetime.fromisoformat(row[4]),
            fetched_at=fetched_at,
            inclination_deg=row[6], raan_deg=row[7], eccentricity=row[8],
            arg_perigee_deg=row[9], mean_anomaly_deg=row[10],
            mean_motion_rev_per_day=row[11], bstar=row[12]
        )
