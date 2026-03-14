import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from oure.core.models import StateVector, CovarianceMatrix
from oure.physics.numerical import NumericalPropagator
from oure.risk.optimizer import ManeuverOptimizer

def test_maneuver_optimizer():
    primary_state = StateVector(
        r=np.array([7000.0, 0.0, 0.0]),
        v=np.array([0.0, 7.5, 0.0]),
        epoch=datetime.now(timezone.utc),
        sat_id="1"
    )
    # Secondary slightly offset to create a risk
    secondary_state = StateVector(
        r=np.array([7000.1, 0.0, 0.0]),
        v=np.array([0.0, -7.5, 0.0]),
        epoch=primary_state.epoch,
        sat_id="2"
    )
    
    cov = CovarianceMatrix(matrix=np.eye(6) * 0.01, epoch=primary_state.epoch, sat_id="1")
    
    prop = NumericalPropagator()
    burn_epoch = primary_state.epoch + timedelta(minutes=10)
    
    optimizer = ManeuverOptimizer(
        base_prop=prop,
        primary_state=primary_state,
        secondary_state=secondary_state,
        primary_cov=cov,
        secondary_cov=cov,
        burn_epoch=burn_epoch,
        target_pc=1e-5
    )
    
    result = optimizer.optimize()
    assert result["success"] is True
    assert "optimal_dv_km_s" in result
    assert result["final_pc"] <= 1e-5
