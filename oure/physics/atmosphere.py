"""
OURE Physics Engine - Atmospheric Model
=======================================
"""

import math
from enum import Enum

import numpy as np

from oure.core import constants


class AtmosphereType(Enum):
    STANDARD_EXPONENTIAL = "STANDARD"
    NASA_MSFC_JACCHIA = "NASA_MSFC"


class AtmosphericModel:
    """
    Computes atmospheric density. Supports standard exponential and
    NASA Marshall Space Flight Center (MSFC) / Jacchia approximations.
    """

    # Basic exponential table (h0, rho0, H)
    ATMO_TABLE = [
        (200, 2.789e-10, 6.3),
        (300, 1.916e-11, 7.3),
        (400, 2.803e-12, 7.9),
        (500, 5.215e-13, 8.7),
        (600, 1.137e-13, 9.3),
        (700, 3.070e-14, 9.9),
    ]

    def __init__(
        self,
        solar_flux: float = 150.0,
        model_type: AtmosphereType = AtmosphereType.NASA_MSFC_JACCHIA,
    ):
        self.f10_7 = solar_flux
        self.model_type = model_type

    def get_density(self, altitude_km: float) -> float:
        alt = max(200, min(700, altitude_km))

        if self.model_type == AtmosphereType.NASA_MSFC_JACCHIA:
            return self._nasa_msfc_density(alt)
        else:
            return self._standard_density(alt)

    def _standard_density(self, alt: float) -> float:
        for i in range(len(self.ATMO_TABLE) - 1):
            h0, rho0, H = self.ATMO_TABLE[i]
            h1, _, _ = self.ATMO_TABLE[i + 1]
            is_last = i == len(self.ATMO_TABLE) - 2

            if h0 <= alt < h1 or (is_last and alt == h1):
                rho = rho0 * math.exp(-(alt - h0) / H)
                rho *= math.exp(
                    constants.JACCHIA_SOLAR_COUPLING
                    * (self.f10_7 - constants.SOLAR_FLUX_MEAN_SFU)
                )
                return rho
        return 1e-14

    def _nasa_msfc_density(self, alt: float) -> float:
        """
        NASA MSFC / Jacchia analytical approximation for exospheric density.
        Accounts for solar flux variations more accurately at high altitudes.
        """
        # Base exospheric temperature estimation from F10.7
        t_exospheric = 900.0 + 2.5 * (self.f10_7 - 70.0)

        # Jacchia analytical fit coefficients
        rho_base = 6.0e-10 * math.exp(-(alt - 175.0) / 50.0)

        # Temperature modifier
        t_modifier = (t_exospheric / 1000.0) ** 4.0

        # High altitude correction factor
        scale_height = 40.0 + 0.2 * alt

        rho = rho_base * t_modifier * math.exp(-(alt - 200.0) / scale_height)
        return float(max(rho, 1e-15))

    def get_density_vectorized(self, altitude_km: np.ndarray) -> np.ndarray:
        alt = np.clip(altitude_km, 200, 700)
        rho = np.full_like(alt, 1e-14, dtype=float)

        if self.model_type == AtmosphereType.NASA_MSFC_JACCHIA:
            t_exospheric = 900.0 + 2.5 * (self.f10_7 - 70.0)
            rho_base = 6.0e-10 * np.exp(-(alt - 175.0) / 50.0)
            t_modifier = (t_exospheric / 1000.0) ** 4.0
            scale_height = 40.0 + 0.2 * alt
            rho_msfc = rho_base * t_modifier * np.exp(-(alt - 200.0) / scale_height)
            rho = np.maximum(rho_msfc, 1e-15)
        else:
            solar_corr = math.exp(
                constants.JACCHIA_SOLAR_COUPLING
                * (self.f10_7 - constants.SOLAR_FLUX_MEAN_SFU)
            )

            for i in range(len(self.ATMO_TABLE) - 1):
                h0, rho0, H = self.ATMO_TABLE[i]
                h1, _, _ = self.ATMO_TABLE[i + 1]
                is_last = i == len(self.ATMO_TABLE) - 2

                if is_last:
                    mask = (alt >= h0) & (alt <= h1)
                else:
                    mask = (alt >= h0) & (alt < h1)

                if np.any(mask):
                    rho[mask] = rho0 * np.exp(-(alt[mask] - h0) / H) * solar_corr

        return rho
