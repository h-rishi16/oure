"""
OURE Uncertainty Modeling - Process Noise Model
===============================================
"""

import numpy as np


class ProcessNoiseModel:
    """Model for process noise (Q) to account for unmodelled forces."""

    def __init__(self, q_scale: float = 1e-10):
        self.q_scale = q_scale

    def get_noise_matrix(self, dt_seconds: float) -> np.ndarray:
        """Returns the 6x6 process noise covariance matrix."""
        q = np.zeros((6, 6))
        id_matrix = np.eye(3)

        q[:3, :3] = id_matrix * self.q_scale * (dt_seconds**3) / 3.0
        q[3:, 3:] = id_matrix * self.q_scale * dt_seconds
        q[:3, 3:] = id_matrix * self.q_scale * (dt_seconds**2) / 2.0
        q[3:, :3] = id_matrix * self.q_scale * (dt_seconds**2) / 2.0

        return q
