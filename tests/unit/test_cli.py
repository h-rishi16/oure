from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from oure.cli.main import cli
from oure.cli.utils import UI


@pytest.fixture
def runner():
    return CliRunner()


@patch("oure.cli.main.OUREContext")
def test_fetch_no_args(mock_context_class, runner):
    mock_ctx = MagicMock()
    mock_context_class.return_value = mock_ctx
    mock_ctx.flux_fetcher.fetch.return_value = []
    mock_ctx.tle_fetcher.fetch.return_value = []

    with (
        patch("oure.cli.cmd_fetch.UI", UI),
        patch("oure.cli.cmd_fetch.console") as mock_console,
    ):
        result = runner.invoke(
            cli, ["--st-username", "u", "--st-password", "p", "fetch"]
        )
    assert result.exit_code == 0


def test_cache_status(runner, tmp_path):
    with patch("oure.cli.main.Path") as mock_path:
        mock_path.return_value = tmp_path / "test.db"
        result = runner.invoke(
            cli, ["--st-username", "u", "--st-password", "p", "cache", "--status"]
        )
        assert result.exit_code == 0


def test_cache_clear(runner, tmp_path):
    with patch("oure.cli.main.Path") as mock_path:
        mock_path.return_value = tmp_path / "test.db"
        result = runner.invoke(
            cli,
            ["--st-username", "u", "--st-password", "p", "cache", "--clear"],
            input="y\n",
        )
        assert result.exit_code == 0


def test_cache_clear_tles(runner, tmp_path):
    with patch("oure.cli.main.Path") as mock_path:
        mock_path.return_value = tmp_path / "test.db"
        result = runner.invoke(
            cli,
            ["--st-username", "u", "--st-password", "p", "cache", "--clear-tles"],
            input="y\n",
        )
        assert result.exit_code == 0


@patch("oure.data.spacetrack.SpaceTrackFetcher.fetch")
@patch("oure.data.noaa.NOAASolarFluxFetcher.fetch")
def test_fetch_all_leo(mock_noaa, mock_spacetrack, runner):
    mock_noaa.return_value = []
    mock_spacetrack.return_value = []
    with (
        patch("oure.cli.cmd_fetch.UI", UI),
        patch("oure.cli.cmd_fetch.console") as mock_console,
    ):
        result = runner.invoke(
            cli, ["--st-username", "u", "--st-password", "p", "fetch", "--all-leo"]
        )
    assert result.exit_code == 0
