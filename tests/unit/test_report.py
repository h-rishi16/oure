import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from oure.cli.cmd_report import report


@pytest.fixture
def sample_results_json(tmp_path: Path) -> Path:
    data = [
        {
            "primary_id": "25544",
            "secondary_id": "43205",
            "tca": "2024-01-16T14:23:11",
            "pc": 2.14e-04,
            "warning_level": "YELLOW",
            "miss_distance_km": 0.183,
            "rel_velocity_km_s": 12.34,
        },
        {
            "primary_id": "25544",
            "secondary_id": "47813",
            "tca": "2024-01-17T09:17:44",
            "pc": 8.32e-07,
            "warning_level": "GREEN",
            "miss_distance_km": 1.041,
            "rel_velocity_km_s": 10.5,
        },
    ]
    file_path = tmp_path / "test_results.json"
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path


def test_report_command_pdf(sample_results_json, tmp_path):
    runner = CliRunner()
    output_pdf = tmp_path / "report.pdf"

    result = runner.invoke(
        report,
        [
            "--results-file",
            str(sample_results_json),
            "--format",
            "pdf",
            "--output",
            str(output_pdf),
        ],
    )

    assert result.exit_code == 0
    assert "PDF report generated successfully" in result.output
    assert output_pdf.exists()
