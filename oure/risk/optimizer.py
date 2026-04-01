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
from oure.core.models import ConjunctionEvent, CovarianceMatrix, StateVector, OptimizationResult
from oure.physics.base import BasePropagator
from oure.physics.maneuver import Maneuver, ManeuverPropagator
from oure.risk.calculator import RiskCalculator

logger = logging.getLogger("oure.risk.optimizer")


class ManeuverOptimizer:
    """
    Finds the optimal Delta-V to mitigate collision risk.
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
    ):
        self.base_prop = base_prop
        self.primary_state = primary_state
        self.secondary_state = secondary_state
        self.primary_cov = primary_cov
        self.secondary_cov = secondary_cov
        self.burn_epoch = burn_epoch
        self.target_pc = target_pc

        self.tca_finder = TCARefinementEngine()
        self.risk_calc = RiskCalculator()

        # Find the nominal TCA (without maneuver)
        search_start = self.primary_state.epoch
        search_end = search_start + timedelta(hours=72)
        res = self.tca_finder.find_tca(
            primary_state,
            base_prop,
            secondary_state,
            base_prop,
            search_start,
            search_end,
        )
        if not res:
            raise ValueError("No nominal conjunction found to optimize.")

        self.nominal_tca, self.nominal_miss = res

    def optimize(self, max_dv_km_s: float = 0.05) -> OptimizationResult:
        """
        Runs SLSQP optimization to find minimum Delta-V.
        """
        # Pre-propagate secondary to nominal TCA once to save time in loop
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
                return self.target_pc  # No collision = constraint satisfied

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
        res = minimize(  # type: ignore[call-overload]
            fun=objective,
            x0=x0,
            method="SLSQP",
            bounds=bnds,
            constraints=cons,
            options={"disp": False, "ftol": 1e-8, "maxiter": 25},
        )

        if res.success:
            optimal_dv = res.x
            # Re-evaluate the final state and true Pc
            man = Maneuver(burn_epoch=self.burn_epoch, delta_v_eci=optimal_dv)
            man_prop = ManeuverPropagator(self.base_prop, [man])

            tca_res = self.tca_finder.find_tca(
                self.primary_state,
                man_prop,
                self.secondary_state,
                self.base_prop,
                self.nominal_tca - timedelta(minutes=5),
                self.nominal_tca + timedelta(minutes=5),
            )

            if tca_res:
                final_tca, final_miss = tca_res
                p_final = man_prop.propagate_to(self.primary_state, final_tca)
                s_final = self.base_prop.propagate_to(self.secondary_state, final_tca)
                v_rel = float(np.linalg.norm(p_final.v - s_final.v))

                final_event = ConjunctionEvent(
                    primary_id=self.primary_state.sat_id,
                    secondary_id=self.secondary_state.sat_id,
                    tca=final_tca,
                    miss_distance_km=final_miss,
                    relative_velocity_km_s=v_rel,
                    primary_state=p_final,
                    secondary_state=s_final,
                    primary_covariance=self.primary_cov,
                    secondary_covariance=self.secondary_cov,
                )
                final_risk = self.risk_calc.compute_pc(final_event)
                final_pc = final_risk.pc
            else:
                # Fallback to algebraic calc if refinement fails
                margin = constraint_pc(optimal_dv)
                final_pc = self.target_pc - margin

            return OptimizationResult(
                optimal_dv_km_s=optimal_dv,
                final_pc=final_pc,
                iterations=res.nit,
                success=True,
                message="Optimization successful",
            )
        else:
            return OptimizationResult(
                optimal_dv_km_s=np.zeros(3),
                final_pc=0.0,
                iterations=res.nit,
                success=False,
                message=res.message,
            )
