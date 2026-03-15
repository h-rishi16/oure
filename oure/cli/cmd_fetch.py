"""
OURE CLI - Fetch Command
========================
"""

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.table import Table

from .main import OUREContext, cli
from .utils import UI, console


def _approx_altitude(mean_motion_rev_day: float) -> float:
    """Quick altitude estimate from mean motion."""
    from oure.core import constants

    n = mean_motion_rev_day * constants.TWO_PI / constants.SECONDS_PER_DAY
    a = (constants.MU_KM3_S2 / n**2) ** (1 / 3) if n > 0 else constants.R_EARTH_KM + 400
    return a - constants.R_EARTH_KM


def _save_tles_to_json(records: list[Any], path: Path) -> None:
    output = [
        {
            "sat_id": r.sat_id,
            "name": r.name,
            "line1": r.line1,
            "line2": r.line2,
            "epoch": r.epoch.isoformat(),
        }
        for r in records
    ]
    with open(path, "w") as f:
        json.dump(output, f, indent=2)


@cli.command()
@click.option(
    "--sat-id",
    "-s",
    multiple=True,
    required=False,
    help="NORAD catalog ID(s) to fetch. Repeat for multiple.",
)
@click.option(
    "--all-leo",
    is_flag=True,
    default=False,
    help="Fetch all catalogued LEO objects (may be slow).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Save TLEs to JSON file (optional).",
)
@click.option(
    "--force-refresh",
    is_flag=True,
    default=False,
    help="Bypass cache and fetch fresh from Space-Track.",
)
@click.pass_context
def fetch(
    ctx: click.Context,
    sat_id: tuple[str, ...],
    all_leo: bool,
    output: str | None,
    force_refresh: bool,
) -> None:
    """
    Fetch TLE data from Space-Track.org and F10.7 flux from NOAA.
    """
    oure_ctx: OUREContext = ctx.obj
    UI.header("Data Ingestion Engine", "Syncing orbital catalogs and space weather")

    with console.status("[bold cyan]Fetching solar flux from NOAA...") as status:
        flux_data = oure_ctx.flux_fetcher.fetch()
        if flux_data:
            f = flux_data[0]
            console.print(
                f"   [info]F10.7 = {f.f10_7:.1f} sfu[/info]  (Date: {f.date.strftime('%Y-%m-%d')})"
            )

    ids_to_fetch = list(sat_id) if sat_id else None
    if all_leo:
        console.print("[info]Fetching all LEO catalog objects...[/info]")
        ids_to_fetch = None
    elif ids_to_fetch:
        console.print(
            f"[info]Fetching TLEs for {len(ids_to_fetch)} satellite(s)...[/info]"
        )

    if not ids_to_fetch and not all_leo:
        UI.error("No satellites specified.", "Use --sat-id or --all-leo.")
        return

    try:
        with console.status("[bold cyan]Querying Space-Track API...") as status:
            records = oure_ctx.tle_fetcher.fetch(
                sat_ids=ids_to_fetch, force_refresh=force_refresh
            )
    except Exception as e:
        UI.error(f"Critical Fetch Error: {e}")
        sys.exit(1)

    UI.success(f"Processed {len(records)} TLE records.")

    table = Table(title="Satellite Inventory", box=None, border_style="dim")
    table.add_column("SAT ID", style="info")
    table.add_column("NAME", style="highlight")
    table.add_column("INCLINATION", justify="right", style="success")
    table.add_column("EST. ALTITUDE", justify="right", style="success")

    for r in records[:10]:
        table.add_row(
            str(r.sat_id),
            str(r.name),
            f"{r.inclination_deg:.2f}°",
            f"~{_approx_altitude(r.mean_motion_rev_per_day):.0f} km",
        )
    console.print(table)

    if len(records) > 10:
        console.print(f"[dim]... and {len(records)-10} more satellites hidden.[/dim]")

    if output:
        _save_tles_to_json(records, Path(output))
        UI.success(f"TLEs Saved to {output}")
