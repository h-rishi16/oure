"""
OURE CLI - Task Sensor Command (Kalman Filter Update)
=====================================================
"""

import sys
import logging
from datetime import timedelta
import click
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from oure.conjunction.tca_finder import TCARefinementEngine
from oure.physics.numerical import NumericalPropagator
from oure.risk.calculator import RiskCalculator
from oure.uncertainty.sensor import SensorTaskingSimulator
from .cmd_analyze import _tle_to_initial_state, _default_covariance
from .main import cli, OUREContext

console = Console()

@cli.command()
@click.option("--primary", "-p", required=True, help="NORAD ID of the primary satellite.")
@click.option("--secondary", "-s", required=True, help="NORAD ID of the secondary satellite.")
@click.option("--sensor-noise-m", default=10.0, help="Radar measurement accuracy in meters (1-sigma).")
@click.pass_context
def task_sensor(ctx, primary, secondary, sensor_noise_m):
    """
    Simulate purchasing a new radar observation to reduce uncertainty and update Pc.
    """
    oure_ctx: OUREContext = ctx.obj
    log = logging.getLogger("oure.cli.task_sensor")

    records = {r.sat_id: r for r in oure_ctx.tle_fetcher.fetch(sat_ids=[primary, secondary])}
    flux = oure_ctx.flux_fetcher.get_current_f107()
        
    if primary not in records or secondary not in records:
        console.print("[bold red]✗ Failed to fetch both satellites.[/bold red]")
        sys.exit(1)

    p_state = _tle_to_initial_state(records[primary])
    s_state = _tle_to_initial_state(records[secondary])
    
    # We simulate a "stale" covariance for the secondary to show the massive improvement
    p_cov = _default_covariance(primary)
    
    # Stale covariance (e.g. 5km position uncertainty)
    s_cov_stale = _default_covariance(secondary)
    s_cov_stale.matrix[:3, :3] = np.eye(3) * 25.0 # 25 km^2 = 5km sigma
    
    base_prop = NumericalPropagator(solar_flux=flux)
    tca_finder = TCARefinementEngine()
    
    search_start = p_state.epoch
    search_end = search_start + timedelta(hours=72)
    tca_result = tca_finder.find_tca(p_state, base_prop, s_state, base_prop, search_start, search_end)
    
    if not tca_result:
        console.print("[bold green]No collision detected in look-ahead window.[/bold green]")
        return
        
    tca, miss = tca_result
    p_tca = base_prop.propagate_to(p_state, tca)
    s_tca = base_prop.propagate_to(s_state, tca)
    v_rel = np.linalg.norm(p_tca.v - s_tca.v)
    
    risk_calc = RiskCalculator()
    
    # 1. Baseline Risk (with Stale Covariance)
    event_baseline = type('Event', (), {
        'primary_id': primary, 'secondary_id': secondary, 'tca': tca,
        'miss_distance_km': miss, 'relative_velocity_km_s': v_rel,
        'primary_state': p_tca, 'secondary_state': s_tca,
        'primary_covariance': p_cov, 'secondary_covariance': s_cov_stale
    })()
    
    baseline_risk = risk_calc.compute_pc(event_baseline)
    
    # 2. Simulate Sensor Update via Kalman Filter
    simulator = SensorTaskingSimulator(sensor_noise_m=sensor_noise_m)
    s_cov_updated = simulator.simulate_radar_update(s_cov_stale)
    
    event_updated = type('Event', (), {
        'primary_id': primary, 'secondary_id': secondary, 'tca': tca,
        'miss_distance_km': miss, 'relative_velocity_km_s': v_rel,
        'primary_state': p_tca, 'secondary_state': s_tca,
        'primary_covariance': p_cov, 'secondary_covariance': s_cov_updated
    })()
    
    updated_risk = risk_calc.compute_pc(event_updated)
    
    console.print(Panel(f"Simulating Commercial Radar Tasking against {secondary} (Accuracy: {sensor_noise_m}m)", style="cyan"))
    
    table = Table(title="Covariance & Risk Update (EKF)")
    table.add_column("Metric", style="blue")
    table.add_column("Before Radar Track (Stale TLE)", style="red")
    table.add_column("After Radar Track", style="green")
    
    table.add_row(
        "Pos. Uncertainty (Trace)", 
        f"{np.trace(s_cov_stale.matrix[:3,:3]):.2f} km²", 
        f"{np.trace(s_cov_updated.matrix[:3,:3]):.5f} km²"
    )
    table.add_row(
        "B-Plane σ_x", 
        f"{baseline_risk.b_plane_sigma_x:.3f} km", 
        f"{updated_risk.b_plane_sigma_x:.3f} km"
    )
    table.add_row(
        "Probability of Collision", 
        f"{baseline_risk.pc:.2e}", 
        f"{updated_risk.pc:.2e}"
    )
    table.add_row(
        "Alert Level", 
        f"{baseline_risk.warning_level}", 
        f"{updated_risk.warning_level}"
    )
    
    console.print(table)
    
    if updated_risk.warning_level != baseline_risk.warning_level:
        console.print(f"\n[bold green]✓ Radar tasking successfully downgraded risk to {updated_risk.warning_level}. Maneuver aborted.[/bold green]")
    else:
        console.print("\n[bold yellow]⚠ Radar tasking did not change the alert tier. Proceed to maneuver analysis.[/bold yellow]")
