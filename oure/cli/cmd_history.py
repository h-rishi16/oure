"""
OURE CLI - History Command (Risk Evolution)
===========================================
"""

import sys
from typing import Any, cast
from pathlib import Path

import click
import plotly.graph_objects as go
from rich.console import Console
from rich.table import Table

from .main import cli, OUREContext

console = Console()

@cli.command()
@click.option("--primary", "-p", required=True, help="NORAD ID of the primary satellite.")
@click.option("--secondary", "-s", required=True, help="NORAD ID of the secondary satellite.")
@click.option("--output", "-o", type=click.Path(), default="risk_history.html", help="Output HTML file path.")
@click.pass_context
def history(ctx: click.Context, primary: str, secondary: str, output: str) -> None:
    """
    Plot the historical evolution of collision risk (Pc) for a specific conjunction pair.
    """
    oure_ctx: OUREContext = ctx.obj

    records = oure_ctx.cache.get_risk_history(primary, secondary)

    if not records:
        console.print(f"[yellow]No historical risk data found in the database for {primary} vs {secondary}.[/yellow]")
        console.print("[dim]Run `oure monitor` first to populate the history database.[/dim]")
        sys.exit(0)

    console.print(f"[cyan]Found {len(records)} historical risk evaluations for {primary} vs {secondary}.[/cyan]")

    table = Table(title="Recent Risk Evaluations")
    table.add_column("Evaluation Time", style="blue")
    table.add_column("TCA", style="green")
    table.add_column("Miss (km)", justify="right")
    table.add_column("Pc", justify="right", style="bold")
    table.add_column("Level", justify="center")

    eval_times = []
    pcs = []
    miss_dists = []
    levels = []

    for r_raw in records[-10:]: # Print last 10
        r = cast(dict[str, Any], r_raw)
        color = "green" if r['warning_level'] == "GREEN" else ("yellow" if r['warning_level'] == "YELLOW" else "red")
        table.add_row(
            str(r['evaluation_time'])[:19].replace("T", " "),
            str(r['tca'])[:19].replace("T", " "),
            f"{r['miss_distance_km']:.3f}",
            f"[{color}]{r['pc']:.2e}[/{color}]",
            f"[{color}]{r['warning_level']}[/{color}]"
        )

    for r_raw in records:
        r = cast(dict[str, Any], r_raw)
        eval_times.append(r['evaluation_time'])
        pcs.append(r['pc'])
        miss_dists.append(r['miss_distance_km'])
        levels.append(r['warning_level'])

    console.print(table)

    # Generate Plotly Chart
    fig = go.Figure()

    # Plot Pc on left Y-axis
    fig.add_trace(go.Scatter(
        x=eval_times, y=pcs,
        mode='lines+markers',
        name='Probability of Collision (Pc)',
        line=dict(color='red', width=3),
        marker=dict(size=8, symbol='circle')
    ))

    # Add Risk Threshold Lines
    fig.add_hline(y=1e-3, line_dash="dash", line_color="red", annotation_text="RED Alert (1e-3)")
    fig.add_hline(y=1e-5, line_dash="dash", line_color="orange", annotation_text="YELLOW Alert (1e-5)")

    fig.update_layout(
        title=f"Risk Evolution History: {primary} vs {secondary}",
        xaxis_title="Evaluation Time (UTC)",
        yaxis_title="Probability of Collision (Pc)",
        yaxis_type="log",
        yaxis=dict(range=[-8, 0]),  # 1e-8 to 1.0
        plot_bgcolor="white",
        xaxis_showgrid=True, xaxis_gridcolor='lightgrey',
        yaxis_showgrid=True, yaxis_gridcolor='lightgrey',
        hovermode="x unified"
    )

    out_path = Path(output)
    fig.write_html(str(out_path))
    console.print(f"\n[bold green]✓ Interactive Risk Evolution plot saved to {out_path.absolute()}[/bold green]")
