import json
from unittest.mock import MagicMock, patch
import pytest
from oure.data.noaa import NOAASolarFluxFetcher

@patch('httpx.AsyncClient.get')
def test_noaa_fetcher_network_fetch(mock_get, cache_manager):
    # Mocking the async response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Flux": "180.0", "TimeStamp": "2024-01-15 12:00:00"}
    mock_response.raise_for_status = MagicMock()
    
    # We need to return a coroutine because the caller will await it
    async def mock_get_coro(*args, **kwargs):
        return mock_response
    
    mock_get.side_effect = mock_get_coro

    fetcher = NOAASolarFluxFetcher(cache=cache_manager)
    results = fetcher.fetch()

    assert len(results) == 1
    assert results[0].f10_7 == 180.0
    # Should call twice: once for current flux, once for archive
    assert mock_get.call_count == 2


@patch('httpx.AsyncClient.get')
def test_noaa_fetcher_cache_hit(mock_get, cache_manager):
    # First, populate the cache
    cached_data = {"Flux": "175.0", "TimeStamp": "2024-01-15 12:00:00"}
    cache_manager.set("noaa_f107_current", json.dumps(cached_data))

    fetcher = NOAASolarFluxFetcher(cache=cache_manager)
    results = fetcher.fetch()

    # Should not call the network
    mock_get.assert_not_called()
    assert len(results) == 1
    assert results[0].f10_7 == 175.0

def test_get_current_f107(cache_manager):
    cached_data = {"Flux": "190.0", "TimeStamp": "2024-01-15 12:00:00"}
    cache_manager.set("noaa_f107_current", json.dumps(cached_data))

    fetcher = NOAASolarFluxFetcher(cache=cache_manager)
    f107 = fetcher.get_current_f107()

    assert f107 == 190.0
