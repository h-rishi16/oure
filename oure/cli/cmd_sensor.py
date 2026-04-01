"""
OURE CLI - Task Sensor Command (Kalman Filter Update)
=====================================================
"""

import sys
from datetime import timedelta

import click
import numpy as np
from rich.panel import Panel
from rich.table import Table

from oure.conjunction.tca_finder import TCARefinementEngine
from oure.physics.numerical import NumericalPropagator
from oure.risk.calculator import RiskCalculator
from oure.uncertainty.sensor import SensorTaskingSimulator

from .main import OUREContext, cli
from .utils import UI, _default_covariance, _tle_to_initial_state, console


@cli.command()
@click.option(
    "--primary", "-p", required=True, help="NORAD ID of the primary satellite."
)
@click.option(
    "--secondary", "-s", required=True, help="NORAD ID of the secondary satellite."
)
@click.option(
    "--sensor-noise-m",
    default=10.0,
    help="Radar measurement accuracy in meters (1-sigma).",
)
@click.pass_context
def task_sensor(
    ctx: click.Context, primary: str, secondary: str, sensor_noise_m: float
) -> None:
    """
    Simulate purchasing a new radar observation to reduce uncertainty and update Pc.
    """
    oure_ctx: OUREContext = ctx.obj
    UI.header(
        "Sensor Tasking Simulator", "Collapsing covariance via commercial radar updates"
    )

    with console.status("[bold cyan]Fetching current orbital data...") as status:
        records = {
            r.sat_id: r
            for r in oure_ctx.tle_fetcher.fetch(sat_ids=[primary, secondary])
        }
        flux = oure_ctx.flux_fetcher.get_current_f107()

    if primary not in records or secondary not in records:
        UI.error(f"Satellite data missing for {primary} or {secondary}.")
        sys.exit(1)

    p_state = _tle_to_initial_state(records[primary])
    s_state = _tle_to_initial_state(records[secondary])

    p_cov = _default_covariance(primary)
    s_cov_orig = _default_covariance(secondary)
    
    # Create stale covariance by inflating position uncertainty without mutating in-place
    stale_matrix = s_cov_orig.matrix.copy()
    stale_matrix[:3, :3] = np.eye(3) * 25.0  # 25 km^2 = 5km sigma
    from oure.core.models import CovarianceMatrix
    s_cov_stale = CovarianceMatrix(
        matrix=stale_matrix, 
        epoch=s_cov_orig.epoch, 
        sat_id=s_cov_orig.sat_id
    )

    base_prop = NumericalPropagator(solar_flux=flux)
    tca_finder = TCARefinementEngine()

    search_start = p_state.epoch
    search_end = search_start + timedelta(hours=72)

    with console.status("[bold cyan]Locating TCA...") as status:
        tca_result = tca_finder.find_tca(
            p_state, base_prop, s_state, base_prop, search_start, search_end
        )

    if not tca_result:
        UI.success("No collision detected in look-ahead window.")
        return

    tca, miss = tca_result
    p_tca = base_prop.propagate_to(p_state, tca)
    s_tca = base_prop.propagate_to(s_state, tca)
    v_rel = float(np.linalg.norm(p_tca.v - s_tca.v))

    risk_calc = RiskCalculator()

    # 1. Baseline Risk (with Stale Covariance)
    from oure.core.models import ConjunctionEvent

    event_baseline = ConjunctionEvent(
        primary_id=primary,
        secondary_id=secondary,
        tca=tca,
        miss_distance_km=miss,
        relative_velocity_km_s=v_rel,
        primary_state=p_tca,
        secondary_state=s_tca,
        primary_covariance=p_cov,
        secondary_covariance=s_cov_stale,
    )
    baseline_risk = risk_calc.compute_pc(event_baseline)

    # 2. Simulate Sensor Update via Kalman Filter
    simulator = SensorTaskingSimulator(sensor_noise_m=sensor_noise_m)
    s_cov_updated = simulator.simulate_radar_update(s_cov_stale)

    event_updated = ConjunctionEvent(
        primary_id=primary,
        secondary_id=secondary,
        tca=tca,
        miss_distance_km=miss,
        relative_velocity_km_s=v_rel,
        primary_state=p_tca,
        secondary_state=s_tca,
        primary_covariance=p_cov,
        secondary_covariance=s_cov_updated,
    )
    updated_risk = risk_calc.compute_pc(event_updated)

    console.print(
        Panel(
            f"Simulating Commercial Radar Tasking against [highlight]{secondary}[/highlight] (Accuracy: {sensor_noise_m}m)",
            border_style="cyan",
        )
    )

    table = Table(title="Covariance & Risk Update (EKF)", box=None)
    table.add_column("Metric", style="info")
    table.add_column("Before Radar Track", style="danger", justify="right")
    table.add_column("After Radar Track", style="success", justify="right")

    table.add_row(
        "Pos. Uncertainty (Trace)",
        f"{np.trace(s_cov_stale.matrix[:3, :3]):.2f} km²",
        f"{np.trace(s_cov_updated.matrix[:3, :3]):.5f} km²",
    )
    table.add_row(
        "B-Plane σ_x",
        f"{baseline_risk.b_plane_sigma_x:.3f} km",
        f"{updated_risk.b_plane_sigma_x:.3f} km",
    )
    table.add_row(
        "Probability of Collision", f"{baseline_risk.pc:.2e}", f"{updated_risk.pc:.2e}"
    )
    # Map warning levels to theme styles
    style_map = {"RED": "danger", "YELLOW": "warning", "GREEN": "success"}
    b_style = style_map.get(baseline_risk.warning_level, "white")
    u_style = style_map.get(updated_risk.warning_level, "white")

    table.add_row(
        "Alert Level",
        f"[{b_style}]{baseline_risk.warning_level}[/]",
        f"[{u_style}]{updated_risk.warning_level}[/]",
    )

    console.print(table)

    if updated_risk.warning_level != baseline_risk.warning_level:
        UI.success(
            f"Radar tasking successfully downgraded risk to [bold]{updated_risk.warning_level}[/bold]. Maneuver aborted."
        )
    else:
        console.print(
            f"\n[warning]WARNING: Radar tasking did not change the alert tier. Alert remains {updated_risk.warning_level}. Proceed to maneuver analysis.[/warning]"
        )
