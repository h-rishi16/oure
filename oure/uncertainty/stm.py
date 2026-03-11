"""
OURE Uncertainty Modeling - State Transition Matrix (STM)
=========================================================
"""

from __future__ import annotations

import logging

import numpy as np
from scipy.linalg import expm

from oure.core import constants
from oure.core.models import StateVector

logger = logging.getLogger("oure.uncertainty.stm")

class STMCalculator:
    """
    Computes the 6×6 State Transition Matrix Φ(t, t₀) for covariance
    propagation.
    """

    def __init__(self, fidelity: int = 1):
        assert fidelity in (0, 1, 2), "Fidelity must be 0, 1, or 2"
        self.fidelity = fidelity

    def compute(self, state: StateVector, dt_seconds: float) -> np.ndarray:
        """Returns the 6×6 STM Φ(t₀+dt, t₀)."""
        if self.fidelity == 0:
            return self._two_body_stm(state, dt_seconds)
        elif self.fidelity == 1:
            return self._j2_linearised_stm(state, dt_seconds)
        else:
            # This case requires a propagator, which is not handled here yet.
            # This will be part of a future refactoring.
            raise NotImplementedError("Numerical STM is not yet implemented in this refactored structure.")

    def _two_body_stm(self, state: StateVector, dt: float) -> np.ndarray:
        r = state.r
        r_mag = np.linalg.norm(r)
        n = np.sqrt(constants.MU_KM3_S2 / r_mag**3)
        G = constants.MU_KM3_S2 / r_mag**3 * (3 * np.outer(r, r) / r_mag**2 - np.eye(3))
        A = np.zeros((6, 6))
        A[:3, 3:] = np.eye(3)
        A[3:, :3] = G
        return expm(A * dt)  # type: ignore

    def _j2_linearised_stm(self, state: StateVector, dt: float) -> np.ndarray:
        r = state.r
        r_mag = np.linalg.norm(r)
        r_hat = r / r_mag
        z_r = r_hat[2]

        coeff = -3/2 * constants.J2 * constants.MU_KM3_S2 * constants.R_EARTH_KM**2 / r_mag**4
        delta_G = np.zeros((3, 3))
        for i in range(3):
            for j in range(3):
                dij = 1.0 if i == j else 0.0
                delta_G[i, j] = coeff * (
                    (1 - 5*z_r**2) * dij / r_mag
                    - (1 - 5*z_r**2) * r_hat[i]*r_hat[j] / r_mag
                    - 10*z_r * r_hat[i]*(1.0 if j == 2 else 0.0) / r_mag
                    + 35*z_r**2 * r_hat[i]*r_hat[j] / r_mag
                )

        G_2body = constants.MU_KM3_S2 / r_mag**3 * (3 * np.outer(r, r) / r_mag**2 - np.eye(3))
        A = np.zeros((6, 6))
        A[:3, 3:] = np.eye(3)
        A[3:, :3] = G_2body + delta_G
        return expm(A * dt)  # type: ignore
