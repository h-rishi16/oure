"""
OURE CLI - Avoid Command (Maneuver Trade Space)
===============================================
"""

import sys
import json
import logging
from pathlib import Path
from datetime import timedelta, timezone
import click
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from oure.core.models import StateVector, ConjunctionEvent
from oure.physics.numerical import NumericalPropagator
from oure.physics.maneuver import Maneuver, ManeuverPropagator
from oure.conjunction.tca_finder import TCARefinementEngine
from oure.risk.calculator import RiskCalculator
from .cmd_analyze import _tle_to_initial_state, _default_covariance
from .main import cli, OUREContext

console = Console()

@cli.command()
@click.option("--primary", "-p", required=True, help="NORAD ID of the primary satellite.")
@click.option("--secondary", "-s", required=True, help="NORAD ID of the secondary satellite.")
@click.option("--burn-time-before-tca", default=12.0, help="Hours before TCA to execute burn.")
@click.pass_context
def avoid(ctx, primary, secondary, burn_time_before_tca):
    """
    Simulate collision avoidance maneuvers to find the cheapest safe delta-V.
    """
    oure_ctx: OUREContext = ctx.obj
    log = logging.getLogger("oure.cli.avoid")

    with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}")) as progress:
        task = progress.add_task("Fetching current orbital data...")
        records = {r.sat_id: r for r in oure_ctx.tle_fetcher.fetch(sat_ids=[primary, secondary])}
        flux = oure_ctx.flux_fetcher.get_current_f107()
        
    if primary not in records or secondary not in records:
        console.print("[bold red]✗ Failed to fetch both satellites.[/bold red]")
        sys.exit(1)

    primary_tle = records[primary]
    secondary_tle = records[secondary]
    
    p_state = _tle_to_initial_state(primary_tle)
    s_state = _tle_to_initial_state(secondary_tle)
    p_cov = _default_covariance(primary_tle.sat_id)
    s_cov = _default_covariance(secondary_tle.sat_id)

    # 1. Base Propagation to find nominal TCA
    console.print("[cyan]Running baseline High-Precision propagation...[/cyan]")
    base_prop = NumericalPropagator(solar_flux=flux)
    
    tca_finder = TCARefinementEngine()
    search_start = p_state.epoch
    search_end = search_start + timedelta(hours=72)
    
    tca_result = tca_finder.find_tca(
        p_state, base_prop, s_state, base_prop, search_start, search_end
    )
    
    if not tca_result:
        console.print("[bold green]No conjunction found in baseline.[/bold green]")
        return
        
    nominal_tca, nominal_miss = tca_result
    
    # Calculate baseline Pc
    p_tca_state = base_prop.propagate_to(p_state, nominal_tca)
    s_tca_state = base_prop.propagate_to(s_state, nominal_tca)
    v_rel = float(np.linalg.norm(p_tca_state.v - s_tca_state.v))
    
    nominal_event = ConjunctionEvent(
        primary_id=primary, secondary_id=secondary, tca=nominal_tca,
        miss_distance_km=nominal_miss, relative_velocity_km_s=v_rel,
        primary_state=p_tca_state, secondary_state=s_tca_state,
        primary_covariance=p_cov, secondary_covariance=s_cov
    )
    
    risk_calc = RiskCalculator()
    nominal_risk = risk_calc.compute_pc(nominal_event)
    
    console.print(f"Baseline TCA: [bold]{nominal_tca.strftime('%Y-%m-%d %H:%M:%S')}[/bold]")
    console.print(f"Baseline Miss: [bold]{nominal_miss:.3f} km[/bold]")
    console.print(f"Baseline Pc: [bold red]{nominal_risk.pc:.2e}[/bold red]\n")
    
    # 2. Setup Trade Space
    burn_epoch = nominal_tca - timedelta(hours=burn_time_before_tca)
    console.print(f"Simulating maneuvers at T-{burn_time_before_tca}h ({burn_epoch.strftime('%H:%M:%S')})")
    
    # We will simulate prograde and retrograde burns (along the velocity vector)
    # Get velocity vector at burn epoch to figure out along-track direction
    burn_state = base_prop.propagate_to(p_state, burn_epoch)
    v_hat = burn_state.v / np.linalg.norm(burn_state.v)
    
    test_dvs_cm_s = [-5.0, -1.0, -0.5, -0.1, 0.1, 0.5, 1.0, 5.0]  # cm/s
    
    table = Table(title="Collision Avoidance Trade Space")
    table.add_column("Maneuver (cm/s)", justify="right", style="cyan")
    table.add_column("Direction", style="blue")
    table.add_column("New Miss (km)", justify="right")
    table.add_column("New Pc", justify="right", style="bold")
    table.add_column("Status", justify="center")

    for dv_cm in test_dvs_cm_s:
        dv_km_s = (dv_cm / 100.0) / 1000.0
        delta_v_vec = v_hat * dv_km_s
        
        maneuver = Maneuver(burn_epoch=burn_epoch, delta_v_eci=delta_v_vec)
        man_prop = ManeuverPropagator(base_propagator=base_prop, maneuvers=[maneuver])
        
        # Find new TCA with maneuver
        new_tca_result = tca_finder.find_tca(
            p_state, man_prop, s_state, base_prop, 
            burn_epoch, burn_epoch + timedelta(hours=burn_time_before_tca + 2)
        )
        
        if new_tca_result:
            new_tca, new_miss = new_tca_result
            p_new_tca = man_prop.propagate_to(p_state, new_tca)
            s_new_tca = base_prop.propagate_to(s_state, new_tca)
            new_v_rel = float(np.linalg.norm(p_new_tca.v - s_new_tca.v))
            
            new_event = ConjunctionEvent(
                primary_id=primary, secondary_id=secondary, tca=new_tca,
                miss_distance_km=new_miss, relative_velocity_km_s=new_v_rel,
                primary_state=p_new_tca, secondary_state=s_new_tca,
                primary_covariance=p_cov, secondary_covariance=s_cov
            )
            
            new_risk = risk_calc.compute_pc(new_event)
            pc_str = f"{new_risk.pc:.2e}"
            
            if new_risk.warning_level == "GREEN":
                status = "[green]SAFE[/green]"
                pc_str = f"[green]{pc_str}[/green]"
            elif new_risk.warning_level == "YELLOW":
                status = "[yellow]ELEVATED[/yellow]"
                pc_str = f"[yellow]{pc_str}[/yellow]"
            else:
                status = "[red]DANGER[/red]"
                pc_str = f"[red]{pc_str}[/red]"
                
            dir_str = "Prograde" if dv_cm > 0 else "Retrograde"
            
            table.add_row(f"{dv_cm:+.1f}", dir_str, f"{new_miss:.3f}", pc_str, status)

    console.print(table)
