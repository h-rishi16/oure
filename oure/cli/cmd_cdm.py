"""
OURE CLI - CDM Assess Command
=============================
"""

import sys

import click

from oure.data.cdm_parser import CDMParser
from oure.risk.calculator import RiskCalculator

from .main import cli
from .utils import UI, _print_results_table, _print_summary_banner


@cli.command()
@click.option("--cdm-file", type=click.Path(exists=True), required=True, help="Path to the JSON CDM file.")
@click.option("--hard-body-radius", default=20.0, show_default=True, help="Combined hard-body radius in metres.")
def assess_cdm(cdm_file: str, hard_body_radius: float) -> None:
    """
    Ingest a CCSDS Conjunction Data Message and calculate risk.
    """
    UI.header("CDM Ingestion Tool", f"Processing Space Force CDM: {cdm_file}")

    try:
        event = CDMParser.parse_json(cdm_file)
    except Exception as e:
        UI.error(f"Failed to parse CDM: {e}", "Ensure the file follows the CCSDS JSON schema.")
        sys.exit(1)

    UI.success(f"Loaded Conjunction Event: [highlight]{event.primary_id}[/highlight] vs [highlight]{event.secondary_id}[/highlight]")

    calculator = RiskCalculator(hard_body_radius_m=hard_body_radius)
    result = calculator.compute_pc(event)

    _print_results_table([result])
    _print_summary_banner(result.pc, 1)
