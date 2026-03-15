"""
OURE CLI - Avoid Command (Interactive Wizard)
=============================================
"""

import sys
from datetime import timedelta

import click
import numpy as np
from rich.prompt import Confirm, Prompt

from oure.conjunction.tca_finder import TCARefinementEngine
from oure.core.models import ConjunctionEvent
from oure.physics.maneuver import Maneuver, ManeuverPropagator
from oure.physics.numerical import NumericalPropagator
from oure.risk.calculator import RiskCalculator
from oure.risk.optimizer import ManeuverOptimizer

from .main import OUREContext, cli
from .utils import (
    UI,
    _default_covariance,
    _tle_to_initial_state,
    console,
)


@cli.command()
@click.option("--primary", "-p", help="NORAD ID of the primary satellite.")
@click.option("--secondary", "-s", help="NORAD ID of the secondary satellite.")
@click.option(
    "--burn-time-before-tca", type=float, help="Hours before TCA to execute burn."
)
@click.option(
    "--optimize", is_flag=True, default=False, help="Run the SLSQP optimizer."
)
@click.pass_context
def avoid(
    ctx: click.Context,
    primary: str | None,
    secondary: str | None,
    burn_time_before_tca: float | None,
    optimize: bool,
) -> None:
    """
    Collision avoidance maneuver analysis. If arguments are missing, starts the interactive Wizard.
    """
    oure_ctx: OUREContext = ctx.obj
    UI.header("Maneuver Analysis Wizard", "Optimizing collision avoidance trajectories")

    # Interactive Wizard Mode
    if not primary:
        primary = Prompt.ask("[info]Enter Primary NORAD ID[/info]")
    if not secondary:
        secondary = Prompt.ask("[info]Enter Secondary NORAD ID[/info]")

    assert primary is not None
    assert secondary is not None

    if burn_time_before_tca is None:
        burn_time_before_tca = float(
            Prompt.ask("[info]Hours before TCA to execute burn?[/info]", default="12.0")
        )

    with console.status("[bold cyan]Fetching current orbital data...") as status:
        try:
            records = {
                r.sat_id: r
                for r in oure_ctx.tle_fetcher.fetch(sat_ids=[primary, secondary])
            }
            flux = oure_ctx.flux_fetcher.get_current_f107()
        except Exception as e:
            UI.error(
                f"Data ingestion failed: {e}",
                "Check your internet connection and Space-Track credentials.",
            )
            sys.exit(1)

    if primary not in records or secondary not in records:
        UI.error(f"Satellite data missing for {primary} or {secondary}.")
        sys.exit(1)

    primary_tle = records[primary]
    secondary_tle = records[secondary]

    p_state = _tle_to_initial_state(primary_tle)
    s_state = _tle_to_initial_state(secondary_tle)
    p_cov = _default_covariance(primary_tle.sat_id)
    s_cov = _default_covariance(secondary_tle.sat_id)

    # Baseline Assessment
    with console.status(
        "[bold cyan]Running baseline High-Precision propagation..."
    ) as status:
        base_prop = NumericalPropagator(solar_flux=flux)
        tca_finder = TCARefinementEngine()
        search_start = p_state.epoch
        search_end = search_start + timedelta(hours=72)
        tca_result = tca_finder.find_tca(
            p_state, base_prop, s_state, base_prop, search_start, search_end
        )

    if not tca_result:
        UI.success(
            "No conjunction detected in baseline trajectory. No maneuver required."
        )
        return

    nominal_tca, nominal_miss = tca_result
    p_tca_state = base_prop.propagate_to(p_state, nominal_tca)
    s_tca_state = base_prop.propagate_to(s_state, nominal_tca)
    v_rel = float(np.linalg.norm(p_tca_state.v - s_tca_state.v))

    nominal_event = ConjunctionEvent(
        primary_id=primary,
        secondary_id=secondary,
        tca=nominal_tca,
        miss_distance_km=nominal_miss,
        relative_velocity_km_s=v_rel,
        primary_state=p_tca_state,
        secondary_state=s_tca_state,
        primary_covariance=p_cov,
        secondary_covariance=s_cov,
    )

    risk_calc = RiskCalculator()
    nominal_risk = risk_calc.compute_pc(nominal_event)

    console.print(
        f"\n[info]Baseline TCA:[/info] {nominal_tca.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    console.print(f"[info]Baseline Miss:[/info] [bold]{nominal_miss:.3f} km[/bold]")
    console.print(
        f"[info]Baseline Pc:[/info]   [danger]{nominal_risk.pc:.2e}[/danger]\n"
    )

    burn_epoch = nominal_tca - timedelta(hours=burn_time_before_tca)

    # Optimization Path
    if optimize or Confirm.ask(
        "[highlight]Run mathematical optimization for minimum-fuel burn?[/highlight]"
    ):
        with console.status(
            f"[bold magenta]Optimizing 3D thrust vector for T-{burn_time_before_tca}h..."
        ) as status:
            optimizer = ManeuverOptimizer(
                base_prop=base_prop,
                primary_state=p_state,
                secondary_state=s_state,
                primary_cov=p_cov,
                secondary_cov=s_cov,
                burn_epoch=burn_epoch,
                target_pc=1e-5,
            )
            result = optimizer.optimize()

        if result["success"]:
            dv = result["optimal_dv_km_s"]
            UI.success(
                f"Minimum fuel maneuver found: [bold cyan]{result['dv_mag_cm_s']:.3f} cm/s[/bold cyan]"
            )
            console.print(f"[dim]Vector (ECI km/s): {dv}[/dim]")
            console.print(
                f"[success]Final Pc:[/success] {result['final_pc']:.2e} (Target: 1.00e-05)"
            )
        else:
            UI.error(f"Optimization failed: {result['message']}")

    else:
        # Trade Space Path
        test_dvs_cm_s = [-5.0, -1.0, -0.5, -0.1, 0.1, 0.5, 1.0, 5.0]
        from rich.table import Table

        table = Table(
            title=f"Maneuver Trade Space (Burn at T-{burn_time_before_tca}h)", box=None
        )
        table.add_column("dV (cm/s)", justify="right", style="cyan")
        table.add_column("Direction", style="blue")
        table.add_column("New Miss (km)", justify="right")
        table.add_column("New Pc", justify="right")
        table.add_column("Outcome", justify="center")

        with console.status("[bold cyan]Simulating trade space...") as status:
            burn_state = base_prop.propagate_to(p_state, burn_epoch)
            v_hat = burn_state.v / np.linalg.norm(burn_state.v)

            for dv_cm in test_dvs_cm_s:
                dv_km_s = (dv_cm / 100.0) / 1000.0
                maneuver = Maneuver(burn_epoch=burn_epoch, delta_v_eci=v_hat * dv_km_s)
                man_prop = ManeuverPropagator(
                    base_propagator=base_prop, maneuvers=[maneuver]
                )

                new_tca_res = tca_finder.find_tca(
                    p_state,
                    man_prop,
                    s_state,
                    base_prop,
                    burn_epoch,
                    nominal_tca + timedelta(hours=2),
                )

                if new_tca_res:
                    new_tca, new_miss = new_tca_res
                    p_new_tca = man_prop.propagate_to(p_state, new_tca)
                    s_new_tca = base_prop.propagate_to(s_state, new_tca)
                    new_risk = risk_calc.compute_pc(
                        ConjunctionEvent(
                            primary_id=primary,
                            secondary_id=secondary,
                            tca=new_tca,
                            miss_distance_km=new_miss,
                            relative_velocity_km_s=float(
                                np.linalg.norm(p_new_tca.v - s_new_tca.v)
                            ),
                            primary_state=p_new_tca,
                            secondary_state=s_new_tca,
                            primary_covariance=p_cov,
                            secondary_covariance=s_cov,
                        )
                    )

                    status_str = (
                        "[success]SAFE[/success]"
                        if new_risk.warning_level == "GREEN"
                        else "[danger]RISK[/danger]"
                    )
                    table.add_row(
                        f"{dv_cm:+.1f}",
                        "Prograde" if dv_cm > 0 else "Retrograde",
                        f"{new_miss:.3f}",
                        f"{new_risk.pc:.2e}",
                        status_str,
                    )

        console.print(table)
