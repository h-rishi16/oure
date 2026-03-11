"""
OURE Physics Engine - J2 Perturbation Corrector
===============================================
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from oure.core import constants
from oure.core.models import StateVector

from .base import BasePropagator


class J2PerturbationCorrector(BasePropagator):
    """
    Applies a first-order J2 correction on top of any base propagator.
    """

    def __init__(self, base_propagator: BasePropagator):
        self._base = base_propagator

    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        base_state = self._base.propagate(state, dt_seconds)
        return self._apply_j2_correction(base_state, dt_seconds)

    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        dt = (target_epoch - state.epoch).total_seconds()
        base_state = self._base.propagate_to(state, target_epoch)
        return self._apply_j2_correction(base_state, dt)

    def propagate_many_to(self, states: np.ndarray, initial_epoch: datetime, target_epoch: datetime) -> np.ndarray:
        base_states = self._base.propagate_many_to(states, initial_epoch, target_epoch)
        dt = (target_epoch - initial_epoch).total_seconds()
        return self._apply_j2_correction_vectorized(base_states, dt)

    def _apply_j2_correction(self, state: StateVector, dt: float) -> StateVector:
        r = state.r
        r_mag = np.linalg.norm(r)
        z = r[2]

        factor = -1.5 * constants.J2 * constants.MU_KM3_S2 * constants.R_EARTH_KM**2 / r_mag**5
        z_ratio = (z / r_mag)**2

        a_j2 = factor * np.array([
            r[0] * (1 - 5*z_ratio),
            r[1] * (1 - 5*z_ratio),
            r[2] * (3 - 5*z_ratio)
        ])

        dv = a_j2 * dt
        dr = 0.5 * a_j2 * dt**2

        return StateVector(
            r=state.r + dr,
            v=state.v + dv,
            epoch=state.epoch,
            sat_id=state.sat_id
        )

    def _apply_j2_correction_vectorized(self, states: np.ndarray, dt: float) -> np.ndarray:
        r = states[:, :3]
        v = states[:, 3:]
        r_mag = np.linalg.norm(r, axis=1)
        z = r[:, 2]

        factor = -1.5 * constants.J2 * constants.MU_KM3_S2 * constants.R_EARTH_KM**2 / r_mag**5
        z_ratio = (z / r_mag)**2

        a_j2 = np.zeros_like(r)
        a_j2[:, 0] = factor * r[:, 0] * (1 - 5*z_ratio)
        a_j2[:, 1] = factor * r[:, 1] * (1 - 5*z_ratio)
        a_j2[:, 2] = factor * r[:, 2] * (3 - 5*z_ratio)

        dv = a_j2 * dt
        dr = 0.5 * a_j2 * dt**2

        return np.hstack([r + dr, v + dv])
