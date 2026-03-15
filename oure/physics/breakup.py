"""
OURE Physics Engine - Space Debris Breakup Model
================================================
Simplified implementation inspired by the NASA Standard Breakup Model.
"""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np

from oure.core.models import StateVector

logger = logging.getLogger("oure.physics.breakup")


class BreakupModel:
    """
    Simulates a hypervelocity collision between two satellites and generates
    a fragment cloud state distribution at the Time of Closest Approach (TCA).
    """

    @staticmethod
    def simulate_collision(
        state1: StateVector,
        mass1_kg: float,
        state2: StateVector,
        mass2_kg: float,
        tca: datetime,
        num_fragments: int = 1000,
        random_seed: int | None = 42,
    ) -> list[StateVector]:
        """
        Simulates the collision and returns a list of StateVectors for the debris.

        Args:
            state1, state2: The exact state vectors of the objects at TCA.
            mass1_kg, mass2_kg: Masses of the colliding bodies.
            tca: Time of Closest Approach (the moment of impact).
            num_fragments: How many debris pieces to simulate.
        """
        rng = np.random.default_rng(random_seed)

        # 1. Collision Kinematics
        # Assume an inelastic collision to find the center of mass velocity
        v1 = state1.v
        v2 = state2.v
        m_tot = mass1_kg + mass2_kg
        v_com = (mass1_kg * v1 + mass2_kg * v2) / m_tot

        # The collision occurs at the primary's position (simplification)
        r_impact = state1.r

        # Relative velocity
        v_rel = np.linalg.norm(v1 - v2)  # km/s

        # 2. Fragment Velocity Dispersion (Simplified NASA SBM)
        # Use v_rel to scale the mean dispersion speed
        # Fragments from hypervelocity impacts typically have mean dV proportional to v_impact^0.5
        v_impact = float(v_rel)
        mu_log_dv = np.log(0.02 * np.sqrt(v_impact))
        sigma_log_dv = 0.55  # NASA SBM standard variance for log10(dv)

        dv_magnitudes = rng.lognormal(
            mean=mu_log_dv, sigma=sigma_log_dv, size=num_fragments
        )  # km/s
        # Cap extremely high velocities that exceed escape velocity unexpectedly
        # (hypervelocity impacts can cause this, but we bound it for simulation stability)
        dv_magnitudes = np.clip(dv_magnitudes, 0.001, 3.0)

        # Generate random spherical directions for the fragments
        phi = rng.uniform(0, 2 * np.pi, num_fragments)
        costheta = rng.uniform(-1, 1, num_fragments)
        theta = np.arccos(costheta)

        # Convert spherical to Cartesian unit vectors
        x_dir = np.sin(theta) * np.cos(phi)
        y_dir = np.sin(theta) * np.sin(phi)
        z_dir = np.cos(theta)

        directions = np.column_stack([x_dir, y_dir, z_dir])  # shape (N, 3)

        # Calculate final ECI velocity for each fragment: V_com + dV
        v_fragments = v_com + directions * dv_magnitudes[:, np.newaxis]

        # 3. Construct State Vectors
        debris_states = []
        for i in range(num_fragments):
            sv = StateVector(
                r=r_impact.copy(),  # All originate from impact point
                v=v_fragments[i],
                epoch=tca,
                sat_id=f"DEBRIS_{state1.sat_id}_{i:05d}",
            )
            debris_states.append(sv)

        logger.info(
            f"Simulated collision at {tca}. V_rel = {v_rel:.2f} km/s. Spawned {num_fragments} fragments."
        )

        return debris_states
