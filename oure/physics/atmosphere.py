"""
OURE Physics Engine - Atmospheric Model
=======================================
"""

import math

import numpy as np

from oure.core import constants


class AtmosphericModel:
    """
    Simplified exponential atmosphere model.
    """

    ATMO_TABLE = [
        (200, 2.789e-10, 6.3),
        (300, 1.916e-11, 7.3),
        (400, 2.803e-12, 7.9),
        (500, 5.215e-13, 8.7),
        (600, 1.137e-13, 9.3),
        (700, 3.070e-14, 9.9),
    ]

    def __init__(self, solar_flux: float = 150.0):
        self.f10_7 = solar_flux

    def get_density(self, altitude_km: float) -> float:
        alt = max(200, min(700, altitude_km))
        for i in range(len(self.ATMO_TABLE) - 1):
            h0, rho0, H = self.ATMO_TABLE[i]
            h1, _, _ = self.ATMO_TABLE[i + 1]
            if h0 <= alt <= h1:
                rho = rho0 * math.exp(-(alt - h0) / H)
                rho *= math.exp(
                    constants.JACCHIA_SOLAR_COUPLING
                    * (self.f10_7 - constants.SOLAR_FLUX_MEAN_SFU)
                )
                return rho
        return 1e-14

    def get_density_vectorized(self, altitude_km: np.ndarray) -> np.ndarray:
        alt = np.clip(altitude_km, 200, 700)
        rho = np.full_like(alt, 1e-14)

        solar_corr = math.exp(
            constants.JACCHIA_SOLAR_COUPLING
            * (self.f10_7 - constants.SOLAR_FLUX_MEAN_SFU)
        )

        for i in range(len(self.ATMO_TABLE) - 1):
            h0, rho0, H = self.ATMO_TABLE[i]
            h1, _, _ = self.ATMO_TABLE[i + 1]

            mask = (alt >= h0) & (alt <= h1)
            if np.any(mask):
                rho[mask] = rho0 * np.exp(-(alt[mask] - h0) / H) * solar_corr

        return rho  # type: ignore
