from unittest.mock import patch

import pytest
from click.testing import CliRunner

from oure.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()

@patch('oure.cli.main.OUREContext')
def test_fetch_no_args(mock_context, runner):
    result = runner.invoke(cli, ['fetch'])
    assert result.exit_code != 0 # Fails missing st-username/pass

def test_cache_status(runner, tmp_path):
    with patch('oure.cli.main.Path') as mock_path:
        mock_path.return_value = tmp_path / "test.db"
        result = runner.invoke(cli, ['--st-username', 'u', '--st-password', 'p', 'cache', '--status'])
        assert result.exit_code == 0

def test_cache_clear(runner, tmp_path):
    with patch('oure.cli.main.Path') as mock_path:
        mock_path.return_value = tmp_path / "test.db"
        result = runner.invoke(cli, ['--st-username', 'u', '--st-password', 'p', 'cache', '--clear'], input='y\n')
        assert result.exit_code == 0

def test_cache_clear_tles(runner, tmp_path):
    with patch('oure.cli.main.Path') as mock_path:
        mock_path.return_value = tmp_path / "test.db"
        result = runner.invoke(cli, ['--st-username', 'u', '--st-password', 'p', 'cache', '--clear-tles'])
        assert result.exit_code == 0

@patch('oure.data.spacetrack.SpaceTrackFetcher.fetch')
@patch('oure.data.noaa.NOAASolarFluxFetcher.fetch')
def test_fetch_all_leo(mock_noaa, mock_spacetrack, runner):
    mock_noaa.return_value = []
    mock_spacetrack.return_value = []
    result = runner.invoke(cli, ['--st-username', 'u', '--st-password', 'p', 'fetch', '--all-leo'])
    assert result.exit_code == 0
