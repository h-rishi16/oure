"""
OURE CLI - CDM Assess Command
=============================
"""

import sys

import click
from rich.console import Console

from oure.data.cdm_parser import CDMParser
from oure.risk.calculator import RiskCalculator

from .cmd_analyze import _print_results_table, _print_summary_banner
from .main import cli

console = Console()

@cli.command()
@click.option("--cdm-file", type=click.Path(exists=True), required=True, help="Path to the JSON CDM file.")
@click.option("--hard-body-radius", default=20.0, show_default=True, help="Combined hard-body radius in metres.")
def assess_cdm(cdm_file: str, hard_body_radius: float) -> None:
    """
    Ingest a CCSDS Conjunction Data Message and calculate risk.
    """
    console.print(f"[cyan]Parsing CDM from {cdm_file}...[/cyan]")

    try:
        event = CDMParser.parse_json(cdm_file)
    except Exception as e:
        console.print(f"[bold red]Failed to parse CDM: {e}[/bold red]")
        sys.exit(1)

    console.print(f"[green]✓ Loaded Conjunction Event: {event.primary_id} vs {event.secondary_id}[/green]")
    console.print(f"   TCA: {event.tca}")
    console.print(f"   Miss Distance: {event.miss_distance_km:.3f} km")

    calculator = RiskCalculator(hard_body_radius_m=hard_body_radius)
    result = calculator.compute_pc(event)

    _print_results_table([result])
    _print_summary_banner(result.pc, 1)
