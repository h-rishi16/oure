"""
OURE Physics Engine - SGP4 Propagator
=====================================
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
from sgp4.api import Satrec, jday

from oure.core import constants
from oure.core.exceptions import PropagationError
from oure.core.models import StateVector, TLERecord

from .base import BasePropagator
from .frames import rv2coe_vectorized
from .kepler import solve_kepler_vectorized


class SGP4Propagator(BasePropagator):
    """
    SGP4/SDP4 orbit propagator wrapping the official Vallado sgp4 library.
    """

    def __init__(self, tle: TLERecord):
        self.tle = tle
        self._satrec = Satrec.twoline2rv(tle.line1, tle.line2)

    @classmethod
    def from_tle(cls, tle: TLERecord) -> SGP4Propagator:
        return cls(tle)

    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        target = state.epoch + timedelta(seconds=dt_seconds)
        return self.propagate_to(state, target)

    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        # sgp4 library requires timezone-naive UTC or specific JD
        # We ensure it's UTC and then get JD
        jd, fr = jday(target_epoch.year, target_epoch.month, target_epoch.day,
                      target_epoch.hour, target_epoch.minute, target_epoch.second + target_epoch.microsecond/1e6)

        error_code, r, v = self._satrec.sgp4(jd, fr)
        if error_code != 0:
            raise PropagationError(f"SGP4 propagation failed with error code {error_code} for satellite {state.sat_id}")

        return StateVector(
            r=np.array(r),
            v=np.array(v),
            epoch=target_epoch,
            sat_id=state.sat_id
        )

    def propagate_many_to(self, states: np.ndarray, initial_epoch: datetime, target_epoch: datetime) -> np.ndarray:
        return self._propagate_many_simplified(states, initial_epoch, target_epoch)

    def _propagate_many_simplified(self, states: np.ndarray, initial_epoch: datetime, target_epoch: datetime) -> np.ndarray:
        # Simplified SGP4-like logic for state perturbations (Monte Carlo)
        n0 = self.tle.mean_motion_rev_per_day * constants.TWO_PI / constants.SECONDS_PER_DAY
        a0 = (constants.MU_KM3_S2 / n0**2) ** (1.0/3.0)

        tsince = (target_epoch - self.tle.epoch).total_seconds() / 60.0

        # Secular drag decay
        a_tle = a0 * (1 - (2/3) * self.tle.bstar * n0 * tsince * 60)
        n_tle = np.sqrt(constants.MU_KM3_S2 / max(a_tle, constants.R_EARTH_KM)**3)

        _, ecc, inc_deg, raan_deg, omega_deg, nu0 = rv2coe_vectorized(states[:, :3], states[:, 3:])

        # Prevent NaN in np.sqrt(1-ecc^2) if noise pushes eccentricity into hyperbolic regime
        ecc = np.clip(ecc, 0.0, 0.999999)

        inc = np.radians(inc_deg)
        raan0 = np.radians(raan_deg)
        omega0 = np.radians(omega_deg)

        E0 = 2 * np.arctan(np.sqrt((1-ecc)/(1+ecc)) * np.tan(nu0/2))
        M0 = E0 - ecc * np.sin(E0)

        p = a_tle * (1 - ecc**2)
        j2_factor = (3/2) * constants.J2 * (constants.R_EARTH_KM / p)**2

        dt_since_initial = (target_epoch - initial_epoch).total_seconds()

        raan  = raan0  - j2_factor * n_tle * np.cos(inc) * dt_since_initial
        omega = omega0 + j2_factor * n_tle * (2.5*np.cos(inc)**2 - 0.5) * dt_since_initial

        M = M0 + n_tle * dt_since_initial
        E = solve_kepler_vectorized(M, ecc)

        sin_nu = np.sqrt(1 - ecc**2) * np.sin(E) / (1 - ecc*np.cos(E))
        cos_nu = (np.cos(E) - ecc) / (1 - ecc * np.cos(E))
        nu = np.arctan2(sin_nu, cos_nu)

        r_vecs, v_vecs = self._elements_to_eci_vectorized(a_tle, ecc, inc, raan, omega, nu)

        return np.hstack([r_vecs, v_vecs])

    def _elements_to_eci_vectorized(self, a: np.ndarray | float, e: np.ndarray, i: np.ndarray, raan: np.ndarray, omega: np.ndarray, nu: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        p = a * (1 - e**2)
        r_mag = p / (1 + e * np.cos(nu))

        r_pqw = np.zeros((len(nu), 3))
        r_pqw[:, 0] = r_mag * np.cos(nu)
        r_pqw[:, 1] = r_mag * np.sin(nu)

        v_pqw = np.zeros((len(nu), 3))
        p_safe = np.maximum(p, 1e-9)
        v_mult = np.sqrt(constants.MU_KM3_S2 / p_safe)
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
