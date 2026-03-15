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

    def propagate_many_to(
        self, states: np.ndarray, initial_epoch: datetime, target_epoch: datetime
    ) -> np.ndarray:
        base_states = self._base.propagate_many_to(states, initial_epoch, target_epoch)
        dt = (target_epoch - initial_epoch).total_seconds()
        return self._apply_j2_correction_vectorized(base_states, dt)

    def _apply_j2_correction_vectorized(
        self, states: np.ndarray, dt: float
    ) -> np.ndarray:
        from oure.physics.frames import coe2rv_vectorized, rv2coe_vectorized

        r = states[:, :3]
        v = states[:, 3:]

        a, e, i, raan, omega, nu = rv2coe_vectorized(r, v)

        n = np.sqrt(constants.MU_KM3_S2 / (a**3))
        p = a * (1 - e**2)
        j2_factor = -1.5 * constants.J2 * (constants.R_EARTH_KM / p) ** 2 * n

        raan_dot = j2_factor * np.cos(i)
        omega_dot = j2_factor * (2.5 * np.cos(i) ** 2 - 0.5)

        raan += raan_dot * dt
        omega += omega_dot * dt

        r_new, v_new = coe2rv_vectorized(a, e, i, raan, omega, nu)
        return np.hstack([r_new, v_new])

    def _apply_j2_correction(self, state: StateVector, dt: float) -> StateVector:
        from oure.physics.frames import coe2rv_vectorized, rv2coe_vectorized

        r = state.r.reshape(1, 3)
        v = state.v.reshape(1, 3)

        a, e, i, raan, omega, nu = rv2coe_vectorized(r, v)

        n = np.sqrt(constants.MU_KM3_S2 / (a**3))
        p = a * (1 - e**2)
        j2_factor = -1.5 * constants.J2 * (constants.R_EARTH_KM / p) ** 2 * n

        raan_dot = j2_factor * np.cos(i)
        omega_dot = j2_factor * (2.5 * np.cos(i) ** 2 - 0.5)

        raan += raan_dot * dt
        omega += omega_dot * dt

        r_new, v_new = coe2rv_vectorized(a, e, i, raan, omega, nu)

        return StateVector(
            r=r_new[0], v=v_new[0], epoch=state.epoch, sat_id=state.sat_id
        )
