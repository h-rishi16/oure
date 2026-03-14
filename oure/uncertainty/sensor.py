"""
OURE Sensor Tasking - Extended Kalman Filter Observation Update
===============================================================
Simulates the reduction in covariance when new radar measurements are taken.
"""

import numpy as np

from oure.core.models import CovarianceMatrix


class SensorTaskingSimulator:
    """
    Simulates a radar observation update using the Kalman Filter equations.
    This demonstrates how purchasing new sensor data shrinks the uncertainty
    ellipsoid and affects the Probability of Collision.
    """

    def __init__(self, sensor_noise_m: float = 10.0):
        # Default radar position accuracy (e.g., 10 meters)
        self.R = np.eye(3) * (sensor_noise_m / 1000.0)**2 # km^2

    def simulate_radar_update(self, prior_cov: CovarianceMatrix) -> CovarianceMatrix:
        """
        Applies a simulated position measurement update to the prior covariance.
        Uses the standard Kalman Filter covariance update equation:
            P_new = (I - K*H) * P_prior
        where:
            H = Observation model (we only observe position, so H is [I_3x3, 0_3x3])
            R = Measurement noise covariance (sensor accuracy)
            K = Kalman Gain = P_prior * H^T * (H * P_prior * H^T + R)^-1
        """
        P_minus = prior_cov.matrix

        # Observation matrix (we observe the first 3 state variables: x, y, z)
        H = np.zeros((3, 6))
        H[:, :3] = np.eye(3)

        # Innovation covariance (S = H*P*H^T + R)
        S = H @ P_minus @ H.T + self.R

        # Kalman Gain (K = P*H^T*S^-1)
        K = P_minus @ H.T @ np.linalg.inv(S)

        # Posterior covariance (P_plus = (I - K*H)*P_minus)
        I = np.eye(6)
        P_plus = (I - K @ H) @ P_minus

        # Ensure symmetry (Joseph form could also be used, but this is fine for simulation)
        P_plus = 0.5 * (P_plus + P_plus.T)

        return CovarianceMatrix(
            matrix=P_plus,
            epoch=prior_cov.epoch,
            sat_id=prior_cov.sat_id,
            frame=prior_cov.frame
        )
