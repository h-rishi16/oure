"""
OURE Command-Line Interface - Main Entry Point
==============================================
"""

from pathlib import Path

import click
import click_completion

click_completion.init()

from oure.core.logging_config import LogFormat, configure_logging
from oure.data.cache import CacheManager
from oure.data.noaa import NOAASolarFluxFetcher
from oure.data.spacetrack import SpaceTrackFetcher

# setup_logging removed — configure_logging() from logging_config is used instead


class OUREContext:
    """Holds shared configuration and service instances."""

    def __init__(
        self, st_username: str, st_password: str, db_path: Path | None, verbose: bool
    ):
        self.cache = CacheManager(db_path=db_path)
        self.tle_fetcher = SpaceTrackFetcher(
            username=st_username, password=st_password, cache=self.cache
        )
        self.flux_fetcher = NOAASolarFluxFetcher(cache=self.cache)
        self.verbose = verbose


@click.group()
@click.option(
    "--st-username",
    envvar="SPACETRACK_USER",
    required=False,
    help="Space-Track.org username (or set $SPACETRACK_USER)",
)
@click.option(
    "--st-password",
    envvar="SPACETRACK_PASS",
    required=False,
    help="Space-Track.org password (or set $SPACETRACK_PASS)",
)
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path to SQLite cache database (default: ~/.oure/cache.db)",
)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.option("--log-file", type=click.Path(), default=None)
@click.version_option(version="1.0.0", prog_name="OURE")
@click.pass_context
def cli(
    ctx: click.Context,
    st_username: str,
    st_password: str,
    db_path: str | None,
    verbose: bool,
    log_file: str | None,
) -> None:
    """
    ╔══════════════════════════════════════════════╗
    ║   OURE --- Orbital Uncertainty & Risk Engine   ║
    ║    Satellite Collision Probability Solver    ║
    ╚══════════════════════════════════════════════╝
    """
    import os

    fmt = (
        LogFormat.CONSOLE
        if not os.getenv("OURE_LOG_FORMAT") == "json"
        else LogFormat.JSON
    )
    configure_logging(
        level="DEBUG" if verbose else "INFO", format=fmt, log_file=log_file
    )

    ctx.ensure_object(dict)
    ctx.obj = OUREContext(
        st_username=st_username,
        st_password=st_password,
        db_path=Path(db_path) if db_path else None,
        verbose=verbose,
    )


@cli.command()
@click.option(
    "--append/--overwrite",
    help="Append the completion script to your shell profile or overwrite it.",
    default=None,
)
@click.argument(
    "shell",
    required=False,
    type=click_completion.DocumentedChoice(click_completion.core.shells),
)
def install_completion(append: bool | None, shell: str | None) -> None:
    """Install the shell completion script for your current shell."""
    shell, path = click_completion.core.install(shell=shell, append=append)
    from .utils import console

    console.print(
        f"[success]DONE[/success] [info]{shell}[/info] completion installed in [info]{path}[/info]"
    )


# Import commands to register them with the CLI group
from . import (  # noqa: F401
    cmd_analyze,
    cmd_avoid,
    cmd_cache,
    cmd_cdm,
    cmd_fetch,
    cmd_fleet,
    cmd_history,
    cmd_monitor,
    cmd_plot,
    cmd_report,
    cmd_sensor,
    cmd_shatter,
)

if __name__ == "__main__":
    cli(auto_envvar_prefix="OURE")
