"""
OURE Physics Engine
===================
The propagator is the heart of the system. It answers one question:

    "Given a satellite's state at time t₀, where is it at time t₁?"

This module is intentionally data-source agnostic. It only speaks
StateVectors and CovarianceMatrices — never TLERecords or SQL rows.

Physics Model Stack
-------------------
1. Base propagator : SGP4 (Simplified General Perturbations 4)
2. Perturbation 1  : J2 — Earth's equatorial bulge
3. Perturbation 2  : Atmospheric Drag (density from NRL MSISE / simplified)

Each perturbation layer is a separate class that wraps the one below it.
This is the "Decorator" pattern applied to orbital mechanics.
"""

from __future__ import annotations
import logging
import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from oure.core.models import StateVector, TLERecord, SolarFluxData

logger = logging.getLogger("oure.physics")

# ---------------------------------------------------------------------------
# Physical Constants
# ---------------------------------------------------------------------------

MU          = 398600.4418      # Earth gravitational parameter  km³/s²
R_EARTH     = 6378.137         # Earth mean equatorial radius   km
J2          = 1.08262668e-3    # Second zonal harmonic (oblateness coefficient)
OMEGA_EARTH = 7.2921150e-5     # Earth rotation rate            rad/s
F_OBLATE    = 1.0 / 298.257    # Earth flattening factor


# ---------------------------------------------------------------------------
# Abstract Propagator Interface
# ---------------------------------------------------------------------------

class BasePropagator(ABC):
    """
    Every propagator must answer: propagate(state, dt) → StateVector

    The Liskov principle: any propagator can replace any other in the
    pipeline without breaking callers. You could drop in a full numerical
    integrator later without touching the ConjunctionAssessor.
    """

    @abstractmethod
    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        """Advance state by dt_seconds. Returns a new StateVector."""
        ...

    @abstractmethod
    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        """Propagate to an absolute epoch."""
        ...


# ---------------------------------------------------------------------------
# Layer 1: SGP4 Core Propagator
# ---------------------------------------------------------------------------

class SGP4Propagator(BasePropagator):
    """
    SGP4 (Simplified General Perturbations 4) — the industry standard for
    TLE-based orbit prediction.

    SGP4 was designed in the 1970s by Hoots & Roehrich for NORAD and handles:
      - Secular drag effects (from B*)
      - Long-period perturbations from J2, J3, J4
      - Short-period perturbations from J2

    In production, we delegate to the `sgp4` PyPI library (Vallado's port)
    for the full Kozai-mean-elements SGP4/SDP4 formulation.
    The wrapper below provides a clean StateVector-based interface.

    Usage:
        prop = SGP4Propagator.from_tle(tle_record)
        state_t1 = prop.propagate(state_t0, dt_seconds=3600.0)
    """

    def __init__(self, tle: TLERecord):
        self.tle = tle
        self._satellite = self._init_sgp4_satellite()

    def _init_sgp4_satellite(self):
        """
        Initialize the underlying sgp4 library object.
        In production: from sgp4.api import Satrec; return Satrec.twoline2rv(l1, l2)
        Here we store parameters for our simplified implementation.
        """
        # Derive mean motion in rad/s from rev/day
        n0 = self.tle.mean_motion_rev_per_day * 2 * math.pi / 86400.0
        # Semi-major axis from mean motion: n² a³ = μ  →  a = (μ/n²)^(1/3)
        a0 = (MU / n0**2) ** (1.0/3.0)
        return {
            "n0": n0, "a0": a0,
            "e0": self.tle.eccentricity,
            "i0": math.radians(self.tle.inclination_deg),
            "omega0": math.radians(self.tle.arg_perigee_deg),
            "raan0": math.radians(self.tle.raan_deg),
            "M0": math.radians(self.tle.mean_anomaly_deg),
            "bstar": self.tle.bstar,
            "epoch": self.tle.epoch,
        }

    @classmethod
    def from_tle(cls, tle: TLERecord) -> "SGP4Propagator":
        return cls(tle)

    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        target = state.epoch + timedelta(seconds=dt_seconds)
        return self.propagate_to(state, target)

    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        """
        Propagate using SGP4 equations.

        Core SGP4 steps:
          1. Compute time since epoch (tsince) in minutes
          2. Update mean motion for secular drag decay
          3. Update secular terms: M (mean anomaly), ω (arg perigee), Ω (RAAN)
          4. Solve Kepler's Equation: M = E - e·sin(E)  [Newton-Raphson]
          5. Compute true anomaly ν from eccentric anomaly E
          6. Transform (a, e, i, Ω, ω, ν) → ECI (r, v)
        """
        sat = self._satellite
        tsince = (target_epoch - sat["epoch"]).total_seconds() / 60.0  # minutes

        # --- Step 1: SGP4 secular drag model ---
        # B* term models ballistic coefficient-related drag decay
        # n̈/n₀ ≈ 1 + (3/2)B*(n₀ tsince)²  (simplified)
        a = sat["a0"] * (1 - (2/3) * sat["bstar"] * sat["n0"] * tsince * 60)
        n = math.sqrt(MU / max(a, R_EARTH)**3)

        # --- Step 2: Secular J2 RAAN and arg-perigee precession ---
        # dΩ/dt = -3/2 * J2 * (R_earth/p)² * n * cos(i)
        # dω/dt = +3/4 * J2 * (R_earth/p)² * n * (5cos²i - 1)
        e = sat["e0"]
        i = sat["i0"]
        p = a * (1 - e**2)                 # Semi-latus rectum
        j2_factor = (3/2) * J2 * (R_EARTH / p)**2

        dt_s = tsince * 60.0
        raan  = sat["raan0"]  - j2_factor * n * math.cos(i) * dt_s
        omega = sat["omega0"] + j2_factor * n * (2.5*math.cos(i)**2 - 0.5) * dt_s

        # --- Step 3: Mean anomaly propagation ---
        M = sat["M0"] + n * dt_s

        # --- Step 4: Kepler's Equation solver (Newton-Raphson) ---
        E = self._solve_kepler(M, e)

        # --- Step 5: True anomaly ---
        sin_nu = math.sqrt(1 - e**2) * math.sin(E) / (1 - e*math.cos(E))
        cos_nu = (math.cos(E) - e) / (1 - e*math.cos(E))
        nu = math.atan2(sin_nu, cos_nu)

        # --- Step 6: Orbital elements → ECI Cartesian ---
        r_vec, v_vec = self._elements_to_eci(a, e, i, raan, omega, nu)

        return StateVector(
            r=r_vec, v=v_vec,
            epoch=target_epoch,
            sat_id=state.sat_id
        )

    def _solve_kepler(self, M: float, e: float, tol: float = 1e-10) -> float:
        """
        Kepler's Equation: M = E - e·sin(E)

        Newton-Raphson iteration:
            E_{k+1} = E_k - (E_k - e·sin(E_k) - M) / (1 - e·cos(E_k))

        Converges in 3-5 iterations for typical LEO eccentricities (e < 0.1).
        """
        E = M  # Initial guess
        for _ in range(50):
            dE = (M - E + e * math.sin(E)) / (1 - e * math.cos(E))
            E += dE
            if abs(dE) < tol:
                break
        return E

    def _elements_to_eci(
        self,
        a: float, e: float, i: float,
        raan: float, omega: float, nu: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Transform Keplerian elements to ECI position and velocity.

        Step 1: Compute r, v in the Perifocal (PQW) frame
            r_pqw = (p/(1+e·cosν)) * [cosν, sinν, 0]
            v_pqw = √(μ/p)         * [-sinν, e+cosν, 0]

        Step 2: Rotate PQW → ECI via three Euler rotations:
            R = R3(-Ω) · R1(-i) · R3(-ω)
            where R3, R1 are rotation matrices about z and x axes.
        """
        p = a * (1 - e**2)
        r_mag = p / (1 + e * math.cos(nu))

        # Perifocal frame
        r_pqw = r_mag * np.array([math.cos(nu), math.sin(nu), 0.0])
        v_pqw = math.sqrt(MU / p) * np.array([-math.sin(nu), e + math.cos(nu), 0.0])

        # Rotation matrix: PQW → ECI
        R = self._rot_pqw_to_eci(raan, i, omega)

        return R @ r_pqw, R @ v_pqw

    def _rot_pqw_to_eci(self, raan: float, i: float, omega: float) -> np.ndarray:
        """Compound rotation: R3(-raan) * R1(-i) * R3(-omega)"""
        c_O, s_O = math.cos(raan),  math.sin(raan)
        c_i, s_i = math.cos(i),     math.sin(i)
        c_w, s_w = math.cos(omega), math.sin(omega)

        return np.array([
            [ c_O*c_w - s_O*s_w*c_i,  -c_O*s_w - s_O*c_w*c_i,  s_O*s_i],
            [ s_O*c_w + c_O*s_w*c_i,  -s_O*s_w + c_O*c_w*c_i, -c_O*s_i],
            [ s_w*s_i,                  c_w*s_i,                 c_i    ]
        ])


# ---------------------------------------------------------------------------
# Layer 2: J2 Perturbation Corrector (Decorator over base propagator)
# ---------------------------------------------------------------------------

class J2PerturbationCorrector(BasePropagator):
    """
    Applies a first-order J2 correction on top of any base propagator.

    J2 is Earth's dominant perturbation: the planet is ~21 km fatter at the
    equator than at the poles (oblateness). This creates a gravitational
    asymmetry that causes:

      1. RAAN drift (Ω̇):  The orbital plane "precesses" westward for
         prograde orbits (i < 90°). Rate:
             dΩ/dt = -3/2 · (J2 · n · R_e²) / a²(1-e²)² · cos(i)
         At 600 km altitude, 51.6° incline (ISS): ~-7°/day

      2. Arg-of-perigee drift (ω̇): The ellipse rotates within its plane.
             dω/dt = +3/4 · (J2 · n · R_e²) / a²(1-e²)² · (5cos²i - 1)
         Sun-synchronous orbits use J2 precession to match solar drift!

    The correction here is additive — it adjusts the r,v vectors after
    the base SGP4 propagation for higher fidelity.
    """

    def __init__(self, base_propagator: BasePropagator):
        self._base = base_propagator

    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        base_state = self._base.propagate(state, dt_seconds)
        return self._apply_j2_correction(base_state, dt_seconds)

    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        dt = (target_epoch - state.epoch).total_seconds()
        return self.propagate(state, dt)

    def _apply_j2_correction(self, state: StateVector, dt: float) -> StateVector:
        """
        Compute J2 acceleration and integrate as a velocity correction.

        J2 acceleration in ECI:
            a_J2 = -3/2 · J2 · μ · R_e² / r⁵ · [
                x(1 - 5z²/r²),
                y(1 - 5z²/r²),
                z(3 - 5z²/r²)
            ]

        This is the gradient of the J2 perturbation potential:
            U_J2 = -(μ J2 R_e²) / 2r³ · (3sin²φ - 1)
        where φ is the geocentric latitude.
        """
        r = state.r
        r_mag = np.linalg.norm(r)
        z = r[2]

        # J2 acceleration
        factor = -1.5 * J2 * MU * R_EARTH**2 / r_mag**5
        z_ratio = (z / r_mag)**2

        a_j2 = factor * np.array([
            r[0] * (1 - 5*z_ratio),
            r[1] * (1 - 5*z_ratio),
            r[2] * (3 - 5*z_ratio)
        ])

        # Simple 1st-order velocity correction: Δv = a · Δt
        # (Higher order: use Verlet or RK4 integration)
        dv = a_j2 * dt

        return StateVector(
            r=state.r + 0.5 * a_j2 * dt**2,  # Δr = ½aΔt²
            v=state.v + dv,
            epoch=state.epoch,
            sat_id=state.sat_id
        )


# ---------------------------------------------------------------------------
# Layer 3: Atmospheric Drag Corrector
# ---------------------------------------------------------------------------

class AtmosphericDragCorrector(BasePropagator):
    """
    Applies drag deceleration using a simplified exponential atmosphere
    whose density is scaled by solar flux (F10.7).

    Atmospheric Density Model (exponential):
        ρ(h) = ρ₀ · exp(-(h - h₀) / H)
    where:
        h  = altitude (km)
        ρ₀ = reference density at h₀
        H  = scale height (km, ~7–8 km in LEO)

    Solar Activity Coupling:
        The upper atmosphere (thermosphere, 200–1000 km) expands dramatically
        during solar maximum. At F10.7 = 250, atmospheric density at 400 km
        can be 10× higher than at solar minimum (F10.7 = 70).

        Jacchia-Roberts correction factor:
            ρ_corrected = ρ(h) · exp(k_f10 · (F10.7 - 150))
        where k_f10 ≈ 0.003 (empirical constant for LEO altitudes).

    Drag Deceleration:
        a_drag = -1/2 · (C_D · A / m) · ρ · v_rel²  ·  v̂_rel
    where:
        C_D  = drag coefficient (~2.2 for typical satellite)
        A/m  = area-to-mass ratio (m²/kg)
        ρ    = atmospheric density (kg/m³)
        v_rel = velocity relative to atmosphere (nearly = v_ECI for LEO)
    """

    # Simplified reference atmosphere at key altitudes
    ATMO_TABLE = [
        # (alt_km, rho_0 kg/m³, scale_height_km)
        (200,  2.789e-10, 6.3),
        (300,  1.916e-11, 7.3),
        (400,  2.803e-12, 7.9),
        (500,  5.215e-13, 8.7),
        (600,  1.137e-13, 9.3),
        (700,  3.070e-14, 9.9),
    ]

    def __init__(
        self,
        base_propagator: BasePropagator,
        cd: float = 2.2,
        area_m2: float = 10.0,
        mass_kg: float = 500.0,
        solar_flux: float = 150.0
    ):
        self._base = base_propagator
        self.cd = cd
        self.am_ratio = area_m2 / mass_kg  # m²/kg
        self.f10_7 = solar_flux

    def set_solar_flux(self, f10_7: float):
        """Hot-reload solar flux without recreating the propagator."""
        self.f10_7 = f10_7
        logger.debug(f"Solar flux updated: F10.7={f10_7}")

    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        base_state = self._base.propagate(state, dt_seconds)
        return self._apply_drag(base_state, dt_seconds)

    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        dt = (target_epoch - state.epoch).total_seconds()
        return self.propagate(state, dt)

    def _atmospheric_density(self, altitude_km: float) -> float:
        """Interpolate density from reference table, corrected for solar flux."""
        # Find bounding rows in altitude table
        alt = max(200, min(700, altitude_km))
        for i in range(len(self.ATMO_TABLE) - 1):
            h0, rho0, H = self.ATMO_TABLE[i]
            h1, _, _    = self.ATMO_TABLE[i+1]
            if h0 <= alt <= h1:
                rho = rho0 * math.exp(-(alt - h0) / H)
                # Solar flux correction (Jacchia-Roberts approximation)
                k_solar = 0.003
                rho *= math.exp(k_solar * (self.f10_7 - 150.0))
                return rho
        return 1e-14  # Near-vacuum above 700 km

    def _apply_drag(self, state: StateVector, dt: float) -> StateVector:
        altitude = state.altitude
        rho = self._atmospheric_density(altitude)

        v_rel = state.v.copy()
        # Subtract Earth's rotation velocity from velocity (co-rotation correction)
        v_rel[0] += OMEGA_EARTH * state.r[1]
        v_rel[1] -= OMEGA_EARTH * state.r[0]

        v_mag = np.linalg.norm(v_rel)
        if v_mag < 1e-9:
            return state

        # Drag acceleration: a = -0.5 * Cd * (A/m) * ρ * v² * v̂  [km/s²]
        # Note: ρ is kg/m³, A/m is m²/kg → convert carefully
        # a [m/s²] = 0.5 * Cd * (A/m) * ρ [kg/m³] * v² [m²/s²]
        v_mag_ms = v_mag * 1000.0       # km/s → m/s
        a_drag_ms2 = -0.5 * self.cd * self.am_ratio * rho * v_mag_ms**2
        a_drag_kms2 = (a_drag_ms2 / 1000.0) * (v_rel / v_mag)  # back to km/s²

        dv = a_drag_kms2 * dt
        dr = 0.5 * a_drag_kms2 * dt**2

        return StateVector(
            r=state.r + dr,
            v=state.v + dv,
            epoch=state.epoch,
            sat_id=state.sat_id
        )


# ---------------------------------------------------------------------------
# Factory: Build the full propagator stack
# ---------------------------------------------------------------------------

class PropagatorFactory:
    """
    Assembles the layered propagator chain from a TLE + space weather context.

    Returns: AtmosphericDrag( J2Correction( SGP4() ) )

    Callers never need to know about the internal layering:
        prop = PropagatorFactory.build(tle, solar_flux=170.0)
        state_at_tca = prop.propagate_to(initial_state, tca_epoch)
    """

    @staticmethod
    def build(
        tle: TLERecord,
        solar_flux: float = 150.0,
        include_j2: bool = True,
        include_drag: bool = True,
        cd: float = 2.2,
        area_m2: float = 10.0,
        mass_kg: float = 500.0,
    ) -> BasePropagator:

        chain: BasePropagator = SGP4Propagator.from_tle(tle)

        if include_j2:
            chain = J2PerturbationCorrector(chain)
            logger.debug("J2 perturbation layer enabled")

        if include_drag:
            chain = AtmosphericDragCorrector(
                chain, cd=cd, area_m2=area_m2,
                mass_kg=mass_kg, solar_flux=solar_flux
            )
            logger.debug(f"Atmospheric drag layer enabled (F10.7={solar_flux})")

        return chain
