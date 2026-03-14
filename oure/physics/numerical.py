"""
OURE Physics Engine - High Precision Orbit Propagator (HPOP)
============================================================
"""

from __future__ import annotations
import numpy as np
from scipy.integrate import solve_ivp
from datetime import datetime, timedelta

from oure.core.models import StateVector
from oure.core import constants
from .base import BasePropagator
from .drag_corrector import AtmosphericDragCorrector

class NumericalPropagator(BasePropagator):
    """
    High-Precision Orbit Propagator using Runge-Kutta 4(5) numerical integration.
    
    Unlike SGP4 (which uses analytical mean elements), this integrates the exact
    equations of motion [r, v] step-by-step. It easily supports injecting instant 
    delta-V maneuvers.
    
    Includes:
    - Point-mass gravity
    - J2 Oblateness
    - Exponential Atmospheric Drag
    """

    def __init__(
        self, 
        cd: float = 2.2, 
        area_m2: float = 10.0, 
        mass_kg: float = 500.0, 
        solar_flux: float = 150.0
    ):
        self.cd = cd
        self.am_ratio = area_m2 / mass_kg
        self.f10_7 = solar_flux
        
        # We instantiate a dummy DragCorrector just to reuse its validated density table logic
        self._drag_model = AtmosphericDragCorrector(
            base_propagator=None, # type: ignore
            cd=cd, area_m2=area_m2, mass_kg=mass_kg, solar_flux=solar_flux
        )

    def _dynamics(self, t: float, y: np.ndarray) -> np.ndarray:
        """
        The state derivative function for solve_ivp: dy/dt = f(t, y)
        y = [x, y, z, vx, vy, vz]
        """
        r = y[:3]
        v = y[3:]
        r_mag = np.linalg.norm(r)
        
        # 1. Two-Body Gravity
        a_grav = -constants.MU_KM3_S2 * r / (r_mag**3)
        
        # 2. J2 Perturbation
        z = r[2]
        factor = -1.5 * constants.J2 * constants.MU_KM3_S2 * constants.R_EARTH_KM**2 / (r_mag**5)
        z_ratio = (z / r_mag)**2
        a_j2 = factor * np.array([
            r[0] * (1 - 5 * z_ratio),
            r[1] * (1 - 5 * z_ratio),
            r[2] * (3 - 5 * z_ratio)
        ])
        
        # 3. Atmospheric Drag
        altitude = r_mag - constants.R_EARTH_KM
        rho = self._drag_model._atmospheric_density(altitude)
        
        # Co-rotation of atmosphere
        v_rel = v.copy()
        v_rel[0] += constants.OMEGA_EARTH_RAD_S * r[1]
        v_rel[1] -= constants.OMEGA_EARTH_RAD_S * r[0]
        
        v_mag = np.linalg.norm(v_rel)
        if v_mag > 1e-9:
            v_mag_ms = v_mag * 1000.0
            a_drag_ms2 = -0.5 * self.cd * self.am_ratio * rho * (v_mag_ms**2)
            a_drag = (a_drag_ms2 / 1000.0) * (v_rel / v_mag)
        else:
            a_drag = np.zeros(3)
            
        a_tot = a_grav + a_j2 + a_drag
        return np.concatenate([v, a_tot])

    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        if dt_seconds == 0:
            return state
            
        y0 = state.state_vector_6d
        
        # Integrate using RK45
        sol = solve_ivp(
            fun=self._dynamics,
            t_span=[0, dt_seconds],
            y0=y0,
            method='RK45',
            rtol=1e-8,
            atol=1e-8
        )
        
        y_final = sol.y[:, -1]
        target_epoch = state.epoch + timedelta(seconds=dt_seconds)
        
        return StateVector.from_6d(y_final, target_epoch, state.sat_id)

    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        dt = (target_epoch - state.epoch).total_seconds()
        return self.propagate(state, dt)

    def _dynamics_vectorized(self, t: float, y: np.ndarray) -> np.ndarray:
        """
        Vectorized dynamics for N satellites. y is shape (6N,).
        """
        y_reshaped = y.reshape(-1, 6)
        r = y_reshaped[:, :3]
        v = y_reshaped[:, 3:]
        
        r_mag = np.linalg.norm(r, axis=1)
        
        # 1. Two-Body Gravity
        a_grav = -constants.MU_KM3_S2 * r / (r_mag[:, np.newaxis]**3)
        
        # 2. J2 Perturbation
        z = r[:, 2]
        factor = -1.5 * constants.J2 * constants.MU_KM3_S2 * constants.R_EARTH_KM**2 / (r_mag**5)
        z_ratio = (z / r_mag)**2
        
        a_j2 = np.zeros_like(r)
        a_j2[:, 0] = factor * r[:, 0] * (1 - 5 * z_ratio)
        a_j2[:, 1] = factor * r[:, 1] * (1 - 5 * z_ratio)
        a_j2[:, 2] = factor * r[:, 2] * (3 - 5 * z_ratio)
        
        # 3. Atmospheric Drag
        altitude = r_mag - constants.R_EARTH_KM
        rho = self._drag_model._atmospheric_density_vectorized(altitude)
        
        # Co-rotation
        v_rel = v.copy()
        v_rel[:, 0] += constants.OMEGA_EARTH_RAD_S * r[:, 1]
        v_rel[:, 1] -= constants.OMEGA_EARTH_RAD_S * r[:, 0]
        
        v_mag = np.linalg.norm(v_rel, axis=1)
        
        a_drag = np.zeros_like(v)
        valid = v_mag > 1e-9
        if np.any(valid):
            v_mag_ms = v_mag[valid] * 1000.0
            a_drag_ms2 = -0.5 * self.cd * self.am_ratio * rho[valid] * (v_mag_ms**2)
            v_hat = v_rel[valid] / v_mag[valid][:, np.newaxis]
            a_drag[valid] = (a_drag_ms2 / 1000.0)[:, np.newaxis] * v_hat
            
        a_tot = a_grav + a_j2 + a_drag
        return np.hstack([v, a_tot]).flatten()

    def propagate_many_to(self, states: np.ndarray, initial_epoch: datetime, target_epoch: datetime) -> np.ndarray:
        dt_seconds = (target_epoch - initial_epoch).total_seconds()
        if dt_seconds == 0:
            return states
            
        y0 = states.flatten()
        
        sol = solve_ivp(
            fun=self._dynamics_vectorized,
            t_span=[0, dt_seconds],
            y0=y0,
            method='RK45',
            rtol=1e-6, # slightly looser for speed on large N
            atol=1e-6
        )
        
        y_final = sol.y[:, -1]
        return y_final.reshape(-1, 6)
