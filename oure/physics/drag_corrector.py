"""
OURE Physics Engine - Atmospheric Drag Corrector
================================================
"""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np

from oure.core import constants
from oure.core.models import StateVector

from .atmosphere import AtmosphericModel
from .base import BasePropagator

logger = logging.getLogger("oure.physics.drag")


class AtmosphericDragCorrector(BasePropagator):
    """
    Applies drag deceleration using a simplified exponential atmosphere
    whose density is scaled by solar flux (F10.7).
    """

    def __init__(
        self,
        base_propagator: BasePropagator,
        cd: float = 2.2,
        area_m2: float = 10.0,
        mass_kg: float = 500.0,
        solar_flux: float = 150.0,
    ):
        self._base = base_propagator
        self.cd = cd
        self.am_ratio = area_m2 / mass_kg
        self._atmo = AtmosphericModel(solar_flux)

    def set_solar_flux(self, f10_7: float) -> None:
        self._atmo.f10_7 = f10_7
        logger.debug(f"Solar flux updated: F10.7={f10_7}")

    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        base_state = self._base.propagate(state, dt_seconds)
        return self._apply_drag(base_state, dt_seconds)

    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        dt = (target_epoch - state.epoch).total_seconds()
        base_state = self._base.propagate_to(state, target_epoch)
        return self._apply_drag(base_state, dt)

    def propagate_many_to(
        self, states: np.ndarray, initial_epoch: datetime, target_epoch: datetime
    ) -> np.ndarray:
        base_states = self._base.propagate_many_to(states, initial_epoch, target_epoch)
        dt = (target_epoch - initial_epoch).total_seconds()
        return self._apply_drag_vectorized(base_states, dt)

    def _apply_drag(self, state: StateVector, dt: float) -> StateVector:
        altitude = state.altitude_km
        rho = self._atmo.get_density(altitude)

        v_rel = state.v.copy()
        v_rel[0] += constants.OMEGA_EARTH_RAD_S * state.r[1]
        v_rel[1] -= constants.OMEGA_EARTH_RAD_S * state.r[0]

        v_mag = np.linalg.norm(v_rel)
        if v_mag < 1e-9:
            return state

        v_mag_ms = v_mag * 1000.0
        a_drag_ms2 = -0.5 * self.cd * self.am_ratio * rho * v_mag_ms**2
        a_drag_kms2 = (a_drag_ms2 / 1000.0) * (v_rel / v_mag)

        dv = a_drag_kms2 * dt
        dr = 0.5 * a_drag_kms2 * dt**2

        return StateVector(
            r=state.r + dr, v=state.v + dv, epoch=state.epoch, sat_id=state.sat_id
        )

    def _apply_drag_vectorized(self, states: np.ndarray, dt: float) -> np.ndarray:
        r = states[:, :3]
        v = states[:, 3:]

        r_mag = np.linalg.norm(r, axis=1)
        altitude = r_mag - constants.R_EARTH_KM
        rho = self._atmo.get_density_vectorized(altitude)

        v_rel = v.copy()
        v_rel[:, 0] += constants.OMEGA_EARTH_RAD_S * r[:, 1]
        v_rel[:, 1] -= constants.OMEGA_EARTH_RAD_S * r[:, 0]

        v_mag = np.linalg.norm(v_rel, axis=1)

        # Mask out near-zero velocities
        valid = v_mag >= 1e-9

        dv = np.zeros_like(v)
        dr = np.zeros_like(r)

        if np.any(valid):
            v_mag_ms = v_mag[valid] * 1000.0
            a_drag_ms2 = -0.5 * self.cd * self.am_ratio * rho[valid] * v_mag_ms**2

            # v_rel / v_mag is unit vector
            v_hat = v_rel[valid] / v_mag[valid][:, np.newaxis]
            a_drag_kms2 = (a_drag_ms2 / 1000.0)[:, np.newaxis] * v_hat

            dv[valid] = a_drag_kms2 * dt
            dr[valid] = 0.5 * a_drag_kms2 * dt**2

        return np.hstack([r + dr, v + dv])
