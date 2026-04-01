from datetime import timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from oure.core.models import (
    CovarianceMatrix,
    OptimizationResult,
    RiskResult,
    StateVector,
)
from oure.physics.numerical import NumericalPropagator
from oure.risk.optimizer import ManeuverOptimizer


@pytest.fixture
def base_states():
    from datetime import UTC, datetime

    epoch = datetime(2026, 4, 1, 12, 58, 27, 400021, tzinfo=UTC)
    primary = StateVector(
        r=np.array([7000, 0, 0]), v=np.array([0, 7.5, 0]), epoch=epoch, sat_id="1"
    )
    secondary = StateVector(
        r=np.array([7000.05, 0, 0]), v=np.array([0, -7.5, 0]), epoch=epoch, sat_id="2"
    )
    cov = CovarianceMatrix(matrix=np.eye(6) * 1e-6, epoch=epoch, sat_id="1")
    return primary, secondary, cov, epoch


def test_maneuver_optimizer(base_states):
    """
    Verifies that ManeuverOptimizer calls SLSQP and returns the expected
    result dict. The propagator and TCA finder are mocked so this test
    runs in milliseconds instead of hanging for 30+ minutes.
    """
    primary, secondary, cov, epoch = base_states
    burn_epoch = epoch + timedelta(minutes=10)
    nominal_tca = epoch + timedelta(minutes=45)
    nominal_miss = 0.05  # km — close enough to trigger the risk constraint

    # Build a mock propagator that returns a plausible state instantly
    mock_state = MagicMock()
    mock_state.r = np.array([7000.0, 100.0, 0.0])
    mock_state.v = np.array([0.0, 7.5, 0.1])

    mock_prop = MagicMock(spec=NumericalPropagator)
    mock_prop.propagate_to.return_value = mock_state

    # Mock the TCA finder: first call (in __init__) returns nominal TCA,
    # subsequent calls (in constraint_pc) return a slightly shifted TCA.
    mock_tca_result = (nominal_tca, nominal_miss)

    with patch(
        "oure.risk.optimizer.TCARefinementEngine.find_tca",
        return_value=mock_tca_result,
    ):
        # Mock the risk calculator so it returns a high Pc initially,
        # then low Pc after a maneuver — allowing the optimizer to converge.
        call_count = {"n": 0}

        def mock_compute_pc(event):
            call_count["n"] += 1
            pc = 1e-3 if call_count["n"] <= 3 else 1e-6
            result = MagicMock(spec=RiskResult)
            result.pc = pc
            result.warning_level = "GREEN" if pc < 1e-5 else "RED"
            return result

        with patch(
            "oure.risk.optimizer.RiskCalculator.compute_pc",
            side_effect=mock_compute_pc,
        ):
            optimizer = ManeuverOptimizer(
                base_prop=mock_prop,
                primary_state=primary,
                secondary_state=secondary,
                primary_cov=cov,
                secondary_cov=cov,
                burn_epoch=burn_epoch,
                target_pc=1e-5,
            )

            result = optimizer.optimize()

            assert isinstance(result, OptimizationResult)
            assert result.success is True
            assert result.final_pc < 1e-5
            assert len(result.optimal_dv_km_s) == 3
