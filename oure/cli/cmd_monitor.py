"""
OURE CLI - Monitor Command
==========================
"""

import time
from datetime import UTC, datetime

import click
from rich.console import Console

from .cmd_analyze import analyze
from .main import cli

console = Console()

@cli.command()
@click.option("--primary", "-p", required=True)
@click.option("--secondaries-file", type=click.Path(exists=True), required=True)
@click.option("--alert-threshold", default=1e-5, show_default=True,
              help="Pc threshold to trigger RED alert (default: 1e-5)")
@click.option("--interval", default=3600, show_default=True,
              help="Re-evaluation interval in seconds (default: 1 hour)")
@click.option("--max-runs", default=None, type=int,
              help="Stop after N evaluations (omit for continuous)")
@click.pass_context
def monitor(ctx: click.Context, primary: str, secondaries_file: str, alert_threshold: float, interval: int, max_runs: int | None) -> None:
    """
    Continuous conjunction monitoring with configurable alert thresholds.
    """
    run_count = 0

    console.print(f"\n[bold blue]🛡️  OURE Monitor — Primary: {primary}[/bold blue]")
    console.print(f"   Alert threshold: Pc ≥ {alert_threshold:.0e}")
    console.print(f"   Re-evaluation: every {interval}s\n")
    console.print("   [dim]Press Ctrl-C to stop.[/dim]\n")

    try:
        while True:
            run_count += 1
            timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
            console.print(f"[cyan][{timestamp}] Run #{run_count}  — invoking ctx.invoke(analyze)...[/cyan]")

            results = ctx.invoke(
                analyze,
                primary=primary,
                secondary=[],
                secondaries_file=secondaries_file,
                look_ahead=72.0,
                screening_dist=5.0,
                mc_samples=500,
                hard_body_radius=20.0,
                output=None
            )

            if results:
                for r in results:
                    ctx.obj.cache.log_risk_event(
                        primary_id=r.conjunction.primary_id,
                        secondary_id=r.conjunction.secondary_id,
                        tca=r.conjunction.tca,
                        pc=r.pc,
                        miss_distance_km=r.conjunction.miss_distance_km,
                        warning_level=r.warning_level
                    )
                console.print(f"[dim]Logged {len(results)} events to risk history database.[/dim]")

            if max_runs and run_count >= max_runs:
                console.print("\n[bold green]Max runs reached. Exiting monitor.[/bold green]")
                break

            console.print(f"\n   [dim]⏱  Next evaluation in {interval}s...[/dim]\n")
            time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Monitor stopped by user.[/bold yellow]")

