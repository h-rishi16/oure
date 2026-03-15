"""
OURE Command-Line Interface - Main Entry Point
==============================================
"""

import logging
import sys
from pathlib import Path

import click
import click_completion

click_completion.init()

from oure.data.cache import CacheManager
from oure.data.noaa import NOAASolarFluxFetcher
from oure.data.spacetrack import SpaceTrackFetcher


def setup_logging(verbose: bool, log_file: str | None = None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )


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
    required=True,
    help="Space-Track.org username (or set $SPACETRACK_USER)",
)
@click.option(
    "--st-password",
    envvar="SPACETRACK_PASS",
    required=True,
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
    setup_logging(verbose, log_file)
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

if __name__ == "__main__":
    cli(auto_envvar_prefix="OURE")
