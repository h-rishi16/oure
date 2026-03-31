"""
OURE Physics Engine - Solar Radiation Pressure (SRP) Corrector
==============================================================
"""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np

from oure.core.models import StateVector

from .base import BasePropagator

logger = logging.getLogger("oure.physics.srp")


class SRPCorrector(BasePropagator):
    """
    Applies Solar Radiation Pressure (SRP) using a first-order cannonball model.
    """

    def __init__(
        self,
        base_propagator: BasePropagator,
        cr: float = 1.2,
        area_m2: float = 10.0,
        mass_kg: float = 500.0,
    ):
        self._base = base_propagator
        self.cr = cr
        self.am_ratio = area_m2 / mass_kg

    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        base_state = self._base.propagate(state, dt_seconds)
        return self._apply_srp(base_state, dt_seconds)

    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        dt = (target_epoch - state.epoch).total_seconds()
        base_state = self._base.propagate_to(state, target_epoch)
        return self._apply_srp(base_state, dt)

    def propagate_many_to(
        self, states: np.ndarray, initial_epoch: datetime, target_epoch: datetime
    ) -> np.ndarray:
        base_states = self._base.propagate_many_to(states, initial_epoch, target_epoch)
        dt = (target_epoch - initial_epoch).total_seconds()
        return self._apply_srp_vectorized(base_states, dt, target_epoch)

    def _get_sun_vector(self, epoch: datetime) -> np.ndarray:
        """
        Approximate sun vector in ECI frame.
        """
        # Simplistic model: Assume sun moves in ecliptic plane
        # This is a placeholder for a more accurate celestial model
        # For a first-order corrector, a coarse sun vector is often acceptable
        # compared to ignoring SRP entirely.
        from datetime import UTC
        from math import cos, sin

        if epoch.tzinfo is None:
            epoch = epoch.replace(tzinfo=UTC)

        # Days since J2000
        t_j2000 = (
            epoch - datetime(2000, 1, 1, 12, 0, tzinfo=UTC)
        ).total_seconds() / 86400.0

        # Mean longitude
        mean_long = (280.460 + 0.9856474 * t_j2000) % 360
        # Mean anomaly
        g = (357.528 + 0.9856003 * t_j2000) % 360

        lamb = (
            mean_long + 1.915 * sin(np.radians(g)) + 0.020 * sin(np.radians(2 * g))
        ) % 360
        eps = 23.439 - 0.0000004 * t_j2000

        r_sun = np.array(
            [
                cos(np.radians(lamb)),
                sin(np.radians(lamb)) * cos(np.radians(eps)),
                sin(np.radians(lamb)) * sin(np.radians(eps)),
            ]
        )
        from typing import cast

        return cast(np.ndarray, r_sun / np.linalg.norm(r_sun))

    def _apply_srp(self, state: StateVector, dt: float) -> StateVector:
        sun_hat = self._get_sun_vector(state.epoch)

        # P_sun at 1 AU ~ 4.56e-6 N/m^2
        p_sun = 4.56e-6
        # a_srp = -P_sun * C_R * (A/m) * r_sun_hat
        # Convert to km/s^2
        a_srp_ms2 = -p_sun * self.cr * self.am_ratio * sun_hat
        a_srp_kms2 = a_srp_ms2 / 1000.0

        dv = a_srp_kms2 * dt
        dr = 0.5 * a_srp_kms2 * dt**2

        return StateVector(
            r=state.r + dr, v=state.v + dv, epoch=state.epoch, sat_id=state.sat_id
        )

    def _apply_srp_vectorized(
        self, states: np.ndarray, dt: float, epoch: datetime
    ) -> np.ndarray:
        sun_hat = self._get_sun_vector(epoch)
        p_sun = 4.56e-6
        a_srp_kms2 = (-p_sun * self.cr * self.am_ratio * sun_hat) / 1000.0

        dv = a_srp_kms2 * dt
        dr = 0.5 * a_srp_kms2 * dt**2

        new_states = states.copy()
        new_states[:, :3] += dr
        new_states[:, 3:] += dv

        return new_states
