"""
OURE Physics Engine - SGP4 Propagator
=====================================
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np

from oure.core import constants
from oure.core.models import StateVector, TLERecord

from .base import BasePropagator
from .frames import rv2coe_vectorized
from .kepler import solve_kepler_vectorized


class SGP4Propagator(BasePropagator):
    """
    SGP4 (Simplified General Perturbations 4) — the industry standard for
    TLE-based orbit prediction.
    """

    def __init__(self, tle: TLERecord):
        self.tle = tle
        self._satellite = self._init_sgp4_satellite()

    def _init_sgp4_satellite(self) -> dict[str, Any]:
        n0 = self.tle.mean_motion_rev_per_day * constants.TWO_PI / constants.SECONDS_PER_DAY
        a0 = (constants.MU_KM3_S2 / n0**2) ** (1.0/3.0)
        return {
            "n0": n0, "a0": a0, "e0": self.tle.eccentricity,
            "i0": np.radians(self.tle.inclination_deg),
            "omega0": np.radians(self.tle.arg_perigee_deg),
            "raan0": np.radians(self.tle.raan_deg),
            "M0": np.radians(self.tle.mean_anomaly_deg),
            "bstar": self.tle.bstar, "epoch": self.tle.epoch,
        }

    @classmethod
    def from_tle(cls, tle: TLERecord) -> SGP4Propagator:
        return cls(tle)

    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        target = state.epoch + timedelta(seconds=dt_seconds)
        return self.propagate_to(state, target)

    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        states = np.atleast_2d(state.state_vector_6d)
        propagated_states = self.propagate_many_to(states, state.epoch, target_epoch)
        return StateVector.from_6d(propagated_states[0], target_epoch, state.sat_id)

    def propagate_many_to(self, states: np.ndarray, initial_epoch: datetime, target_epoch: datetime) -> np.ndarray:
        sat = self._satellite
        tsince = (target_epoch - sat["epoch"]).total_seconds() / 60.0
        dt_s = tsince * 60.0

        a = sat["a0"] * (1 - (2/3) * sat["bstar"] * sat["n0"] * tsince * 60)
        n = np.sqrt(constants.MU_KM3_S2 / max(a, constants.R_EARTH_KM)**3)

        e = np.full(states.shape[0], sat["e0"])
        i = np.full(states.shape[0], sat["i0"])

        p = a * (1 - e**2)
        j2_factor = (3/2) * constants.J2 * (constants.R_EARTH_KM / p)**2

        raan  = sat["raan0"]  - j2_factor * n * np.cos(i) * dt_s
        omega = sat["omega0"] + j2_factor * n * (2.5*np.cos(i)**2 - 0.5) * dt_s

        _, _, _, _, _, nu0 = rv2coe_vectorized(states[:, :3], states[:, 3:])
        E0 = 2 * np.arctan(np.sqrt((1-e)/(1+e)) * np.tan(nu0/2))
        M0 = E0 - e * np.sin(E0)

        dt_since_initial = (target_epoch - initial_epoch).total_seconds()
        M = M0 + n * dt_since_initial
        E = solve_kepler_vectorized(M, e)

        sin_nu = np.sqrt(1 - e**2) * np.sin(E) / (1 - e*np.cos(E))
        cos_nu = (np.cos(E) - e) / (1 - e*np.cos(E))
        nu = np.arctan2(sin_nu, cos_nu)

        r_vecs, v_vecs = self._elements_to_eci_vectorized(a, e, i, raan, omega, nu)

        return np.hstack([r_vecs, v_vecs])

    def _elements_to_eci_vectorized(self, a: np.ndarray, e: np.ndarray, i: np.ndarray, raan: np.ndarray, omega: np.ndarray, nu: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        p = a * (1 - e**2)
        r_mag = p / (1 + e * np.cos(nu))

        r_pqw = np.zeros((len(nu), 3))
        r_pqw[:, 0] = r_mag * np.cos(nu)
        r_pqw[:, 1] = r_mag * np.sin(nu)

        v_pqw = np.zeros((len(nu), 3))
        v_mult = np.sqrt(constants.MU_KM3_S2 / p)
        v_pqw[:, 0] = -v_mult * np.sin(nu)
        v_pqw[:, 1] = v_mult * (e + np.cos(nu))

        R = self._rot_pqw_to_eci_vectorized(raan, i, omega)

        r_eci = np.einsum('ijk,ik->ij', R, r_pqw)
        v_eci = np.einsum('ijk,ik->ij', R, v_pqw)

        return r_eci, v_eci

    def _rot_pqw_to_eci_vectorized(self, raan: np.ndarray, i: np.ndarray, omega: np.ndarray) -> np.ndarray:
        c_O, s_O = np.cos(raan), np.sin(raan)
        c_i, s_i = np.cos(i), np.sin(i)
        c_w, s_w = np.cos(omega), np.sin(omega)

        R = np.zeros((len(raan), 3, 3))
        R[:, 0, 0] = c_O*c_w - s_O*s_w*c_i
        R[:, 0, 1] = -c_O*s_w - s_O*c_w*c_i
        R[:, 0, 2] = s_O*s_i
        R[:, 1, 0] = s_O*c_w + c_O*s_w*c_i
        R[:, 1, 1] = -s_O*s_w + c_O*c_w*c_i
        R[:, 1, 2] = -c_O*s_i
        R[:, 2, 0] = s_w*s_i
        R[:, 2, 1] = c_w*s_i
        R[:, 2, 2] = c_i
        return R
