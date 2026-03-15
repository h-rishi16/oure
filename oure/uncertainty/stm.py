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
            return self._numerical_stm(state, dt_seconds)

    def _two_body_stm(self, state: StateVector, dt: float) -> np.ndarray:
        r = state.r
        r_mag = np.linalg.norm(r)
        g_matrix = (
            constants.MU_KM3_S2 / r_mag**3 * (3 * np.outer(r, r) / r_mag**2 - np.eye(3))
        )
        a_matrix = np.zeros((6, 6))
        a_matrix[:3, 3:] = np.eye(3)
        a_matrix[3:, :3] = g_matrix
        return expm(a_matrix * dt)

    def _j2_linearised_stm(self, state: StateVector, dt: float) -> np.ndarray:
        r = state.r
        r_mag = np.linalg.norm(r)
        r_hat = r / r_mag
        z_r = r_hat[2]

        coeff = (
            -1.5
            * constants.J2
            * constants.MU_KM3_S2
            * constants.R_EARTH_KM**2
            / r_mag**5
        )
        delta_g = np.zeros((3, 3))
        for i in range(3):
            for j in range(3):
                dij = 1.0 if i == j else 0.0
                delta_g[i, j] = coeff * (
                    (1 - 5 * z_r**2) * dij
                    - (1 - 5 * z_r**2) * r_hat[i] * r_hat[j]
                    - 10 * z_r * r_hat[i] * (1.0 if j == 2 else 0.0)
                    + 35 * z_r**2 * r_hat[i] * r_hat[j]
                )

        g_2body = (
            constants.MU_KM3_S2 / r_mag**3 * (3 * np.outer(r, r) / r_mag**2 - np.eye(3))
        )
        a_matrix = np.zeros((6, 6))
        a_matrix[:3, 3:] = np.eye(3)
        a_matrix[3:, :3] = g_2body + delta_g
        return expm(a_matrix * dt)

    def _numerical_stm(self, state: StateVector, dt: float) -> np.ndarray:
        """
        Computes the STM via centered finite differences of the dynamics.
        Uses a high-fidelity numerical propagator.
        """
        from oure.physics.numerical import NumericalPropagator

        prop = NumericalPropagator()

        epsilon = 1e-4  # Perturbation size in km and km/s
        stm = np.zeros((6, 6))

        x0 = state.state_vector_6d

        # We perturb each element of the initial state and see how the final state changes
        for i in range(6):
            x_plus = x0.copy()
            x_minus = x0.copy()
            x_plus[i] += epsilon
            x_minus[i] -= epsilon

            s_plus = StateVector.from_6d(x_plus, state.epoch, state.sat_id)
            s_minus = StateVector.from_6d(x_minus, state.epoch, state.sat_id)

            y_plus = prop.propagate(s_plus, dt).state_vector_6d
            y_minus = prop.propagate(s_minus, dt).state_vector_6d

            # Central difference: dY/dx_i
            stm[:, i] = (y_plus - y_minus) / (2 * epsilon)

        return stm
