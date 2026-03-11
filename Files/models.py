"""
OURE Core Data Models
=====================
Immutable dataclasses that flow between all layers of the system.
No business logic here — pure data containers with validation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import numpy as np


# ---------------------------------------------------------------------------
# Orbital State Representation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StateVector:
    """
    A satellite's position and velocity in ECI (Earth-Centered Inertial) frame.

    Units
    -----
    r : km        (3-component position vector)
    v : km/s      (3-component velocity vector)
    epoch : UTC   (the moment this state is valid)

    Design note: frozen=True enforces immutability — physics functions
    produce new StateVectors rather than mutating existing ones.
    """
    r: np.ndarray          # shape (3,) — ECI position in km
    v: np.ndarray          # shape (3,) — ECI velocity in km/s
    epoch: datetime
    sat_id: str            # NORAD catalog ID

    def __post_init__(self):
        # NumPy arrays aren't hashable, so we convert to tuple for identity
        object.__setattr__(self, 'r', np.asarray(self.r, dtype=np.float64))
        object.__setattr__(self, 'v', np.asarray(self.v, dtype=np.float64))
        assert self.r.shape == (3,), "Position vector must be shape (3,)"
        assert self.v.shape == (3,), "Velocity vector must be shape (3,)"

    @property
    def speed(self) -> float:
        return float(np.linalg.norm(self.v))

    @property
    def altitude(self) -> float:
        """Approximate altitude above Earth's surface in km."""
        R_EARTH = 6378.137  # km
        return float(np.linalg.norm(self.r)) - R_EARTH


@dataclass(frozen=True)
class TLERecord:
    """
    Raw Two-Line Element set as fetched from Space-Track.
    Stored verbatim — transformation to StateVector is the propagator's job.
    """
    sat_id: str
    name: str
    line1: str
    line2: str
    epoch: datetime
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    # Parsed orbital elements (convenience fields, derived from TLE lines)
    inclination_deg: float = 0.0
    raan_deg: float = 0.0          # Right Ascension of Ascending Node
    eccentricity: float = 0.0
    arg_perigee_deg: float = 0.0
    mean_anomaly_deg: float = 0.0
    mean_motion_rev_per_day: float = 0.0
    bstar: float = 0.0             # Drag coefficient (SGP4 B* term)


@dataclass
class CovarianceMatrix:
    """
    6×6 position-velocity covariance in ECI frame.

    Layout:
        [ Cov(r,r)  Cov(r,v) ]     rows/cols: [x, y, z, vx, vy, vz]
        [ Cov(v,r)  Cov(v,v) ]

    The covariance describes our uncertainty about a satellite's true state.
    A larger covariance = we know less about where it really is.

    Units: km² for position blocks, km²/s² for mixed, km²/s⁴ for velocity.
    """
    matrix: np.ndarray   # shape (6, 6), symmetric positive-definite
    epoch: datetime
    sat_id: str
    frame: str = "ECI"   # coordinate frame label

    def __post_init__(self):
        self.matrix = np.asarray(self.matrix, dtype=np.float64)
        assert self.matrix.shape == (6, 6), "Covariance must be 6×6"

    @property
    def position_block(self) -> np.ndarray:
        """Upper-left 3×3: position uncertainty (km²)."""
        return self.matrix[:3, :3]

    @property
    def velocity_block(self) -> np.ndarray:
        """Lower-right 3×3: velocity uncertainty (km²/s²)."""
        return self.matrix[3:, 3:]

    @property
    def is_positive_definite(self) -> bool:
        try:
            np.linalg.cholesky(self.matrix)
            return True
        except np.linalg.LinAlgError:
            return False


@dataclass
class SolarFluxData:
    """F10.7 solar flux index — proxy for solar activity affecting drag."""
    date: datetime
    f10_7: float           # Solar radio flux at 10.7 cm wavelength (sfu)
    f10_7_81day_avg: float # 81-day centered average (smoothed)
    ap_index: float        # Geomagnetic activity index


@dataclass
class ConjunctionEvent:
    """
    A predicted close approach between two satellites.
    Produced by the ConjunctionAssessor; consumed by the RiskCalculator.
    """
    primary_id: str
    secondary_id: str
    tca: datetime                      # Time of Closest Approach
    miss_distance_km: float
    relative_velocity_km_s: float
    primary_state: StateVector
    secondary_state: StateVector
    primary_covariance: CovarianceMatrix
    secondary_covariance: CovarianceMatrix


@dataclass
class RiskResult:
    """Final output of the Pc calculation pipeline."""
    conjunction: ConjunctionEvent
    pc: float                          # Probability of Collision [0, 1]
    combined_covariance: np.ndarray    # Combined 3×3 in B-plane
    hard_body_radius_m: float          # Combined physical radius
    b_plane_sigma_x: float             # Uncertainty semi-axis in B-plane (km)
    b_plane_sigma_z: float             # Uncertainty semi-axis in B-plane (km)
    method: str = "Foster2D"           # Which algorithm was used
    monte_carlo_samples: int = 0       # If MC was run, how many
    warning_level: str = "GREEN"       # GREEN / YELLOW / RED

    def __post_init__(self):
        if self.pc >= 1e-3:
            object.__setattr__(self, 'warning_level', 'RED')
        elif self.pc >= 1e-5:
            object.__setattr__(self, 'warning_level', 'YELLOW')
