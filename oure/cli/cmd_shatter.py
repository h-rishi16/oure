"""
OURE CLI - Shatter Command (Debris Fragmentation Modeling)
==========================================================
"""

import sys
import logging
from pathlib import Path
from datetime import timedelta
import click
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from oure.physics.breakup import BreakupModel
from oure.physics.numerical import NumericalPropagator
from oure.conjunction.tca_finder import TCARefinementEngine
from oure.risk.plotter import RiskPlotter
from .cmd_analyze import _tle_to_initial_state
from .main import cli, OUREContext

console = Console()

@cli.command()
@click.option("--primary", "-p", required=True, help="NORAD ID of the primary satellite.")
@click.option("--secondary", "-s", required=True, help="NORAD ID of the secondary satellite.")
@click.option("--mass1", default=500.0, help="Mass of primary in kg.")
@click.option("--mass2", default=200.0, help="Mass of secondary in kg.")
@click.option("--fragments", default=1000, help="Number of debris fragments to simulate.")
@click.option("--propagate-hours", default=24.0, help="Hours to propagate the cloud post-impact.")
@click.pass_context
def shatter(ctx, primary, secondary, mass1, mass2, fragments, propagate_hours):
    """
    Simulate a hypervelocity collision and propagate the resulting debris cloud.
    """
    oure_ctx: OUREContext = ctx.obj
    log = logging.getLogger("oure.cli.shatter")

    with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}")) as progress:
        task = progress.add_task("Fetching orbital data...")
        records = {r.sat_id: r for r in oure_ctx.tle_fetcher.fetch(sat_ids=[primary, secondary])}
        flux = oure_ctx.flux_fetcher.get_current_f107()
        
    if primary not in records or secondary not in records:
        console.print("[bold red]✗ Failed to fetch both satellites.[/bold red]")
        sys.exit(1)

    p_state = _tle_to_initial_state(records[primary])
    s_state = _tle_to_initial_state(records[secondary])
    
    base_prop = NumericalPropagator(solar_flux=flux)
    tca_finder = TCARefinementEngine()
    
    console.print("\n[cyan]Locating exact impact time (TCA)...[/cyan]")
    search_start = p_state.epoch
    search_end = search_start + timedelta(hours=72)
    tca_result = tca_finder.find_tca(p_state, base_prop, s_state, base_prop, search_start, search_end)
    
    if not tca_result:
        console.print("[bold green]No collision detected in look-ahead window.[/bold green]")
        return
        
    tca, miss = tca_result
    
    # We force a collision at TCA for the simulation
    p_tca = base_prop.propagate_to(p_state, tca)
    s_tca = base_prop.propagate_to(s_state, tca)
    # Align secondary to primary perfectly for impact
    s_tca_aligned = type(s_tca)(r=p_tca.r, v=s_tca.v, epoch=tca, sat_id=s_tca.sat_id)
    
    v_rel = np.linalg.norm(p_tca.v - s_tca_aligned.v)
    energy_mj = 0.5 * min(mass1, mass2) * (v_rel * 1000)**2 / 1e6
    
    panel = Panel(
        f"Impact Time: {tca}\n"
        f"Relative Velocity: {v_rel:.2f} km/s\n"
        f"Impact Energy: {energy_mj:.2f} MJ",
        title="💥 Hypervelocity Impact Detected",
        border_style="red"
    )
    console.print(panel)
    
    with Progress(SpinnerColumn(), TextColumn("[red]{task.description}")) as progress:
        task = progress.add_task(f"Shattering into {fragments} fragments...")
        debris_states = BreakupModel.simulate_collision(
            p_tca, mass1, s_tca_aligned, mass2, tca, num_fragments=fragments
        )
        
    initial_debris_vecs = np.array([d.state_vector_6d for d in debris_states])
    
    with Progress(SpinnerColumn(), TextColumn("[yellow]{task.description}")) as progress:
        task = progress.add_task(f"Propagating debris cloud +{propagate_hours} hours...")
        target_epoch = tca + timedelta(hours=propagate_hours)
        final_debris_vecs = base_prop.propagate_many_to(initial_debris_vecs, tca, target_epoch)
        
    final_positions = final_debris_vecs[:, :3]
    center_of_cloud = np.mean(final_positions, axis=0)
    max_dispersion = np.max(np.linalg.norm(final_positions - center_of_cloud, axis=1))
    
    console.print(f"\n[bold yellow]Debris Cloud Status at T+{propagate_hours} hours[/bold yellow]")
    console.print(f"Cloud Center (ECI): {center_of_cloud}")
    console.print(f"Maximum Dispersion Radius: [bold]{max_dispersion:.2f} km[/bold]")
    console.print("\n[dim]Note: Run `oure plot` features for 3D visualization (coming soon to shatter).[/dim]")
