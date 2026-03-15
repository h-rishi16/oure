"""
OURE CLI - Analyze Command
==========================
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

import click
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from oure.conjunction.assessor import ConjunctionAssessor
from oure.core.models import RiskResult
from oure.physics.factory import PropagatorFactory
from oure.risk.calculator import RiskCalculator

from .main import OUREContext, cli
from .utils import (
    UI,
    _default_covariance,
    _print_results_table,
    _print_summary_banner,
    _save_results_to_json,
    _tle_to_initial_state,
    console,
)


def validate_norad_id(
    ctx: click.Context, param: click.Parameter, value: str | tuple[str, ...]
) -> Any:
    if not value:
        return value

    if isinstance(value, tuple):
        for v in value:
            if not re.fullmatch(r"\d{1,9}", v):
                raise click.BadParameter(
                    f"Invalid NORAD ID: {v!r}. Must be 1–9 digits."
                )
        return value

    if not re.fullmatch(r"\d{1,9}", value):
        raise click.BadParameter(f"Invalid NORAD ID: {value!r}. Must be 1–9 digits.")
    return value


@cli.command()
@click.option(
    "--primary",
    "-p",
    required=True,
    callback=validate_norad_id,
    help="NORAD ID of the primary satellite.",
)
@click.option(
    "--secondary",
    "-s",
    multiple=True,
    callback=validate_norad_id,
    help="NORAD ID(s) of secondary satellites to screen against.",
)
@click.option(
    "--secondaries-file",
    type=click.Path(exists=True),
    help="JSON file with list of NORAD IDs to screen.",
)
@click.option(
    "--look-ahead", default=72.0, show_default=True, help="Look-ahead window in hours."
)
@click.option(
    "--screening-dist",
    default=5.0,
    show_default=True,
    help="KD-Tree screening distance in km.",
)
@click.option(
    "--mc-samples",
    default=1000,
    show_default=True,
    help="Monte Carlo samples for uncertainty propagation.",
)
@click.option(
    "--hard-body-radius",
    default=20.0,
    show_default=True,
    help="Combined hard-body radius in metres.",
)
@click.option(
    "--output", "-o", type=click.Path(), default=None, help="Save results to JSON."
)
@click.pass_context
def analyze(
    ctx: click.Context,
    primary: str,
    secondary: tuple[str, ...],
    secondaries_file: str | None,
    look_ahead: float,
    screening_dist: float,
    mc_samples: int,
    hard_body_radius: float,
    output: str | None,
) -> list[RiskResult] | None:
    """
    Run full conjunction assessment and Pc calculation pipeline.
    """
    oure_ctx: OUREContext = ctx.obj
    UI.header(
        "Risk Analysis Pipeline", f"Screening primary {primary} against secondaries"
    )

    secondary_ids = list(secondary)
    if secondaries_file:
        try:
            with open(secondaries_file) as f:
                secondary_ids.extend(json.load(f))
        except Exception as e:
            UI.error(f"Failed to read secondaries file: {e}")
            sys.exit(1)

    if not secondary_ids:
        UI.error(
            "No secondary satellites specified.",
            "Use --secondary or --secondaries-file.",
        )
        sys.exit(1)

    all_ids = [primary] + secondary_ids

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task1 = progress.add_task("[cyan]Fetching data...", total=3)
        try:
            records = {r.sat_id: r for r in oure_ctx.tle_fetcher.fetch(sat_ids=all_ids)}
            progress.update(task1, advance=1)
            flux = oure_ctx.flux_fetcher.get_current_f107()
            progress.update(task1, advance=1)
            if primary not in records:
                UI.error(f"Primary {primary} not found in catalog.")
                sys.exit(1)
            progress.update(task1, advance=1)
        except Exception as e:
            UI.error(f"Data fetch failed: {e}")
            sys.exit(1)

    console.print(
        f"   [success]DONE[/success] [info]F10.7={flux:.1f}[/info] [dim]|[/dim] [success]{len(records)} TLEs loaded[/success]"
    )

    primary_tle = records[primary]
    primary_prop = PropagatorFactory.build(primary_tle, solar_flux=flux)
    primary_state = _tle_to_initial_state(primary_tle)
    primary_cov = _default_covariance(primary_tle.sat_id)

    secondaries_data = []
    for sid in secondary_ids:
        if sid not in records:
            console.print(
                f"   [warning]WARNING:[/warning] [dim]{sid} not in cache — skipping[/dim]"
            )
            continue
        tle = records[sid]
        prop = PropagatorFactory.build(tle, solar_flux=flux)
        state = _tle_to_initial_state(tle)
        cov = _default_covariance(tle.sat_id)
        secondaries_data.append((state, cov, prop))

    console.print(
        f"\n[bold cyan]Running KD-Tree conjunction screening ({len(secondaries_data)} objects)...[/bold cyan]"
    )
    assessor = ConjunctionAssessor(screening_distance_km=screening_dist)
    events = assessor.find_conjunctions(
        primary_state,
        primary_cov,
        primary_prop,
        secondaries_data,
        look_ahead_hours=look_ahead,
    )

    if not events:
        UI.success("No conjunctions found in look-ahead window.")
        return []

    console.print(f"\n[warning]Found {len(events)} conjunction event(s):[/warning]\n")

    calculator = RiskCalculator(hard_body_radius_m=hard_body_radius)
    results = []

    for i, event in enumerate(events):
        result = calculator.compute_pc(event)
        results.append(result)

    _print_results_table(results)

    if output:
        _save_results_to_json(results, Path(output))
        UI.success(f"Results saved to {output}")

    max_pc = max(r.pc for r in results)
    _print_summary_banner(max_pc, len(results))

    return results
