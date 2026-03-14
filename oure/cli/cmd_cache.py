"""
OURE CLI - Cache Command
========================
"""

import sqlite3

import click

from .main import OUREContext, cli
from .utils import UI, console


@cli.command()
@click.option("--status", is_flag=True, help="Show cache statistics.")
@click.option("--clear", is_flag=True, help="Clear all cached data.")
@click.option("--clear-tles", is_flag=True, help="Clear only TLE records.")
@click.pass_context
def cache(ctx: click.Context, status: bool, clear: bool, clear_tles: bool) -> None:
    """
    Manage the local SQLite data cache.
    """
    oure_ctx: OUREContext = ctx.obj
    db_path = oure_ctx.cache.db_path
    UI.header("Cache Management", f"Database: {db_path}")

    if not db_path.exists():
        UI.error(f"Cache database not found at: {db_path}")
        return

    if status:
        with sqlite3.connect(db_path) as conn:
            try:
                n_tles = conn.execute("SELECT COUNT(*) FROM tle_records").fetchone()[0]
                n_cache = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
                n_risk = conn.execute("SELECT COUNT(*) FROM risk_history").fetchone()[0]
                db_size = db_path.stat().st_size / 1024
            except sqlite3.OperationalError as e:
                UI.error(f"Error reading cache: {e}")
                return

        from rich.table import Table
        table = Table(title="Database Statistics", box=None)
        table.add_column("Category", style="info")
        table.add_column("Count / Size", justify="right", style="success")

        table.add_row("TLE Records", f"{n_tles:,}")
        table.add_row("API Cache Entries", f"{n_cache:,}")
        table.add_row("Risk History Logs", f"{n_risk:,}")
        table.add_row("Total DB Size", f"{db_size:.1f} KB")
        console.print(table)

    elif clear:
        if click.confirm("WARNING: [danger]This will delete ALL cached data and risk logs. Continue?[/danger]", default=False):
            with sqlite3.connect(db_path) as conn:
                conn.execute("DELETE FROM tle_records")
                conn.execute("DELETE FROM cache_entries")
                conn.execute("DELETE FROM risk_history")
            UI.success("All cache and history tables cleared.")

    elif clear_tles:
        if click.confirm("WARNING: [warning]Delete all TLE records?[/warning]", default=False):
            with sqlite3.connect(db_path) as conn:
                conn.execute("DELETE FROM tle_records")
            UI.success("TLE records cleared.")
