"""
OURE Risk Calculation - Maneuver Optimizer
==========================================
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from scipy.optimize import minimize

from oure.conjunction.tca_finder import TCARefinementEngine
from oure.core.models import ConjunctionEvent, CovarianceMatrix, StateVector
from oure.physics.base import BasePropagator
from oure.physics.maneuver import Maneuver, ManeuverPropagator
from oure.risk.calculator import RiskCalculator

logger = logging.getLogger("oure.risk.optimizer")


class ManeuverOptimizer:
    """
    Uses Sequential Least Squares Programming (SLSQP) to find the minimum-fuel
    maneuver that successfully lowers the Probability of Collision below a
    specified safety threshold.
    """

    def __init__(
        self,
        base_prop: BasePropagator,
        primary_state: StateVector,
        secondary_state: StateVector,
        primary_cov: CovarianceMatrix,
        secondary_cov: CovarianceMatrix,
        burn_epoch: datetime,
        target_pc: float = 1e-5,
        hard_body_radius_m: float = 20.0,
    ):
        self.base_prop = base_prop
        self.primary_state = primary_state
        self.secondary_state = secondary_state
        self.primary_cov = primary_cov
        self.secondary_cov = secondary_cov
        self.burn_epoch = burn_epoch
        self.target_pc = target_pc

        self.tca_finder = TCARefinementEngine(
            tolerance_seconds=0.5
        )  # Looser tolerance for speed during optimization
        self.risk_calc = RiskCalculator(hard_body_radius_m=hard_body_radius_m)

        # Find the nominal TCA to bound our search windows
        tca_res = self.tca_finder.find_tca(
            self.primary_state,
            self.base_prop,
            self.secondary_state,
            self.base_prop,
            self.burn_epoch,
            self.burn_epoch + timedelta(hours=72),
        )
        if not tca_res:
            raise ValueError("No baseline conjunction found in the look-ahead window.")
        self.nominal_tca = tca_res[0]

    def optimize(self, max_dv_km_s: float = 0.01) -> dict[str, Any]:
        """
        Runs the SLSQP optimizer to find the optimal 3D Delta-V vector.
        max_dv_km_s: Maximum allowable thrust in km/s (default 10 m/s).
        """
        # Pre-propagate the secondary to the nominal TCA *once*.
        # The secondary is unaffected by our maneuver — its TCA state is constant.
        # Without this, it is re-propagated on every single SLSQP function evaluation.
        s_tca_nominal = self.base_prop.propagate_to(
            self.secondary_state, self.nominal_tca
        )

        # Pre-propagate primary to burn epoch for the initial-guess velocity direction.
        burn_state = self.base_prop.propagate_to(self.primary_state, self.burn_epoch)

        def objective(dv: np.ndarray) -> float:
            """Objective: Minimize the magnitude of the Delta-V vector (save fuel)."""
            return float(np.sum(dv**2) * 1e6)

        def constraint_pc(dv: np.ndarray) -> float:
            """
            Constraint: Target Pc - Actual Pc >= 0
            (Actual Pc must be less than or equal to Target Pc)
            """
            maneuver = Maneuver(burn_epoch=self.burn_epoch, delta_v_eci=dv)
            man_prop = ManeuverPropagator(self.base_prop, [maneuver])

            # Narrow search window to ±1h — find_tca now exits fast when no
            # minimum exists, so a tight window adds negligible overhead.
            tca_res = self.tca_finder.find_tca(
                self.primary_state,
                man_prop,
                self.secondary_state,
                self.base_prop,
                self.nominal_tca - timedelta(hours=1),
                self.nominal_tca + timedelta(hours=1),
            )

            if not tca_res:
                return self.target_pc  # No conjunction found — constraint satisfied

            new_tca, new_miss = tca_res

            p_tca = man_prop.propagate_to(self.primary_state, new_tca)
            # Re-use the pre-propagated secondary state if the TCA hasn't shifted much
            if abs((new_tca - self.nominal_tca).total_seconds()) < 60.0:
                s_tca = s_tca_nominal
            else:
                s_tca = self.base_prop.propagate_to(self.secondary_state, new_tca)

            v_rel = float(np.linalg.norm(p_tca.v - s_tca.v))

            event = ConjunctionEvent(
                primary_id=self.primary_state.sat_id,
                secondary_id=self.secondary_state.sat_id,
                tca=new_tca,
                miss_distance_km=new_miss,
                relative_velocity_km_s=v_rel,
                primary_state=p_tca,
                secondary_state=s_tca,
                primary_covariance=self.primary_cov,
                secondary_covariance=self.secondary_cov,
            )

            risk = self.risk_calc.compute_pc(event)
            return self.target_pc - risk.pc

        v_hat = burn_state.v / np.linalg.norm(burn_state.v)
        x0 = v_hat * 1e-5  # 1 cm/s prograde initial guess

        bnds = [(-max_dv_km_s, max_dv_km_s)] * 3
        cons = {"type": "ineq", "fun": constraint_pc}

        logger.info("Starting SLSQP maneuver optimization...")
        res = minimize(
            fun=objective,
            x0=x0,
            method="SLSQP",
            bounds=bnds,
            constraints=cons,
            options={"disp": False, "ftol": 1e-8, "maxiter": 25},
        )

        if res.success:
            optimal_dv = res.x
            # Calculate final Pc to return
            margin = constraint_pc(optimal_dv)
            final_pc = self.target_pc - margin
            return {
                "success": True,
                "optimal_dv_km_s": optimal_dv,
                "dv_mag_cm_s": np.linalg.norm(optimal_dv) * 100000.0,
                "final_pc": final_pc,
                "iterations": res.nit,
            }
        else:
            return {
                "success": False,
                "message": res.message,
                "optimal_dv_km_s": np.zeros(3),
            }
