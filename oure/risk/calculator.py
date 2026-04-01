"""
OURE Risk Calculation - Orchestrator
====================================
"""

from __future__ import annotations

import numpy as np

from oure.core.models import ConjunctionEvent, RiskResult

from .alert import AlertClassifier
from .bplane import BPlaneProjector
from .foster import FosterPcCalculator


class RiskCalculator:
    """
    Computes the Probability of Collision for a ConjunctionEvent.
    """

    def __init__(self, hard_body_radius_m: float = 20.0):
        self.hard_body_radius_km = hard_body_radius_m / 1000.0
        self.bplane_projector = BPlaneProjector()
        self.pc_calculator = FosterPcCalculator(self.hard_body_radius_km)

    def compute_pc(self, event: ConjunctionEvent) -> RiskResult:
        """
        Full Pc pipeline for one conjunction event.
        """
        import time

        from oure.core.metrics import MetricsManager

        start_time = time.perf_counter()

        # Safety check: Near-zero relative velocity makes B-plane projection singular
        if event.relative_velocity_km_s < 1e-6:
            res = RiskResult(
                conjunction=event,
                pc=0.0,
                combined_covariance=np.zeros((2, 2)),
                warning_level="GREEN",
                b_plane_sigma_x=0.0,
                b_plane_sigma_z=0.0,
                hard_body_radius_m=self.hard_body_radius_km * 1000.0,
                method="SKIPPED_SINGULAR",
            )
            MetricsManager.record_risk_duration(time.perf_counter() - start_time)
            return res

        projection = self.bplane_projector.project(event)

        pc = self.pc_calculator.compute(projection.b_vec_2d, projection.C_2d)

        sigma_x = np.sqrt(projection.C_2d[0, 0])
        sigma_z = np.sqrt(projection.C_2d[1, 1])

        alert = AlertClassifier()

        result = RiskResult(
            conjunction=event,
            pc=pc,
            combined_covariance=projection.C_2d,
            hard_body_radius_m=self.hard_body_radius_km * 1000,
            b_plane_sigma_x=sigma_x,
            b_plane_sigma_z=sigma_z,
            method=self.pc_calculator.method.value,
        )

        result.warning_level = alert.classify(result)

        # Record metrics
        MetricsManager.record_risk_duration(time.perf_counter() - start_time)

        return result
