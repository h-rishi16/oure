"""
OURE Physics Engine - Base
==========================
Abstract base class for all orbit propagators.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import numpy as np

from oure.core.models import StateVector


class BasePropagator(ABC):
    """
    Abstract base for all orbit propagators.
    """

    @abstractmethod
    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        """Advance state by dt_seconds from state.epoch."""
        ...

    @abstractmethod
    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        """Propagate to an absolute UTC epoch."""
        ...

    @abstractmethod
    def propagate_many_to(self, states: np.ndarray, initial_epoch: datetime, target_epoch: datetime) -> np.ndarray:
        """Propagate a batch of states (N, 6) from initial_epoch to target_epoch."""
        ...

    def propagate_sequence(self, state: StateVector, epochs: list[datetime]) -> list[StateVector]:
        """Propagate to a list of epochs."""
        return [self.propagate_to(state, t) for t in epochs]
