import json
from unittest.mock import patch

from click.testing import CliRunner

from oure.cli.main import cli


def test_cli_plot_command(tmp_path):
    runner = CliRunner()

    results_file = tmp_path / "results.json"
    results_data = [
        {
            "primary_id": "25544",
            "secondary_id": "43205",
            "pc": 1e-4,
            "warning_level": "YELLOW",
            "miss_distance_km": 0.5,
            "rel_velocity_km_s": 10.0,
            "tca": "2026-03-12T14:23:11Z",
            "sigma_bplane_km": [1.0, 1.0],
            "hard_body_radius_m": 20.0,
        }
    ]
    with open(results_file, "w") as f:
        json.dump(results_data, f)

    out_file = tmp_path / "plot.html"

    with patch("oure.risk.plotter.RiskPlotter.plot_bplane_from_json") as mock_plot:
        result = runner.invoke(
            cli,
            ["plot", "--results-file", str(results_file), "--output", str(out_file)],
        )

    assert result.exit_code == 0
    assert mock_plot.called
