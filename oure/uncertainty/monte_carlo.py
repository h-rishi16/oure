"""
OURE Uncertainty Modeling - Monte Carlo Propagator
==================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from oure.core.exceptions import CovarianceNotPositiveDefiniteError
from oure.core.models import CovarianceMatrix, StateVector
from oure.physics.base import BasePropagator

logger = logging.getLogger("oure.uncertainty.monte_carlo")

@dataclass
class MonteCarloResult:
    """Container for a completed Monte Carlo run."""
    nominal_state: StateVector
    ghost_states: list[StateVector]
    sample_covariance: np.ndarray
    n_samples: int
    outlier_fraction: float

class MonteCarloUncertaintyPropagator:
    """
    Generates N "ghost" satellite trajectories by sampling the initial
    state distribution, propagating each, then reconstructing the
    output covariance from the ensemble.
    """

    def __init__(
        self,
        propagator: BasePropagator,
        n_samples: int = 1000,
        random_seed: int | None = 42
    ):
        self.propagator = propagator
        self.n_samples = n_samples
        self.rng = np.random.default_rng(random_seed)

    def run(
        self,
        initial_state: StateVector,
        initial_covariance: CovarianceMatrix,
        target_epoch: datetime
    ) -> MonteCarloResult:
        """
        Execute Monte Carlo propagation.
        """
        P0 = initial_covariance.matrix
        x0 = initial_state.state_vector_6d

        try:
            L = np.linalg.cholesky(P0)
        except np.linalg.LinAlgError:
            logger.warning("Covariance not positive definite — adding regularisation")
            P0_reg = P0 + np.eye(6) * 1e-12
            try:
                L = np.linalg.cholesky(P0_reg)
            except np.linalg.LinAlgError:
                raise CovarianceNotPositiveDefiniteError("Failed to regularize non-positive definite covariance matrix.")

        xi = self.rng.standard_normal((self.n_samples, 6))
        perturbations = (L @ xi.T).T
        samples_x0 = x0 + perturbations

        logger.info(f"Propagating {self.n_samples} Monte Carlo samples to {target_epoch}")

        # Vectorized propagation
        ghost_vecs = self.propagator.propagate_many_to(samples_x0, initial_state.epoch, target_epoch)

        # Convert the propagated vectors back to StateVector objects (if needed for return)
        ghost_states = [
            StateVector.from_6d(vec, target_epoch, f"{initial_state.sat_id}_ghost_{i:04d}")
            for i, vec in enumerate(ghost_vecs)
        ]

        x_mean = ghost_vecs.mean(axis=0)
        delta = ghost_vecs - x_mean
        P_mc = (delta.T @ delta) / (self.n_samples - 1)

        P_inv = np.linalg.pinv(P_mc)
        from scipy.stats import chi2
        # 3-sigma (99.73%) threshold for 6 degrees of freedom
        threshold = chi2.ppf(0.9973, df=6) # ~22.46
        distances = np.array([delta[i] @ P_inv @ delta[i] for i in range(self.n_samples)])
        outlier_frac = float(np.mean(distances > threshold))

        nominal_propagated = StateVector.from_6d(x_mean, target_epoch, initial_state.sat_id)

        logger.info(
            f"MC complete | outlier_frac={outlier_frac:.2%} | "
            f"σ_along-track≈{np.sqrt(P_mc[1,1]):.3f} km"
        )

        return MonteCarloResult(
            nominal_state=nominal_propagated,
            ghost_states=ghost_states,
            sample_covariance=P_mc,
            n_samples=self.n_samples,
            outlier_fraction=outlier_frac
        )
