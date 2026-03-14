"""
OURE CLI - Analyze Command
==========================
"""

import json
import logging
import sys
from datetime import UTC
from pathlib import Path
from typing import Any

import click
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from oure.conjunction.assessor import ConjunctionAssessor
from oure.core.models import CovarianceMatrix, RiskResult, StateVector
from oure.physics.factory import PropagatorFactory
from oure.risk.calculator import RiskCalculator

from .main import OUREContext, cli

console = Console()

def _tle_to_initial_state(tle: Any) -> StateVector:
    from oure.core import constants
    import math
    n = tle.mean_motion_rev_per_day * constants.TWO_PI / constants.SECONDS_PER_DAY
    a = (constants.MU_KM3_S2 / n**2) ** (1.0/3.0) if n > 0 else constants.R_EARTH_KM + 400

    e = tle.eccentricity
    i = math.radians(tle.inclination_deg)
    raan = math.radians(tle.raan_deg)
    omega = math.radians(tle.arg_perigee_deg)
    M = math.radians(tle.mean_anomaly_deg)

    # Solve Kepler for E
    E = M
    for _ in range(10):
        E = E - (E - e * math.sin(E) - M) / (1 - e * math.cos(E))

    # True anomaly
    nu = 2 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2), math.sqrt(1 - e) * math.cos(E / 2))

    p = a * (1 - e**2)
    r_mag = p / (1 + e * math.cos(nu))

    # Perifocal coordinates
    r_pqw = r_mag * np.array([math.cos(nu), math.sin(nu), 0.0])
    v_pqw = math.sqrt(constants.MU_KM3_S2 / p) * np.array([-math.sin(nu), e + math.cos(nu), 0.0])

    # Rotation PQW -> ECI
    c_O, s_O = math.cos(raan), math.sin(raan)
    c_i, s_i = math.cos(i), math.sin(i)
    c_w, s_w = math.cos(omega), math.sin(omega)

    R = np.array([
        [c_O*c_w - s_O*s_w*c_i, -c_O*s_w - s_O*c_w*c_i, s_O*s_i],
        [s_O*c_w + c_O*s_w*c_i, -s_O*s_w + c_O*c_w*c_i, -c_O*s_i],
        [s_w*s_i, c_w*s_i, c_i]
    ])

    return StateVector(r=R @ r_pqw, v=R @ v_pqw, epoch=tle.epoch, sat_id=tle.sat_id)

def _default_covariance(sat_id: str) -> CovarianceMatrix:
    from datetime import datetime
    P = np.diag([1.0, 1.0, 1.0, 1e-6, 1e-6, 1e-6])
    return CovarianceMatrix(matrix=P, epoch=datetime.now(UTC), sat_id=sat_id)

def _print_results_table(results: list[RiskResult]) -> None:
    table = Table(title="Conjunction Assessment Results")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Sec ID", style="magenta")
    table.add_column("TCA (UTC)", justify="center", style="green")
    table.add_column("Miss (km)", justify="right", style="blue")
    table.add_column("Pc", justify="right", style="red")
    table.add_column("Level", justify="center")

    for idx, r in enumerate(results, 1):
        color = "white"
        symbol = "⚪"
        if r.warning_level == "RED":
            color = "red"
            symbol = "🔴 RED"
        elif r.warning_level == "YELLOW":
            color = "yellow"
            symbol = "🟡 YELLOW"
        elif r.warning_level == "GREEN":
            color = "green"
            symbol = "🟢 GREEN"

        table.add_row(
            str(idx),
            r.conjunction.secondary_id,
            r.conjunction.tca.strftime('%Y-%m-%d %H:%M'),
            f"{r.conjunction.miss_distance_km:.3f}",
            f"[{color}]{r.pc:.2e}[/{color}]",
            f"[{color}]{symbol}[/{color}]"
        )
    console.print(table)

def _print_summary_banner(max_pc: float, num_events: int = 1) -> None:
    if max_pc >= 1e-3:
        color = "red"
        symbol = "🔴 RED ALERT"
    elif max_pc >= 1e-5:
        color = "yellow"
        symbol = "🟡 YELLOW ALERT"
    else:
        color = "green"
        symbol = "🟢 ALL CLEAR"

    panel = Panel(
        f"{symbol} — Max Pc = {max_pc:.2e} across {num_events} analyzed events",
        title="Summary",
        expand=False,
        border_style=color
    )
    console.print(panel)

def _save_results_to_json(results: list[RiskResult], path: Path) -> None:
    output = []
    for r in results:
        output.append({
            "primary_id":      r.conjunction.primary_id,
            "secondary_id":    r.conjunction.secondary_id,
            "tca":             r.conjunction.tca.isoformat(),
            "pc":              r.pc,
            "warning_level":   r.warning_level,
            "miss_distance_km": r.conjunction.miss_distance_km,
            "rel_velocity_km_s": r.conjunction.relative_velocity_km_s,
            "sigma_bplane_km": [r.b_plane_sigma_x, r.b_plane_sigma_z],
            "hard_body_radius_m": r.hard_body_radius_m,
        })
    with open(path, "w") as f:
        json.dump(output, f, indent=2)

@cli.command()
@click.option("--primary", "-p", required=True, help="NORAD ID of the primary satellite.")
@click.option("--secondary", "-s", multiple=True, help="NORAD ID(s) of secondary satellites to screen against.")
@click.option("--secondaries-file", type=click.Path(exists=True), help="JSON file with list of NORAD IDs to screen.")
@click.option("--look-ahead", default=72.0, show_default=True, help="Look-ahead window in hours.")
@click.option("--screening-dist", default=5.0, show_default=True, help="KD-Tree screening distance in km.")
@click.option("--mc-samples", default=1000, show_default=True, help="Monte Carlo samples for uncertainty propagation.")
@click.option("--hard-body-radius", default=20.0, show_default=True, help="Combined hard-body radius in metres.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Save results to JSON.")
@click.pass_context
def analyze(
    ctx: click.Context, primary: str, secondary: tuple[str, ...], secondaries_file: str | None, look_ahead: float,
    screening_dist: float, mc_samples: int, hard_body_radius: float, output: str | None
) -> list[RiskResult] | None:
    """
    Run full conjunction assessment and Pc calculation pipeline.
    """
    oure_ctx: OUREContext = ctx.obj
    log = logging.getLogger("oure.cli.analyze")

    secondary_ids = list(secondary)
    if secondaries_file:
        with open(secondaries_file) as f:
            secondary_ids.extend(json.load(f))

    if not secondary_ids:
        console.print("✗ No secondary satellites specified.", style="bold red")
        sys.exit(1)

    all_ids = [primary] + secondary_ids

    panel = Panel(
        f"Primary: {primary} | Look-ahead: {look_ahead}h | Screening: {screening_dist}km | MC: {mc_samples}",
        title="OURE Conjunction Assessment",
        expand=False,
        border_style="blue"
    )
    console.print(panel)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn()) as progress:
        task1 = progress.add_task("[cyan]Fetching data...", total=3)
        records = {r.sat_id: r for r in oure_ctx.tle_fetcher.fetch(sat_ids=all_ids)}
        progress.update(task1, advance=1)
        flux = oure_ctx.flux_fetcher.get_current_f107()
        progress.update(task1, advance=1)
        if primary not in records:
            console.print(f"\n✗ Primary {primary} not found in catalog.", style="bold red")
            sys.exit(1)
        progress.update(task1, advance=1)

    console.print(f"   [green]✓ F10.7={flux:.1f} | {len(records)} TLEs loaded[/green]")

    primary_tle = records[primary]
    primary_prop = PropagatorFactory.build(primary_tle, solar_flux=flux)
    primary_state = _tle_to_initial_state(primary_tle)
    primary_cov = _default_covariance(primary_tle.sat_id)

    secondaries_data = []
    for sid in secondary_ids:
        if sid not in records:
            console.print(f"   [yellow]⚠ {sid} not in cache — skipping[/yellow]")
            continue
        tle = records[sid]
        prop = PropagatorFactory.build(tle, solar_flux=flux)
        state = _tle_to_initial_state(tle)
        cov = _default_covariance(tle.sat_id)
        secondaries_data.append((state, cov, prop))

    console.print(f"\n[cyan]🔍 Running KD-Tree conjunction screening ({len(secondaries_data)} objects)...[/cyan]")
    assessor = ConjunctionAssessor(screening_distance_km=screening_dist)
    events = assessor.find_conjunctions(
        primary_state, primary_cov, primary_prop,
        secondaries_data, look_ahead_hours=look_ahead
    )

    if not events:
        console.print("\n[bold green]✓ No conjunctions found in look-ahead window.[/bold green]")
        return []

    console.print(f"\n[bold yellow]⚠  Found {len(events)} conjunction event(s):[/bold yellow]\n")

    calculator = RiskCalculator(hard_body_radius_m=hard_body_radius)
    results = []

    for i, event in enumerate(events):
        result = calculator.compute_pc(event)
        results.append(result)

    _print_results_table(results)

    if output:
        _save_results_to_json(results, Path(output))
        console.print(f"\n[bold green]💾 Results saved to {output}[/bold green]")

    max_pc = max(r.pc for r in results)
    _print_summary_banner(max_pc, len(results))

    return results
