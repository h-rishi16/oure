"""
OURE Physics Engine - Maneuver Trade-Space Simulator
====================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from oure.core.models import StateVector
from oure.physics.base import BasePropagator


@dataclass
class Maneuver:
    """Represents an impulsive thruster burn."""
    burn_epoch: datetime
    delta_v_eci: np.ndarray  # shape (3,) in km/s

class ManeuverPropagator(BasePropagator):
    """
    Wraps a High-Precision Numerical Propagator to inject delta-V
    maneuvers exactly at their execution epochs.
    """

    def __init__(self, base_propagator: BasePropagator, maneuvers: list[Maneuver]):
        self._base = base_propagator
        # Sort maneuvers chronologically
        self.maneuvers = sorted(maneuvers, key=lambda m: m.burn_epoch)

    def propagate(self, state: StateVector, dt_seconds: float) -> StateVector:
        from datetime import timedelta
        target_epoch = state.epoch + timedelta(seconds=dt_seconds)
        return self.propagate_to(state, target_epoch)

    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        current_state = state

        # If propagating forward
        if target_epoch >= state.epoch:
            for man in self.maneuvers:
                if current_state.epoch < man.burn_epoch <= target_epoch:
                    # 1. Propagate up to the exact moment of the burn
                    current_state = self._base.propagate_to(current_state, man.burn_epoch)

                    # 2. Inject the delta-v (instantaneous velocity change)
                    new_v = current_state.v + man.delta_v_eci
                    current_state = StateVector(
                        r=current_state.r,
                        v=new_v,
                        epoch=man.burn_epoch,
                        sat_id=current_state.sat_id
                    )

        # 3. Propagate the rest of the way to the target epoch
        if current_state.epoch != target_epoch:
            current_state = self._base.propagate_to(current_state, target_epoch)

        return current_state

    def propagate_many_to(self, states: np.ndarray, initial_epoch: datetime, target_epoch: datetime) -> np.ndarray:
        raise NotImplementedError("Maneuver propagation is not yet vectorized.")
