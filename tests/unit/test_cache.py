import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from oure.core.models import TLERecord
from oure.data.cache import CacheManager


def test_cache_manager_init(db_path: Path, cache_manager: CacheManager):
    assert db_path.exists()


def test_cache_set_get(cache_manager: CacheManager):
    cache_manager.set("key1", "value1", ttl_seconds=10)
    assert cache_manager.get("key1") == "value1"


def test_cache_expiration(cache_manager: CacheManager):
    cache_manager.set("key2", "value2", ttl_seconds=0.1)
    time.sleep(0.2)
    assert cache_manager.get("key2") is None


def test_cache_tle(cache_manager: CacheManager):
    tle = TLERecord(
        sat_id="12345",
        name="TESTSAT",
        line1="1 12345U 98067A   23284.14444444  .00016715  00000-0  30046-3 0  9997",
        line2="2 12345  51.6416 122.9930 0004901 329.8058 116.7325 15.50379301420131",
        epoch=datetime.now(UTC),
    )
    cache_manager.cache_tle(tle)
    retrieved_tle = cache_manager.get_tle("12345")
    assert retrieved_tle is not None
    assert retrieved_tle.sat_id == "12345"


def test_cache_tle_expiration(cache_manager: CacheManager):
    tle = TLERecord(
        sat_id="54321",
        name="TESTSAT-EXPIRING",
        line1="1 54321U 98067A   23284.14444444  .00016715  00000-0  30046-3 0  9997",
        line2="2 54321  51.6416 122.9930 0004901 329.8058 116.7325 15.50379301420131",
        epoch=datetime.now(UTC),
        fetched_at=datetime.now(UTC) - timedelta(hours=1),
    )
    cache_manager.cache_tle(tle)
    assert cache_manager.get_tle("54321", max_age_hours=0.5) is None
    assert cache_manager.get_tle("54321", max_age_hours=2.0) is not None
