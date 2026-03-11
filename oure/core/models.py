"""
OURE Core Data Models
=====================
Immutable dataclasses that flow between all layers of the system.
No business logic here — pure data containers with validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np

from . import constants

# ---------------------------------------------------------------------------
# Orbital State Representation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StateVector:
    """
    A satellite's position and velocity in ECI (Earth-Centered Inertial) frame.

    Attributes:
        r (np.ndarray): ECI position (km), shape (3,).
        v (np.ndarray): ECI velocity (km/s), shape (3,).
        epoch (datetime): UTC epoch for the state.
        sat_id (str): NORAD catalog ID string.
    """
    r: np.ndarray
    v: np.ndarray
    epoch: datetime
    sat_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.r, np.ndarray) or self.r.shape != (3,):
            raise TypeError("Position vector 'r' must be a NumPy array of shape (3,)")
        if not isinstance(self.v, np.ndarray) or self.v.shape != (3,):
            raise TypeError("Velocity vector 'v' must be a NumPy array of shape (3,)")

        # Use object.__setattr__ because the class is frozen
        object.__setattr__(self, 'r', self.r.astype(np.float64))
        object.__setattr__(self, 'v', self.v.astype(np.float64))

    @property
    def speed_km_s(self) -> float:
        """Returns the magnitude of the velocity vector in km/s."""
        return float(np.linalg.norm(self.v))

    @property
    def altitude_km(self) -> float:
        """Returns the approximate altitude above Earth's surface in km."""
        return float(np.linalg.norm(self.r) - constants.R_EARTH_KM)

    @property
    def state_vector_6d(self) -> np.ndarray:
        """Returns the concatenated 6D state vector [r, v]."""
        return np.concatenate([self.r, self.v])

    @property
    def is_in_leo(self) -> bool:
        """Checks if the satellite is in Low Earth Orbit (altitude < 2000 km)."""
        return self.altitude_km < 2000.0

    @property
    def orbital_energy(self) -> float:
        """Calculates the specific orbital energy in km²/s²."""
        return float((self.speed_km_s**2 / 2) - (constants.MU_KM3_S2 / np.linalg.norm(self.r)))

    @classmethod
    def from_6d(cls, vec: np.ndarray, epoch: datetime, sat_id: str) -> StateVector:
        """Creates a StateVector from a 6D NumPy array."""
        if vec.shape != (6,):
            raise ValueError("Input vector must have shape (6,)")
        return cls(r=vec[:3], v=vec[3:], epoch=epoch, sat_id=sat_id)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the StateVector to a dictionary."""
        return {
            "r": self.r.tolist(),
            "v": self.v.tolist(),
            "epoch": self.epoch.isoformat(),
            "sat_id": self.sat_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> StateVector:
        """Deserializes a StateVector from a dictionary."""
        return cls(
            r=np.array(d["r"]),
            v=np.array(d["v"]),
            epoch=datetime.fromisoformat(d["epoch"]),
            sat_id=d["sat_id"],
        )

    def __repr__(self) -> str:
        return f"StateVector(sat_id='{self.sat_id}', epoch='{self.epoch.isoformat()}')"


@dataclass(frozen=True)
class TLERecord:
    """
    Raw Two-Line Element set as fetched from Space-Track.
    """
    sat_id: str
    name: str
    line1: str
    line2: str
    epoch: datetime
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    inclination_deg: float = 0.0
    raan_deg: float = 0.0
    eccentricity: float = 0.0
    arg_perigee_deg: float = 0.0
    mean_anomaly_deg: float = 0.0
    mean_motion_rev_per_day: float = 0.0
    bstar: float = 0.0


@dataclass
class CovarianceMatrix:
    """
    6×6 position-velocity covariance in ECI frame.
    """
    matrix: np.ndarray
    epoch: datetime
    sat_id: str
    frame: str = "ECI"

    def __post_init__(self) -> None:
        self.matrix = np.asarray(self.matrix, dtype=np.float64)
        if self.matrix.shape != (6, 6):
            raise ValueError("Covariance must be 6×6")

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
        """Checks if the matrix is positive definite."""
        try:
            np.linalg.cholesky(self.matrix)
            return True
        except np.linalg.LinAlgError:
            return False


@dataclass(frozen=True)
class SolarFluxData:
    """F10.7 solar flux index."""
    date: datetime
    f10_7: float
    f10_7_81day_avg: float
    ap_index: float


@dataclass(frozen=True)
class AtmosphereParams:
    """Instantaneous atmosphere model parameters."""
    f10_7: float
    ap_index: float
    rho_ref: float
    scale_height_km: float


@dataclass
class ConjunctionEvent:
    """
    A predicted close approach between two satellites.
    """
    primary_id: str
    secondary_id: str
    tca: datetime
    miss_distance_km: float
    relative_velocity_km_s: float
    primary_state: StateVector
    secondary_state: StateVector
    primary_covariance: CovarianceMatrix
    secondary_covariance: CovarianceMatrix


@dataclass
class BPlaneProjection:
    """B-plane coordinate system and projected covariance."""
    xi_hat: np.ndarray
    zeta_hat: np.ndarray
    T_matrix: np.ndarray
    b_vec_2d: np.ndarray
    C_2d: np.ndarray


@dataclass
class RiskResult:
    """Final output of the Pc calculation pipeline."""
    conjunction: ConjunctionEvent
    pc: float
    combined_covariance: np.ndarray
    hard_body_radius_m: float
    b_plane_sigma_x: float
    b_plane_sigma_z: float
    warning_level: str = "GREEN"
    method: str = "Foster2D"
    monte_carlo_samples: int = 0




@dataclass(frozen=True)
class CacheEntry:
    """Represents a record in the SQLite key-value cache."""
    key: str
    value_json: str
    fetched_at: datetime
    ttl_s: float


@dataclass
class PipelineConfig:
    """Runtime configuration bundle for an analysis pipeline."""
    mc_samples: int = 1000
    screening_km: float = 5.0
    hbr_m: float = 20.0
    look_ahead_h: float = 72.0
    fidelity: int = 1
