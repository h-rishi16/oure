
"""
OURE CLI - Cache Command
========================
"""

import sqlite3

import click
from rich.console import Console

from .main import OUREContext, cli

console = Console()

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

    if not db_path.exists():
        console.print(f"[yellow]Cache database not found at: {db_path}[/yellow]")
        return

    if status:
        console.print(f"\n[bold blue]📦 Cache Status — {db_path}[/bold blue]")
        with sqlite3.connect(db_path) as conn:
            try:
                n_tles = conn.execute("SELECT COUNT(*) FROM tle_records").fetchone()[0]
                n_cache = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
                db_size = db_path.stat().st_size / 1024
            except sqlite3.OperationalError as e:
                console.print(f"[bold red]Error reading cache: {e}[/bold red]")
                return

        console.print(f"   [cyan]TLE records[/cyan]   : {n_tles:,}")
        console.print(f"   [cyan]Cache entries[/cyan] : {n_cache:,}")
        console.print(f"   [cyan]Database size[/cyan] : {db_size:.1f} KB")

    elif clear:
        click.confirm("⚠  This will delete all cached data. Continue?", abort=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM tle_records")
            conn.execute("DELETE FROM cache_entries")
        console.print("[bold green]✓ Cache cleared.[/bold green]")

    elif clear_tles:
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM tle_records")
        console.print("[bold green]✓ TLE records cleared.[/bold green]")

