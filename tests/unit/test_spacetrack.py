import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from oure.data.spacetrack import SpaceTrackFetcher
from oure.data.cache import CacheManager
import httpx

@pytest.fixture
def cache_manager(tmp_path):
    return CacheManager(db_path=tmp_path / "test_cache.db")

@pytest.mark.asyncio
@patch('httpx.AsyncClient')
async def test_spacetrack_fetcher_login_success(mock_client_class, cache_manager):
    mock_client = AsyncMock()
    mock_post_response = MagicMock()
    mock_post_response.text = "successful"
    mock_post_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_post_response
    
    mock_client_class.return_value.__aenter__.return_value = mock_client

    fetcher = SpaceTrackFetcher(username="test", password="password", cache=cache_manager)
    await fetcher._async_login(mock_client)

    mock_client.post.assert_called_once_with(
        fetcher.LOGIN_URL,
        data={"identity": "test", "password": "password"},
        timeout=30.0
    )

@patch('httpx.AsyncClient')
def test_spacetrack_fetcher_fetch_from_network(mock_client_class, cache_manager):
    mock_client = AsyncMock()
    
    mock_post_response = MagicMock()
    mock_post_response.text = "successful"
    mock_client.post.return_value = mock_post_response
    
    mock_get_response = MagicMock()
    mock_get_response.json.return_value = [
        {
            "NORAD_CAT_ID": "25544",
            "OBJECT_NAME": "ISS (ZARYA)",
            "TLE_LINE1": "1 25544U 98067A   23284.14444444  .00016715  00000-0  30046-3 0  9997",
            "TLE_LINE2": "2 25544  51.6416 122.9930 0004901 329.8058 116.7325 15.50379301420131",
            "EPOCH": "2023-10-11 03:27:59",
            "INCLINATION": 51.6416,
            "RA_OF_ASC_NODE": 122.9930,
            "ECCENTRICITY": 0.0004901,
            "ARG_OF_PERICENTER": 329.8058,
            "MEAN_ANOMALY": 116.7325,
            "MEAN_MOTION": 15.50379301,
            "BSTAR": 0.00016715
        }
    ]
    mock_client.get.return_value = mock_get_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    fetcher = SpaceTrackFetcher(username="test", password="password", cache=cache_manager)
    records = fetcher._fetch_from_network(sat_ids=["25544"])

    assert len(records) == 1
    assert records[0].sat_id == "25544"
    # Expect 2 calls: one for the TLE data, one for logout
    assert mock_client.get.call_count == 2

@patch('httpx.AsyncClient')
def test_spacetrack_fetcher_cache_logic(mock_client_class, cache_manager):
    fetcher = SpaceTrackFetcher(username="test", password="password", cache=cache_manager)
    
    mock_client = AsyncMock()
    mock_post_response = MagicMock()
    mock_post_response.text = "successful"
    mock_client.post.return_value = mock_post_response
    
    mock_get_response = MagicMock()
    mock_get_response.json.return_value = [
        {
            "NORAD_CAT_ID": "12345",
            "OBJECT_NAME": "DUMMY",
            "TLE_LINE1": "1",
            "TLE_LINE2": "2",
            "EPOCH": "2023-10-11 03:27:59",
            "INCLINATION": 0.0,
            "RA_OF_ASC_NODE": 0.0,
            "ECCENTRICITY": 0.0,
            "ARG_OF_PERICENTER": 0.0,
            "MEAN_ANOMALY": 0.0,
            "MEAN_MOTION": 0.0,
            "BSTAR": 0.0
        }
    ]
    mock_client.get.return_value = mock_get_response
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    # 1. First call (network fetch)
    fetcher.fetch(sat_ids=["12345"])
    assert mock_client.get.call_count == 2

    # 2. Second call (cache hit)
    mock_client.get.reset_mock()
    fetcher.fetch(sat_ids=["12345"])
    mock_client.get.assert_not_called()
