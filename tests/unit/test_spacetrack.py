from unittest.mock import MagicMock, patch

from oure.data.spacetrack import SpaceTrackFetcher


@patch('requests.Session')
def test_spacetrack_fetcher_login_success(mock_session, cache_manager):
    mock_post = MagicMock()
    mock_post.text = "successful"
    mock_session_instance = mock_session.return_value
    mock_session_instance.post.return_value = mock_post

    fetcher = SpaceTrackFetcher(username="test", password="password", cache=cache_manager)
    session = fetcher._login()

    mock_session_instance.post.assert_called_once_with(
        fetcher.LOGIN_URL,
        data={"identity": "test", "password": "password"},
        timeout=30
    )
    assert session is not None

@patch('requests.Session')
def test_spacetrack_fetcher_fetch_from_network(mock_session, cache_manager):
    mock_post = MagicMock()
    mock_post.text = "successful"
    mock_get = MagicMock()
    mock_get.json.return_value = [
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
    mock_session_instance = mock_session.return_value
    mock_session_instance.post.return_value = mock_post
    mock_session_instance.get.return_value = mock_get

    fetcher = SpaceTrackFetcher(username="test", password="password", cache=cache_manager)
    records = fetcher._fetch_from_network(sat_ids=["25544"])

    assert len(records) == 1
    assert records[0].sat_id == "25544"
    assert mock_session_instance.get.call_count == 2

@patch('requests.Session')
def test_spacetrack_fetcher_cache_logic(mock_session, cache_manager):
    # This test will check the fetch method's caching logic
    fetcher = SpaceTrackFetcher(username="test", password="password", cache=cache_manager)

    # 1. First call (network fetch)
    mock_post = MagicMock()
    mock_post.text = "successful"
    mock_get = MagicMock()
    mock_get.json.return_value = [
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
    mock_session_instance = mock_session.return_value
    mock_session_instance.post.return_value = mock_post
    mock_session_instance.get.return_value = mock_get

    fetcher.fetch(sat_ids=["12345"])
    assert mock_session_instance.get.call_count == 2

    # 2. Second call (cache hit)
    mock_session_instance.get.reset_mock()
    fetcher.fetch(sat_ids=["12345"])
    mock_session_instance.get.assert_not_called()
