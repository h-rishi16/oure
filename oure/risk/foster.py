"""
OURE Risk Calculation - Foster's Algorithm
==========================================
"""

from __future__ import annotations

from enum import Enum
from math import exp, pi, sqrt

import numpy as np
from scipy.integrate import dblquad
from scipy.special import gammainc


class PcMethod(str, Enum):
    NUMERICAL = 'numerical'
    FOSTER_SERIES = 'series'

class FosterPcCalculator:
    """
    Probability of Collision via Foster's 2D B-plane integral.
    """

    def __init__(
        self,
        hard_body_radius_km: float,
        method: PcMethod = PcMethod.NUMERICAL,
        integration_sigma: float = 5.0,
        series_terms: int = 200,
    ):
        self.R = hard_body_radius_km
        self.method = method
        self.integration_sigma = integration_sigma
        self.series_terms = series_terms

    def compute(self, b_miss: np.ndarray, C_2d: np.ndarray) -> float:
        """
        Computes the Probability of Collision (Pc).
        """
        if self.method == PcMethod.NUMERICAL:
            return self._numerical_integration(b_miss, C_2d)
        else:
            return self._foster_series(b_miss, C_2d)

    def _numerical_integration(self, b: np.ndarray, C: np.ndarray) -> float:
        C_inv = np.linalg.inv(C)
        det_C = np.linalg.det(C)
        if det_C <= 0:
            return 0.0
        norm_factor = 1.0 / (2 * pi * sqrt(det_C))
        R_sq = self.R**2

        def integrand(zeta: float, xi: float) -> float:
            if xi**2 + zeta**2 > R_sq:
                return 0.0
            u = np.array([xi - b[0], zeta - b[1]])
            return norm_factor * exp(-0.5 * u @ C_inv @ u)

        sigma_x = sqrt(C[0, 0])
        sigma_z = sqrt(C[1, 1])
        xi_lo = -self.integration_sigma * sigma_x
        xi_hi = self.integration_sigma * sigma_x

        result, _ = dblquad(
            integrand,
            xi_lo, xi_hi,
            lambda xi: -self.integration_sigma * sigma_z,
            lambda xi: self.integration_sigma * sigma_z,
            epsabs=1e-12, epsrel=1e-8,
        )
        return float(np.clip(result, 0.0, 1.0))

    def _foster_series(self, b: np.ndarray, C: np.ndarray) -> float:
        eigenvalues, _ = np.linalg.eigh(C)
        lam1, lam2 = sorted(eigenvalues)
        if lam1 <= 0 or lam2 <= 0:
            return 0.0

        miss_sq = float(b @ np.linalg.inv(C) @ b)
        u = miss_sq / 2.0
        v = self.R**2 / (2 * lam1)

        pc = 0.0

        # Iteratively calculate the terms to avoid large factorials
        # The term is (exp(-u) * u**n) / n!
        log_term = -u
        for n in range(self.series_terms):
            if n > 0:
                log_term += np.log(u) - np.log(n)

            weight = np.exp(log_term)
            gamma_term = gammainc(n + 1, v)
            pc += weight * gamma_term

        return float(np.clip(pc * pi * self.R**2 / (2 * pi * sqrt(lam1 * lam2)), 0, 1))
