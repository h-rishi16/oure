"""
OURE Risk Calculation - B-Plane Projection
==========================================
"""

from __future__ import annotations

import numpy as np

from oure.core.exceptions import BPlaneError
from oure.core.models import BPlaneProjection, ConjunctionEvent


class BPlaneProjector:
    """
    Constructs the B-plane reference frame and projects covariances.
    """

    def project(self, event: ConjunctionEvent) -> BPlaneProjection:
        """
        Projects the conjunction event onto the B-plane.
        """
        r_p = event.primary_state.r
        r_s = event.secondary_state.r
        v_p = event.primary_state.v
        v_s = event.secondary_state.v

        dr = r_p - r_s
        dv = v_p - v_s

        v_mag = np.linalg.norm(dv)
        if v_mag < 1e-9:
            raise BPlaneError("Relative velocity is near zero, B-plane is undefined.")

        v_hat = dv / v_mag

        ref = np.array([0.0, 0.0, 1.0])
        if abs(np.dot(v_hat, ref)) > 0.99:
            ref = np.array([0.0, 1.0, 0.0])

        xi_hat = np.cross(ref, v_hat)
        xi_hat /= np.linalg.norm(xi_hat)
        zeta_hat = np.cross(v_hat, xi_hat)
        zeta_hat /= np.linalg.norm(zeta_hat)

        T = np.array([xi_hat, zeta_hat])

        # 2x6 projection matrix to project 6x6 covariance onto the 2D B-plane
        T_full = np.zeros((2, 6))
        T_full[:, :3] = T

        C_combined_6x6 = (
            event.primary_covariance.matrix + event.secondary_covariance.matrix
        )

        C_2d = T_full @ C_combined_6x6 @ T_full.T
        b_vec_2d = T @ dr

        return BPlaneProjection(
            xi_hat=xi_hat,
            zeta_hat=zeta_hat,
            T_matrix=T,
            b_vec_2d=b_vec_2d,
            C_2d=C_2d,
        )
