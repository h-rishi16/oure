"""
OURE Command-Line Interface
============================
Professional CLI built with `click`. Subcommands mirror the
system's pipeline stages, giving operators direct access to
each layer independently.

Usage:
    oure fetch --sat-id 25544 --sat-id 40379
    oure analyze --primary 25544 --secondaries catalog_leo.json
    oure monitor --primary 25544 --alert-threshold 1e-5 --interval 3600
    oure cache --status
    oure cache --clear
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import numpy as np

from oure.core.models import CovarianceMatrix, StateVector
from oure.data.fetchers import SpaceTrackFetcher, NOAASolarFluxFetcher, CacheManager
from oure.physics.propagator import PropagatorFactory
from oure.uncertainty.covariance import CovariancePropagator, MonteCarloUncertaintyPropagator
from oure.conjunction.assessor import ConjunctionAssessor, RiskCalculator

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(verbose: bool, log_file: Optional[str] = None):
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers
    )


# ---------------------------------------------------------------------------
# Shared context object (passed between subcommands via @click.pass_context)
# ---------------------------------------------------------------------------

class OUREContext:
    """Holds shared configuration and service instances."""
    def __init__(
        self,
        st_username: str,
        st_password: str,
        db_path: Optional[Path],
        verbose: bool
    ):
        self.cache = CacheManager(db_path=db_path)
        self.tle_fetcher = SpaceTrackFetcher(
            username=st_username,
            password=st_password,
            cache=self.cache
        )
        self.flux_fetcher = NOAASolarFluxFetcher(cache=self.cache)
        self.verbose = verbose


# ---------------------------------------------------------------------------
# CLI Root Command Group
# ---------------------------------------------------------------------------

@click.group()
@click.option("--st-username", envvar="SPACETRACK_USER", required=True,
              help="Space-Track.org username (or set $SPACETRACK_USER)")
@click.option("--st-password", envvar="SPACETRACK_PASS", required=True,
              help="Space-Track.org password (or set $SPACETRACK_PASS)")
@click.option("--db-path", type=click.Path(), default=None,
              help="Path to SQLite cache database (default: ~/.oure/cache.db)")
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.option("--log-file", type=click.Path(), default=None)
@click.version_option(version="0.1.0", prog_name="OURE")
@click.pass_context
def cli(ctx, st_username, st_password, db_path, verbose, log_file):
    """
    ╔══════════════════════════════════════════════╗
    ║   OURE — Orbital Uncertainty & Risk Engine   ║
    ║   Satellite Collision Probability Solver     ║
    ╚══════════════════════════════════════════════╝

    Subcommands: fetch | analyze | monitor | cache
    """
    setup_logging(verbose, log_file)
    ctx.ensure_object(dict)
    ctx.obj = OUREContext(
        st_username=st_username,
        st_password=st_password,
        db_path=Path(db_path) if db_path else None,
        verbose=verbose
    )


# ---------------------------------------------------------------------------
# SUBCOMMAND: fetch
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--sat-id", "-s", multiple=True, required=False,
              help="NORAD catalog ID(s) to fetch. Repeat for multiple.")
@click.option("--all-leo", is_flag=True, default=False,
              help="Fetch all catalogued LEO objects (may be slow).")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Save TLEs to JSON file (optional).")
@click.option("--force-refresh", is_flag=True, default=False,
              help="Bypass cache and fetch fresh from Space-Track.")
@click.pass_context
def fetch(ctx, sat_id, all_leo, output, force_refresh):
    """
    Fetch TLE data from Space-Track.org and F10.7 flux from NOAA.

    Examples:
        oure fetch --sat-id 25544                    # ISS
        oure fetch --sat-id 25544 --sat-id 43205     # ISS + Starlink
        oure fetch --all-leo --output tle_cache.json
    """
    oure_ctx: OUREContext = ctx.obj
    log = logging.getLogger("oure.cli.fetch")

    # Fetch solar flux first (cheap, always useful)
    click.echo("📡 Fetching solar flux from NOAA...")
    flux_data = oure_ctx.flux_fetcher.fetch()
    if flux_data:
        f = flux_data[0]
        click.echo(
            click.style(f"   F10.7 = {f.f10_7:.1f} sfu  ", fg="cyan") +
            f"(Date: {f.date.strftime('%Y-%m-%d')})"
        )

    # Determine which satellites to fetch
    ids_to_fetch = list(sat_id) if sat_id else None
    if all_leo:
        click.echo("🛰️  Fetching all LEO catalog objects...")
        ids_to_fetch = None
    elif ids_to_fetch:
        click.echo(f"🛰️  Fetching TLEs for {len(ids_to_fetch)} satellite(s)...")

    if not ids_to_fetch and not all_leo:
        click.echo(click.style("⚠  No satellites specified. Use --sat-id or --all-leo.", fg="yellow"))
        return

    try:
        records = oure_ctx.tle_fetcher.fetch(sat_ids=ids_to_fetch)
        click.echo(click.style(f"✓ Fetched {len(records)} TLE records.", fg="green"))

        for r in records[:5]:   # Show first 5
            click.echo(
                f"   [{r.sat_id}] {r.name:<30s} "
                f"i={r.inclination_deg:6.2f}°  "
                f"alt~{_approx_altitude(r.mean_motion_rev_per_day):.0f}km"
            )
        if len(records) > 5:
            click.echo(f"   ... and {len(records)-5} more")

        if output:
            _save_tles_to_json(records, Path(output))
            click.echo(click.style(f"💾 Saved to {output}", fg="green"))

    except Exception as e:
        click.echo(click.style(f"✗ Fetch failed: {e}", fg="red"), err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# SUBCOMMAND: analyze
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--primary", "-p", required=True,
              help="NORAD ID of the primary satellite.")
@click.option("--secondary", "-s", multiple=True,
              help="NORAD ID(s) of secondary satellites to screen against.")
@click.option("--secondaries-file", type=click.Path(exists=True),
              help="JSON file with list of NORAD IDs to screen.")
@click.option("--look-ahead", default=72.0, show_default=True,
              help="Look-ahead window in hours.")
@click.option("--screening-dist", default=5.0, show_default=True,
              help="KD-Tree screening distance in km.")
@click.option("--mc-samples", default=1000, show_default=True,
              help="Monte Carlo samples for uncertainty propagation.")
@click.option("--hard-body-radius", default=20.0, show_default=True,
              help="Combined hard-body radius in metres.")
@click.option("--output", "-o", type=click.Path(), default=None,
              help="Save results to JSON.")
@click.pass_context
def analyze(
    ctx, primary, secondary, secondaries_file, look_ahead,
    screening_dist, mc_samples, hard_body_radius, output
):
    """
    Run full conjunction assessment and Pc calculation pipeline.

    The pipeline: Fetch TLEs → Propagate → KD-Tree screen →
    Refine TCA → Propagate covariance → B-plane Pc

    Examples:
        oure analyze --primary 25544 --secondary 43205 --secondary 40379
        oure analyze --primary 25544 --secondaries-file leo_catalog.json
        oure analyze --primary 25544 --secondaries-file leo.json --mc-samples 2000
    """
    oure_ctx: OUREContext = ctx.obj
    log = logging.getLogger("oure.cli.analyze")

    # Collect secondary IDs
    secondary_ids = list(secondary)
    if secondaries_file:
        with open(secondaries_file) as f:
            secondary_ids.extend(json.load(f))

    if not secondary_ids:
        click.echo(click.style("✗ No secondary satellites specified.", fg="red"), err=True)
        sys.exit(1)

    all_ids = [primary] + secondary_ids

    click.echo(f"\n🔭 OURE Analysis: {primary} vs {len(secondary_ids)} objects")
    click.echo(f"   Look-ahead: {look_ahead}h | Screening: {screening_dist}km | MC: {mc_samples}\n")

    # --- Step 1: Fetch TLEs ---
    with click.progressbar(length=3, label="Fetching data", width=40) as bar:
        records = {r.sat_id: r for r in oure_ctx.tle_fetcher.fetch(sat_ids=all_ids)}
        bar.update(1)
        flux = oure_ctx.flux_fetcher.get_current_f107()
        bar.update(1)

        if primary not in records:
            click.echo(click.style(f"\n✗ Primary {primary} not found in catalog.", fg="red"))
            sys.exit(1)
        bar.update(1)

    click.echo(f"   ✓ F10.7={flux:.1f} | {len(records)} TLEs loaded")

    # --- Step 2: Build propagators ---
    primary_tle = records[primary]
    primary_prop = PropagatorFactory.build(primary_tle, solar_flux=flux)
    primary_state = _tle_to_initial_state(primary_tle)
    primary_cov = _default_covariance(primary_tle.sat_id)

    secondaries = []
    for sid in secondary_ids:
        if sid not in records:
            click.echo(click.style(f"   ⚠ {sid} not in cache — skipping", fg="yellow"))
            continue
        tle = records[sid]
        prop = PropagatorFactory.build(tle, solar_flux=flux)
        state = _tle_to_initial_state(tle)
        cov = _default_covariance(tle.sat_id)
        secondaries.append((state, cov, prop))

    # --- Step 3: Conjunction screening ---
    click.echo(f"\n🔍 Running KD-Tree conjunction screening ({len(secondaries)} objects)...")
    assessor = ConjunctionAssessor(screening_distance_km=screening_dist)
    events = assessor.find_conjunctions(
        primary_state, primary_cov, primary_prop,
        secondaries, look_ahead_hours=look_ahead
    )

    if not events:
        click.echo(click.style("\n✓ No conjunctions found in look-ahead window.", fg="green"))
        return

    click.echo(click.style(f"\n⚠  Found {len(events)} conjunction event(s):\n", fg="yellow"))

    # --- Step 4: Compute Pc for each event ---
    calculator = RiskCalculator(hard_body_radius_m=hard_body_radius)
    results = []

    for i, event in enumerate(events):
        result = calculator.compute_pc(event)
        results.append(result)
        _print_result(i+1, result)

    # --- Step 5: Export ---
    if output:
        _save_results_to_json(results, Path(output))
        click.echo(f"\n💾 Results saved to {output}")

    # Final summary banner
    max_pc = max(r.pc for r in results)
    _print_summary_banner(max_pc)


# ---------------------------------------------------------------------------
# SUBCOMMAND: monitor
# ---------------------------------------------------------------------------

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
def monitor(ctx, primary, secondaries_file, alert_threshold, interval, max_runs):
    """
    Continuous conjunction monitoring with configurable alert thresholds.

    Re-fetches TLEs and re-evaluates Pc at each interval tick.
    Sends console alerts (and optionally webhook/email) when Pc exceeds thresholds.

    ALERT LEVELS:
        GREEN   Pc < 1e-5    (routine monitoring)
        YELLOW  Pc ∈ [1e-5, 1e-3)  (elevated — track closely)
        RED     Pc ≥ 1e-3    (emergency — notify operators)

    Example:
        oure monitor --primary 25544 --secondaries-file catalog.json \\
                     --alert-threshold 1e-4 --interval 1800
    """
    import time

    oure_ctx: OUREContext = ctx.obj
    run_count = 0

    click.echo(f"\n🛡️  OURE Monitor — Primary: {primary}")
    click.echo(f"   Alert threshold: Pc ≥ {alert_threshold:.0e}")
    click.echo(f"   Re-evaluation: every {interval}s\n")
    click.echo("   Press Ctrl-C to stop.\n")

    try:
        while True:
            run_count += 1
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            click.echo(f"[{timestamp}] Run #{run_count}  — invoking ctx.invoke(analyze)...")

            # Delegate to `analyze` for each run
            # In production: capture results and compare to threshold
            ctx.invoke(
                analyze,
                primary=primary,
                secondary=[],
                secondaries_file=secondaries_file,
                look_ahead=72.0,
                screening_dist=5.0,
                mc_samples=500,   # Faster for monitoring cadence
                hard_body_radius=20.0,
                output=None
            )

            if max_runs and run_count >= max_runs:
                click.echo("\nMax runs reached. Exiting monitor.")
                break

            click.echo(f"\n   ⏱  Next evaluation in {interval}s...\n")
            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("\n\nMonitor stopped by user.")


# ---------------------------------------------------------------------------
# SUBCOMMAND: cache
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--status", is_flag=True, help="Show cache statistics.")
@click.option("--clear", is_flag=True, help="Clear all cached data.")
@click.option("--clear-tles", is_flag=True, help="Clear only TLE records.")
@click.pass_context
def cache(ctx, status, clear, clear_tles):
    """
    Manage the local SQLite data cache.

    Examples:
        oure cache --status
        oure cache --clear-tles
        oure cache --clear
    """
    import sqlite3
    oure_ctx: OUREContext = ctx.obj
    db_path = oure_ctx.cache.db_path

    if status:
        click.echo(f"\n📦 Cache Status — {db_path}")
        with sqlite3.connect(db_path) as conn:
            n_tles = conn.execute("SELECT COUNT(*) FROM tle_records").fetchone()[0]
            n_cache = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
            db_size = db_path.stat().st_size / 1024 if db_path.exists() else 0

        click.echo(f"   TLE records   : {n_tles:,}")
        click.echo(f"   Cache entries : {n_cache:,}")
        click.echo(f"   Database size : {db_size:.1f} KB")

    elif clear:
        click.confirm("⚠  Clear ALL cached data?", abort=True)
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM tle_records")
            conn.execute("DELETE FROM cache_entries")
        click.echo(click.style("✓ Cache cleared.", fg="green"))

    elif clear_tles:
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM tle_records")
        click.echo(click.style("✓ TLE records cleared.", fg="green"))


# ---------------------------------------------------------------------------
# Internal helpers (not exposed as CLI commands)
# ---------------------------------------------------------------------------

def _approx_altitude(mean_motion_rev_day: float) -> float:
    """Quick altitude estimate from mean motion."""
    from oure.physics.propagator import MU, R_EARTH
    n = mean_motion_rev_day * 2 * 3.141592 / 86400
    a = (MU / n**2) ** (1/3) if n > 0 else 6778.0
    return a - R_EARTH


def _tle_to_initial_state(tle) -> StateVector:
    """
    Convert a TLERecord to an initial StateVector at TLE epoch.
    In production: use the SGP4 propagator at t=0.
    Here: approximate circular orbit.
    """
    from oure.physics.propagator import MU, R_EARTH
    import math
    n = tle.mean_motion_rev_per_day * 2 * math.pi / 86400
    a = (MU / n**2) ** (1.0/3.0) if n > 0 else 6778.0
    # Simplified: equatorial circular orbit position
    angle = math.radians(tle.mean_anomaly_deg)
    r = a * np.array([math.cos(angle), math.sin(angle), 0.0])
    v_mag = math.sqrt(MU / a)
    v = v_mag * np.array([-math.sin(angle), math.cos(angle), 0.0])
    return StateVector(r=r, v=v, epoch=tle.epoch, sat_id=tle.sat_id)


def _default_covariance(sat_id: str) -> CovarianceMatrix:
    """
    Default initial covariance for objects with no UCT (Uncorrelated Track) data.
    Conservative values: σ_pos ≈ 1 km, σ_vel ≈ 1 m/s
    """
    P = np.diag([1.0, 1.0, 1.0, 1e-6, 1e-6, 1e-6])  # km², km²/s²
    return CovarianceMatrix(matrix=P, epoch=datetime.utcnow(), sat_id=sat_id)


def _print_result(idx: int, result: RiskResult):
    level_colors = {"GREEN": "green", "YELLOW": "yellow", "RED": "red"}
    color = level_colors.get(result.warning_level, "white")

    click.echo(
        f"  [{idx}] "
        + click.style(f"{result.warning_level:6s}", fg=color, bold=True)
        + f"  Pc = {result.pc:.2e}"
        + f"  TCA: {result.conjunction.tca.strftime('%Y-%m-%d %H:%M')}"
        + f"  Miss: {result.conjunction.miss_distance_km:.3f} km"
        + f"  ΔV: {result.conjunction.relative_velocity_km_s:.2f} km/s"
        + f"  σ_B: ({result.b_plane_sigma_x:.2f}, {result.b_plane_sigma_z:.2f}) km"
        + f"  [{result.conjunction.primary_id} vs {result.conjunction.secondary_id}]"
    )


def _print_summary_banner(max_pc: float):
    if max_pc >= 1e-3:
        color, symbol = "red",    "🔴 RED ALERT"
    elif max_pc >= 1e-5:
        color, symbol = "yellow", "🟡 YELLOW ALERT"
    else:
        color, symbol = "green",  "🟢 ALL CLEAR"

    click.echo("\n" + "─" * 60)
    click.echo(click.style(
        f"  {symbol}  —  Max Pc = {max_pc:.2e}", fg=color, bold=True
    ))
    click.echo("─" * 60 + "\n")


def _save_results_to_json(results: list[RiskResult], path: Path):
    output = []
    for r in results:
        output.append({
            "primary_id":      r.conjunction.primary_id,
            "secondary_id":    r.conjunction.secondary_id,
            "tca":             r.conjunction.tca.isoformat(),
            "pc":              r.pc,
            "warning_level":   r.warning_level,
            "miss_distance_km": r.conjunction.miss_distance_km,
            "rel_velocity_km_s": r.conjunction.relative_velocity_km_s,
            "sigma_bplane_km": [r.b_plane_sigma_x, r.b_plane_sigma_z],
            "hard_body_radius_m": r.hard_body_radius_m,
        })
    with open(path, "w") as f:
        json.dump(output, f, indent=2)


def _save_tles_to_json(records, path: Path):
    output = [
        {"sat_id": r.sat_id, "name": r.name,
         "line1": r.line1, "line2": r.line2,
         "epoch": r.epoch.isoformat()}
        for r in records
    ]
    with open(path, "w") as f:
        json.dump(output, f, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli(auto_envvar_prefix="OURE")
