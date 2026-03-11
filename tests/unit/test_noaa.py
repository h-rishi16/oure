import json
from unittest.mock import MagicMock, patch

from oure.data.noaa import NOAASolarFluxFetcher


@patch('requests.get')
def test_noaa_fetcher_network_fetch(mock_get, cache_manager):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Flux": "180.0", "TimeStamp": "2024-01-15 12:00:00"}
    mock_get.return_value = mock_response

    fetcher = NOAASolarFluxFetcher(cache=cache_manager)
    results = fetcher.fetch()

    assert len(results) == 1
    assert results[0].f10_7 == 180.0
    mock_get.assert_called_once()

@patch('requests.get')
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
