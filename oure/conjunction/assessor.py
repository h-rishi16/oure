"""
OURE Conjunction Assessment - Assessor
======================================
Orchestrator for the conjunction assessment process.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import numpy as np

from oure.core.models import ConjunctionEvent, CovarianceMatrix, StateVector
from oure.physics.base import BasePropagator

from .spatial_index import KDTreeSpatialIndex
from .tca_finder import TCARefinementEngine

logger = logging.getLogger("oure.conjunction.assessor")

class ConjunctionAssessor:
    """
    Two-stage conjunction detection orchestrator.
    """

    def __init__(
        self,
        screening_distance_km: float = 5.0,
        tca_time_step_s: float = 30.0,
        tca_refinement_tol_s: float = 0.1,
    ):
        self.screening_distance = screening_distance_km
        self.tca_time_step_s = tca_time_step_s
        self.tca_finder = TCARefinementEngine(tolerance_seconds=tca_refinement_tol_s)

    def find_conjunctions(
        self,
        primary: StateVector,
        primary_cov: CovarianceMatrix,
        primary_propagator: BasePropagator,
        secondaries: list[tuple[StateVector, CovarianceMatrix, BasePropagator]],
        look_ahead_hours: float = 72.0,
    ) -> list[ConjunctionEvent]:
        """
        Screen primary against all secondaries over a look-ahead window.
        """
        n_steps = int(look_ahead_hours * 3600 / self.tca_time_step_s)
        t0 = primary.epoch
        time_offsets = [i * self.tca_time_step_s for i in range(n_steps)]

        logger.info(f"Screening {len(secondaries)} objects over {look_ahead_hours}h ({n_steps} steps)")

        candidate_pairs: dict[int, list[datetime]] = {}
        
        # Group secondaries by propagator type for potential future batching
        # For now, we still iterate steps, but we can optimize the inner loops
        
        for dt in time_offsets:
            epoch = t0 + timedelta(seconds=dt)
            p_state = primary_propagator.propagate_to(primary, epoch)

            sec_positions = np.zeros((len(secondaries), 3))
            
            # TODO: Future optimization - implement propagate_many in all base propagators
            # and use it here to eliminate the inner Python loop.
            for j, (s_state, _, s_prop) in enumerate(secondaries):
                try:
                    s_prop_state = s_prop.propagate_to(s_state, epoch)
                    sec_positions[j] = s_prop_state.r
                except Exception:
                    sec_positions[j] = np.array([1e9, 1e9, 1e9])

            index = KDTreeSpatialIndex(sec_positions)
            close_indices = index.query_radius(p_state.r, self.screening_distance)

            for idx in close_indices:
                if idx not in candidate_pairs:
                    candidate_pairs[idx] = []
                candidate_pairs[idx].append(epoch)

        logger.info(f"Stage 1 found {len(candidate_pairs)} candidate pairs")

        conjunction_events = []
        for sec_idx, flagged_epochs in candidate_pairs.items():
            s_state, s_cov, s_prop = secondaries[sec_idx]

            tca_result = self.tca_finder.find_tca(
                primary, primary_propagator, s_state, s_prop,
                min(flagged_epochs), max(flagged_epochs)
            )

            if tca_result:
                tca_epoch, miss_distance = tca_result
                if miss_distance <= self.screening_distance * 2:
                    p_tca = primary_propagator.propagate_to(primary, tca_epoch)
                    s_tca = s_prop.propagate_to(s_state, tca_epoch)
                    v_rel = float(np.linalg.norm(p_tca.v - s_tca.v))

                    event = ConjunctionEvent(
                        primary_id=primary.sat_id,
                        secondary_id=s_state.sat_id,
                        tca=tca_epoch,
                        miss_distance_km=miss_distance,
                        relative_velocity_km_s=v_rel,
                        primary_state=p_tca,
                        secondary_state=s_tca,
                        primary_covariance=primary_cov,
                        secondary_covariance=s_cov,
                    )
                    conjunction_events.append(event)

        conjunction_events.sort(key=lambda e: e.miss_distance_km)
        logger.info(f"Stage 2 produced {len(conjunction_events)} conjunction events")
        return conjunction_events
