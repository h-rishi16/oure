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
        Q = np.zeros((6, 6))
        I = np.eye(3)
        
        Q[:3, :3] = I * self.q_scale * (dt_seconds**3) / 3.0
        Q[3:, 3:] = I * self.q_scale * dt_seconds
        Q[:3, 3:] = I * self.q_scale * (dt_seconds**2) / 2.0
        Q[3:, :3] = I * self.q_scale * (dt_seconds**2) / 2.0
        
        return Q
