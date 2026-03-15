"""
OURE CLI - fleet Command (Distributed "All-on-All" Screening)
=============================================================
"""

import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
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
    _save_results_to_json,
    _tle_to_initial_state,
    console,
)


def _screen_single_primary(
    primary_id: str,
    primary_tle: Any,
    secondary_ids: list[str],
    records: dict[str, Any],
    flux: float,
    look_ahead: float,
    screening_dist: float,
    hard_body_radius: float,
) -> list[RiskResult]:
    try:
        primary_state = _tle_to_initial_state(primary_tle)
        primary_prop = PropagatorFactory.build(primary_tle, solar_flux=flux)
        primary_cov = _default_covariance(primary_id)

        secondaries_data = []
        for sid in secondary_ids:
            if sid == primary_id or sid not in records:
                continue
            tle = records[sid]
            prop = PropagatorFactory.build(tle, solar_flux=flux)
            state = _tle_to_initial_state(tle)
            cov = _default_covariance(sid)
            secondaries_data.append((state, cov, prop))

        assessor = ConjunctionAssessor(screening_distance_km=screening_dist)
        events = assessor.find_conjunctions(
            primary_state,
            primary_cov,
            primary_prop,
            secondaries_data,
            look_ahead_hours=look_ahead,
        )

        calculator = RiskCalculator(hard_body_radius_m=hard_body_radius)
        results = [calculator.compute_pc(e) for e in events]
        return results
    except Exception:
        return []


@cli.command()
@click.option(
    "--primaries-file",
    type=click.Path(exists=True),
    required=True,
    help="JSON file with primary NORAD IDs.",
)
@click.option(
    "--secondaries-file",
    type=click.Path(exists=True),
    required=True,
    help="JSON file with secondary NORAD IDs.",
)
@click.option("--look-ahead", default=72.0, show_default=True)
@click.option("--screening-dist", default=5.0, show_default=True)
@click.option("--hard-body-radius", default=20.0, show_default=True)
@click.option("--workers", default=4, help="Number of parallel processes.")
@click.option("--output", "-o", type=click.Path(), default="fleet_results.json")
@click.pass_context
def analyze_fleet(
    ctx: click.Context,
    primaries_file: str,
    secondaries_file: str,
    look_ahead: float,
    screening_dist: float,
    hard_body_radius: float,
    workers: int,
    output: str,
) -> None:
    """Run distributed conjunction screening for an entire fleet."""
    oure_ctx: OUREContext = ctx.obj
    UI.header("Fleet Screening Engine", "Distributed multi-satellite proximity search")

    try:
        with open(primaries_file) as f:
            primary_ids = json.load(f)
        with open(secondaries_file) as f:
            secondary_ids = json.load(f)
    except Exception as e:
        UI.error(f"Failed to read fleet files: {e}")
        sys.exit(1)

    all_ids = list(set(primary_ids + secondary_ids))

    with console.status("[bold cyan]Fetching TLE data...") as status:
        try:
            records = {r.sat_id: r for r in oure_ctx.tle_fetcher.fetch(sat_ids=all_ids)}
            flux = oure_ctx.flux_fetcher.get_current_f107()
        except Exception as e:
            UI.error(f"Data fetch failed: {e}")
            sys.exit(1)

    all_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Screening fleet (Distributed)...", total=len(primary_ids)
        )

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _screen_single_primary,
                    pid,
                    records[pid],
                    secondary_ids,
                    records,
                    flux,
                    look_ahead,
                    screening_dist,
                    hard_body_radius,
                ): pid
                for pid in primary_ids
                if pid in records
            }

            for future in as_completed(futures):
                res = future.result()
                all_results.extend(res)
                progress.update(task, advance=1)

    if not all_results:
        UI.success("No conjunctions found across the fleet.")
        return

    all_results.sort(key=lambda r: r.pc, reverse=True)
    _print_results_table(all_results[:20])  # show top 20
    _save_results_to_json(all_results, Path(output))
    UI.success(f"Saved {len(all_results)} total events to {output}")
