"""
OURE Uncertainty Modeling - Analytical Covariance Propagator
===========================================================
"""

from __future__ import annotations

import logging
from datetime import timedelta

import numpy as np

from oure.core.models import CovarianceMatrix, StateVector

from .noise import ProcessNoiseModel
from .stm import STMCalculator

logger = logging.getLogger("oure.uncertainty.covariance_propagator")

class CovariancePropagator:
    """
    Propagates the 6×6 covariance matrix from t₀ to t using the STM:
    P(t) = Φ P₀ Φᵀ + Q
    """

    DEFAULT_Q_SCALE = 1e-10  # km²/s³

    def __init__(self, stm_calculator: STMCalculator | None = None, q_scale: float = DEFAULT_Q_SCALE):
        self.stm = stm_calculator or STMCalculator(fidelity=1)
        self.noise_model = ProcessNoiseModel(q_scale=q_scale)

    def propagate(
        self,
        covariance: CovarianceMatrix,
        reference_state: StateVector,
        dt_seconds: float,
    ) -> CovarianceMatrix:
        """
        Propagate covariance by dt_seconds.
        """
        Phi = self.stm.compute(reference_state, dt_seconds)
        P0 = covariance.matrix
        P_propagated = Phi @ P0 @ Phi.T

        Q = self.noise_model.get_noise_matrix(dt_seconds)

        P_final = P_propagated + Q
        P_final = 0.5 * (P_final + P_final.T)

        target_epoch = covariance.epoch + timedelta(seconds=dt_seconds)

        logger.debug(
            f"Covariance propagated Δt={dt_seconds:.0f}s | "
            f"σ_pos={np.sqrt(P_final[0,0]):.3f} km | "
            f"σ_vel={np.sqrt(P_final[3,3])*1000:.3f} m/s"
        )

        return CovarianceMatrix(
            matrix=P_final,
            epoch=target_epoch,
            sat_id=covariance.sat_id,
            frame="ECI"
        )
