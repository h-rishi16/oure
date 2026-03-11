"""
OURE CLI - Fleet Command (Distributed "All-on-All" Screening)
=============================================================
"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from oure.conjunction.assessor import ConjunctionAssessor
from oure.physics.factory import PropagatorFactory
from oure.risk.calculator import RiskCalculator
from .cmd_analyze import _tle_to_initial_state, _default_covariance, _print_results_table, _print_summary_banner, _save_results_to_json
from .main import cli, OUREContext

console = Console()

def _screen_single_primary(primary_id, primary_tle, secondary_ids, records, flux, look_ahead, screening_dist, hard_body_radius):
    try:
        primary_state = _tle_to_initial_state(primary_tle)
        primary_prop = PropagatorFactory.build(primary_tle, solar_flux=flux)
        primary_cov = _default_covariance(primary_id)
        
        secondaries_data = []
        for sid in secondary_ids:
            if sid == primary_id or sid not in records: continue
            tle = records[sid]
            prop = PropagatorFactory.build(tle, solar_flux=flux)
            state = _tle_to_initial_state(tle)
            cov = _default_covariance(sid)
            secondaries_data.append((state, cov, prop))
            
        assessor = ConjunctionAssessor(screening_distance_km=screening_dist)
        events = assessor.find_conjunctions(
            primary_state, primary_cov, primary_prop, secondaries_data, look_ahead_hours=look_ahead
        )
        
        calculator = RiskCalculator(hard_body_radius_m=hard_body_radius)
        results = [calculator.compute_pc(e) for e in events]
        return results
    except Exception as e:
        return []

@cli.command()
@click.option("--primaries-file", type=click.Path(exists=True), required=True, help="JSON file with primary NORAD IDs.")
@click.option("--secondaries-file", type=click.Path(exists=True), required=True, help="JSON file with secondary NORAD IDs.")
@click.option("--look-ahead", default=72.0, show_default=True)
@click.option("--screening-dist", default=5.0, show_default=True)
@click.option("--hard-body-radius", default=20.0, show_default=True)
@click.option("--workers", default=4, help="Number of parallel processes.")
@click.option("--output", "-o", type=click.Path(), default="fleet_results.json")
@click.pass_context
def analyze_fleet(ctx, primaries_file, secondaries_file, look_ahead, screening_dist, hard_body_radius, workers, output):
    """Run distributed conjunction screening for an entire fleet."""
    oure_ctx = ctx.obj
    
    with open(primaries_file) as f: primary_ids = json.load(f)
    with open(secondaries_file) as f: secondary_ids = json.load(f)
        
    all_ids = list(set(primary_ids + secondary_ids))
    
    console.print(f"[cyan]Fetching TLE data for {len(all_ids)} objects...[/cyan]")
    records = {r.sat_id: r for r in oure_ctx.tle_fetcher.fetch(sat_ids=all_ids)}
    flux = oure_ctx.flux_fetcher.get_current_f107()
    
    all_results = []
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn()) as progress:
        task = progress.add_task("[cyan]Screening fleet (Distributed)...", total=len(primary_ids))
        
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _screen_single_primary, pid, records[pid], secondary_ids, records, flux, look_ahead, screening_dist, hard_body_radius
                ): pid for pid in primary_ids if pid in records
            }
            
            for future in as_completed(futures):
                res = future.result()
                all_results.extend(res)
                progress.update(task, advance=1)
                
    if not all_results:
        console.print("[bold green]No conjunctions found across the fleet.[/bold green]")
        return
        
    all_results.sort(key=lambda r: r.pc, reverse=True)
    _print_results_table(all_results[:20]) # show top 20
    _save_results_to_json(all_results, Path(output))
    console.print(f"\n[bold green]Saved {len(all_results)} total events to {output}[/bold green]")
