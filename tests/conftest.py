from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from oure.core.models import StateVector, TLERecord
from oure.data.cache import CacheManager


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Provides a path to a temporary database file."""
    return tmp_path / "test_cache.db"

@pytest.fixture
def cache_manager(db_path: Path) -> CacheManager:
    """Provides a CacheManager instance with a temporary database."""
    return CacheManager(db_path=db_path)

@pytest.fixture
def dummy_state() -> StateVector:
    """Provides a generic dummy state vector."""
    return StateVector(
        r=np.array([7000.0, 0.0, 0.0]),
        v=np.array([0.0, 7.5, 0.0]),
        epoch=datetime.now(UTC),
        sat_id="12345"
    )

@pytest.fixture
def dummy_state_primary() -> StateVector:
    """Provides a dummy state vector for a primary satellite."""
    return StateVector(
        r=np.array([7000.0, 0.0, 0.0]),
        v=np.array([0.0, 7.5, 0.0]),
        epoch=datetime.now(UTC),
        sat_id="1"
    )

@pytest.fixture
def dummy_state_secondary() -> StateVector:
    """Provides a dummy state vector for a secondary satellite."""
    return StateVector(
        r=np.array([7001.0, 0.0, 0.0]),
        v=np.array([0.0, 7.4, 0.1]),
        epoch=datetime.now(UTC),
        sat_id="2"
    )

@pytest.fixture
def sample_tle() -> TLERecord:
    """Provides a sample TLE record for the ISS."""
    return TLERecord(
        sat_id="25544",
        name="ISS (ZARYA)",
        line1="1 25544U 98067A   23284.14444444  .00016715  00000-0  30046-3 0  9997",
        line2="2 25544  51.6416 122.9930 0004901 329.8058 116.7325 15.50379301420131",
        epoch=datetime(2023, 10, 11, 3, 27, 59, tzinfo=UTC),
        inclination_deg=51.6416,
        raan_deg=122.9930,
        eccentricity=0.0004901,
        arg_perigee_deg=329.8058,
        mean_anomaly_deg=116.7325,
        mean_motion_rev_per_day=15.50379301,
        bstar=0.00016715
    )
