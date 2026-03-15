import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from click.testing import CliRunner

from oure.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "analyze" in result.output
    assert "shatter" in result.output


@patch("oure.cli.main.OUREContext")
@patch("oure.cli.utils._tle_to_initial_state")
def test_cli_analyze(mock_tle_state, mock_ctx_class, runner, sample_tle):
    mock_ctx = MagicMock()
    mock_ctx_class.return_value = mock_ctx
    mock_ctx.tle_fetcher.fetch.return_value = [sample_tle]
    mock_ctx.flux_fetcher.get_current_f107.return_value = 150.0

    from oure.core.models import StateVector

    mock_tle_state.return_value = StateVector(
        r=np.array([7000, 0, 0]),
        v=np.array([0, 7.5, 0]),
        epoch=sample_tle.epoch,
        sat_id="25544",
    )

    result = runner.invoke(
        cli,
        [
            "--st-username",
            "u",
            "--st-password",
            "p",
            "analyze",
            "--primary",
            "25544",
            "--secondary",
            "43205",
        ],
    )
    assert result.exit_code == 0


@patch("oure.cli.main.OUREContext")
@patch("oure.conjunction.tca_finder.TCARefinementEngine.find_tca")
@patch("oure.cli.utils._tle_to_initial_state")
def test_cli_shatter(mock_tle_state, mock_tca, mock_ctx_class, runner, sample_tle):
    mock_ctx = MagicMock()
    mock_ctx_class.return_value = mock_ctx

    tle2 = type(sample_tle)(**{**sample_tle.__dict__, "sat_id": "43205"})
    mock_ctx.tle_fetcher.fetch.return_value = [sample_tle, tle2]
    mock_ctx.flux_fetcher.get_current_f107.return_value = 150.0

    from oure.core.models import StateVector

    mock_tle_state.return_value = StateVector(
        r=np.array([7000, 0, 0]),
        v=np.array([0, 7.5, 0]),
        epoch=sample_tle.epoch,
        sat_id="25544",
    )
    mock_tca.return_value = (sample_tle.epoch, 0.1)

    result = runner.invoke(
        cli,
        [
            "--st-username",
            "u",
            "--st-password",
            "p",
            "shatter",
            "--primary",
            "25544",
            "--secondary",
            "43205",
            "--fragments",
            "10",
        ],
    )
    assert result.exit_code == 0


@patch("oure.cli.main.OUREContext")
def test_cli_history(mock_ctx_class, runner):
    mock_ctx = MagicMock()
    mock_ctx_class.return_value = mock_ctx
    mock_ctx.cache.get_risk_history.return_value = [
        {
            "evaluation_time": "2026-03-14T00:00:00",
            "tca": "2026-03-15T00:00:00",
            "pc": 1e-4,
            "miss_distance_km": 0.5,
            "warning_level": "YELLOW",
        }
    ]

    result = runner.invoke(
        cli,
        [
            "--st-username",
            "u",
            "--st-password",
            "p",
            "history",
            "--primary",
            "25544",
            "--secondary",
            "43205",
        ],
    )
    assert result.exit_code == 0


@patch("oure.cli.main.OUREContext")
@patch("oure.risk.calculator.RiskCalculator.compute_pc")
@patch("oure.conjunction.tca_finder.TCARefinementEngine.find_tca")
@patch("oure.cli.utils._tle_to_initial_state")
def test_cli_task_sensor(
    mock_tle_state, mock_tca, mock_risk, mock_ctx_class, runner, sample_tle
):
    mock_ctx = MagicMock()
    mock_ctx_class.return_value = mock_ctx

    tle2 = type(sample_tle)(**{**sample_tle.__dict__, "sat_id": "43205"})
    mock_ctx.tle_fetcher.fetch.return_value = [sample_tle, tle2]
    mock_ctx.flux_fetcher.get_current_f107.return_value = 150.0

    from oure.core.models import StateVector

    mock_tle_state.return_value = StateVector(
        r=np.array([7000, 0, 0]),
        v=np.array([0, 7.5, 0]),
        epoch=sample_tle.epoch,
        sat_id="25544",
    )
    mock_tca.return_value = (sample_tle.epoch, 0.5)

    mock_res = MagicMock()
    mock_res.pc = 1e-4
    mock_res.warning_level = "YELLOW"
    mock_res.b_plane_sigma_x = 1.0
    mock_risk.return_value = mock_res

    result = runner.invoke(
        cli,
        [
            "--st-username",
            "u",
            "--st-password",
            "p",
            "task-sensor",
            "--primary",
            "25544",
            "--secondary",
            "43205",
        ],
    )
    assert result.exit_code == 0


@patch("oure.cli.main.OUREContext")
@patch("oure.risk.calculator.RiskCalculator.compute_pc")
@patch("oure.conjunction.tca_finder.TCARefinementEngine.find_tca")
@patch("oure.cli.utils._tle_to_initial_state")
def test_cli_avoid(
    mock_tle_state, mock_tca, mock_risk, mock_ctx_class, runner, sample_tle
):
    mock_ctx = MagicMock()
    mock_ctx_class.return_value = mock_ctx

    tle2 = type(sample_tle)(**{**sample_tle.__dict__, "sat_id": "43205"})
    mock_ctx.tle_fetcher.fetch.return_value = [sample_tle, tle2]
    mock_ctx.flux_fetcher.get_current_f107.return_value = 150.0

    from oure.core.models import StateVector

    mock_tle_state.return_value = StateVector(
        r=np.array([7000, 0, 0]),
        v=np.array([0, 7.5, 0]),
        epoch=sample_tle.epoch,
        sat_id="25544",
    )
    mock_tca.return_value = (sample_tle.epoch, 0.5)

    mock_res = MagicMock()
    mock_res.pc = 1e-4
    mock_res.warning_level = "YELLOW"
    mock_risk.return_value = mock_res

    result = runner.invoke(
        cli,
        [
            "--st-username",
            "u",
            "--st-password",
            "p",
            "avoid",
            "--primary",
            "25544",
            "--secondary",
            "43205",
            "--burn-time-before-tca",
            "12.0",
        ],
        input="n\n",
    )
    assert result.exit_code == 0


@patch("oure.cli.main.OUREContext")
@patch("oure.cli.utils._tle_to_initial_state")
def test_cli_fleet(mock_tle_state, mock_ctx_class, runner, sample_tle, tmp_path):
    mock_ctx = MagicMock()
    mock_ctx_class.return_value = mock_ctx

    tle2 = type(sample_tle)(**{**sample_tle.__dict__, "sat_id": "43205"})
    mock_ctx.tle_fetcher.fetch.return_value = [sample_tle, tle2]
    mock_ctx.flux_fetcher.get_current_f107.return_value = 150.0

    from oure.core.models import StateVector

    mock_tle_state.return_value = StateVector(
        r=np.array([7000, 0, 0]),
        v=np.array([0, 7.5, 0]),
        epoch=sample_tle.epoch,
        sat_id="25544",
    )

    p_file = tmp_path / "p.json"
    s_file = tmp_path / "s.json"
    with open(p_file, "w") as f:
        json.dump(["25544"], f)
    with open(s_file, "w") as f:
        json.dump(["43205"], f)

    result = runner.invoke(
        cli,
        [
            "--st-username",
            "u",
            "--st-password",
            "p",
            "analyze-fleet",
            "--primaries-file",
            str(p_file),
            "--secondaries-file",
            str(s_file),
        ],
    )
    assert result.exit_code == 0


@patch("oure.cli.main.OUREContext")
@patch("oure.cli.cmd_monitor.analyze")
@patch("time.sleep", return_value=None)
def test_cli_monitor(mock_sleep, mock_analyze, mock_ctx_class, runner, tmp_path):
    mock_ctx = MagicMock()
    mock_ctx_class.return_value = mock_ctx

    mock_res = MagicMock()
    mock_res.conjunction.primary_id = "25544"
    mock_res.conjunction.secondary_id = "43205"
    mock_res.conjunction.tca = datetime.now(UTC)
    mock_res.pc = 1e-4
    mock_res.conjunction.miss_distance_km = 0.5
    mock_res.warning_level = "YELLOW"
    mock_analyze.return_value = [mock_res]

    sec_file = tmp_path / "s.json"
    with open(sec_file, "w") as f:
        json.dump(["43205"], f)

    result = runner.invoke(
        cli,
        [
            "--st-username",
            "u",
            "--st-password",
            "p",
            "monitor",
            "--primary",
            "25544",
            "--secondaries-file",
            str(sec_file),
            "--interval",
            "1",
            "--max-runs",
            "1",
        ],
    )
    assert result.exit_code == 0


@patch("oure.cli.main.OUREContext")
def test_cli_assess_cdm(mock_ctx_class, runner, tmp_path):
    cdm_data = {
        "body": {
            "TCA": "2026-03-12T14:23:11Z",
            "MISS_DISTANCE": 0.5,
            "RELATIVE_SPEED": 12.5,
            "segment1": {
                "metadata": {"OBJECT_DESIGNATOR": "SAT1"},
                "data": {
                    "state_vector": {
                        "X": 7000,
                        "Y": 0,
                        "Z": 0,
                        "X_DOT": 0,
                        "Y_DOT": 7.5,
                        "Z_DOT": 0,
                    },
                    "covariance_matrix": {},
                },
            },
            "segment2": {
                "metadata": {"OBJECT_DESIGNATOR": "SAT2"},
                "data": {
                    "state_vector": {
                        "X": 7000.5,
                        "Y": 0,
                        "Z": 0,
                        "X_DOT": 0,
                        "Y_DOT": -7.5,
                        "Z_DOT": 0,
                    },
                    "covariance_matrix": {},
                },
            },
        }
    }
    cdm_file = tmp_path / "test.json"
    with open(cdm_file, "w") as f:
        json.dump(cdm_data, f)

    result = runner.invoke(
        cli,
        [
            "--st-username",
            "u",
            "--st-password",
            "p",
            "assess-cdm",
            "--cdm-file",
            str(cdm_file),
        ],
    )
    assert result.exit_code == 0
