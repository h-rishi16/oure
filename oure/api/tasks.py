"""
OURE Background Tasks
=====================
"""

import logging
import os
from typing import Any

from oure.cli.utils import _default_covariance, _tle_to_initial_state
from oure.conjunction.assessor import ConjunctionAssessor
from oure.data.noaa import NOAASolarFluxFetcher
from oure.data.spacetrack import SpaceTrackFetcher
from oure.physics.factory import PropagatorFactory
from oure.risk.calculator import RiskCalculator

from .celery_app import celery_app

logger = logging.getLogger("oure.tasks")

@celery_app.task(bind=True)  # type: ignore
def run_fleet_screening(self: Any, primary_id: str, secondary_ids: list[str]) -> dict[str, Any]:
    """
    Background task to run a massive KD-Tree screening and risk analysis
    on the entire catalog without blocking the main web server.
    """
    self.update_state(state='PROGRESS', meta={'status': 'Fetching TLEs from Space-Track...'})

    tle_fetcher = SpaceTrackFetcher(username=os.getenv("SPACETRACK_USER", ""), password=os.getenv("SPACETRACK_PASS", ""))
    flux_fetcher = NOAASolarFluxFetcher()

    all_ids = [primary_id] + secondary_ids
    records = {r.sat_id: r for r in tle_fetcher.fetch(sat_ids=all_ids)}
    flux = flux_fetcher.get_current_f107()

    if primary_id not in records:
        return {"status": "failed", "error": f"Primary {primary_id} not found."}

    self.update_state(state='PROGRESS', meta={'status': 'Building Physics Propagators...'})

    primary_tle = records[primary_id]
    primary_state = _tle_to_initial_state(primary_tle)
    primary_prop = PropagatorFactory.build(primary_tle, solar_flux=flux)
    primary_cov = _default_covariance(primary_id)

    secondaries_data = []
    for sid in secondary_ids:
        if sid not in records:
            continue
        tle = records[sid]
        prop = PropagatorFactory.build(tle, solar_flux=flux)
        state = _tle_to_initial_state(tle)
        cov = _default_covariance(sid)
        secondaries_data.append((state, cov, prop))

    self.update_state(state='PROGRESS', meta={'status': f'Screening {len(secondaries_data)} objects...'})

    assessor = ConjunctionAssessor(screening_distance_km=5.0)
    events = assessor.find_conjunctions(
        primary_state, primary_cov, primary_prop, secondaries_data, look_ahead_hours=72.0
    )

    self.update_state(state='PROGRESS', meta={'status': 'Calculating Risk Metrics...'})
    calculator = RiskCalculator(hard_body_radius_m=20.0)
    results: list[dict[str, Any]] = []
    for e in events:
        res = calculator.compute_pc(e)
        results.append({
            "primary_id": e.primary_id,
            "secondary_id": e.secondary_id,
            "tca": e.tca.isoformat(),
            "miss_distance_km": e.miss_distance_km,
            "pc": res.pc,
            "warning_level": res.warning_level
        })

    results.sort(key=lambda x: float(x['pc']), reverse=True)

    return {
        "status": "completed",
        "events_found": len(results),
        "results": results
    }
