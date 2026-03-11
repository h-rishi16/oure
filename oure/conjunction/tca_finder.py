"""
OURE Conjunction Assessment - TCA Finder
========================================
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from oure.core.models import StateVector
from oure.physics.base import BasePropagator


class TCARefinementEngine:
    """
    Golden-section search for Time of Closest Approach.
    Minimises ρ(t) = |r_p(t) - r_s(t)| over a time window.
    """

    GOLDEN_RATIO: float = (np.sqrt(5) - 1) / 2

    def __init__(self, tolerance_seconds: float = 0.1, max_iterations: int = 100):
        self.tolerance_seconds = tolerance_seconds
        self.max_iterations = max_iterations

    def find_tca(
        self,
        primary_state: StateVector,
        primary_propagator: BasePropagator,
        secondary_state: StateVector,
        secondary_propagator: BasePropagator,
        search_start: datetime,
        search_end: datetime,
    ) -> tuple[datetime, float] | None:
        """
        Finds the Time of Closest Approach (TCA) and miss distance.
        
        Returns:
            A tuple of (tca_epoch, miss_distance_km), or None if no valid TCA is found.
        """
        dt_span = (search_end - search_start).total_seconds()
        a, b = 0.0, dt_span

        for _ in range(self.max_iterations):
            c = b - self.GOLDEN_RATIO * (b - a)
            d = a + self.GOLDEN_RATIO * (b - a)

            if self._range_at(c, search_start, primary_state, primary_propagator, secondary_state, secondary_propagator) < self._range_at(d, search_start, primary_state, primary_propagator, secondary_state, secondary_propagator):
                b = d
            else:
                a = c

            if abs(b - a) < self.tolerance_seconds:
                break

        tca_offset = (a + b) / 2.0
        tca_epoch = search_start + timedelta(seconds=tca_offset)

        miss_distance_km = self._range_at(tca_offset, search_start, primary_state, primary_propagator, secondary_state, secondary_propagator)

        return tca_epoch, miss_distance_km

    def _range_at(
        self,
        dt_offset: float,
        start_epoch: datetime,
        p_state: StateVector,
        p_prop: BasePropagator,
        s_state: StateVector,
        s_prop: BasePropagator
    ) -> float:
        t = start_epoch + timedelta(seconds=dt_offset)
        rp = p_prop.propagate_to(p_state, t).r
        rs = s_prop.propagate_to(s_state, t).r
        return float(np.linalg.norm(rp - rs))
