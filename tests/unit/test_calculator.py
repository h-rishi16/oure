from datetime import UTC, datetime

import numpy as np
import pytest

from oure.core.models import ConjunctionEvent, CovarianceMatrix, StateVector
from oure.risk.calculator import RiskCalculator
from oure.risk.foster import PcMethod


@pytest.fixture
def dummy_state_primary():
    return StateVector(
        r=np.array([7000.0, 0.0, 0.0]),
        v=np.array([0.0, 7.5, 0.0]),
        epoch=datetime.now(UTC),
        sat_id="1"
    )

@pytest.fixture
def dummy_state_secondary():
    return StateVector(
        r=np.array([7001.0, 0.0, 0.0]),
        v=np.array([0.0, 7.4, 0.1]),
        epoch=datetime.now(UTC),
        sat_id="2"
    )

def test_risk_calculator(dummy_state_primary, dummy_state_secondary):
    calc = RiskCalculator(hard_body_radius_m=20.0)
    calc.pc_calculator.method = PcMethod.FOSTER_SERIES

    cov1 = CovarianceMatrix(matrix=np.eye(6)*0.01, epoch=dummy_state_primary.epoch, sat_id="1")
    cov2 = CovarianceMatrix(matrix=np.eye(6)*0.01, epoch=dummy_state_secondary.epoch, sat_id="2")

    event = ConjunctionEvent(
        primary_id="1", secondary_id="2",
        tca=dummy_state_primary.epoch,
        miss_distance_km=0.1,
        relative_velocity_km_s=10.0,
        primary_state=dummy_state_primary,
        secondary_state=dummy_state_secondary,
        primary_covariance=cov1,
        secondary_covariance=cov2
    )

    result = calc.compute_pc(event)
    assert result.pc >= 0.0
