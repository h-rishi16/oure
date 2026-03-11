import numpy as np

from oure.core.models import CovarianceMatrix
from oure.uncertainty.covariance_propagator import CovariancePropagator
from oure.uncertainty.stm import STMCalculator


def test_covariance_propagator(dummy_state):
    cov = CovarianceMatrix(matrix=np.eye(6), epoch=dummy_state.epoch, sat_id="12345")
    stm_calc = STMCalculator(fidelity=1)
    propagator = CovariancePropagator(stm_calculator=stm_calc)

    new_cov = propagator.propagate(cov, reference_state=dummy_state, dt_seconds=60.0)
    assert new_cov.matrix.shape == (6, 6)
    assert new_cov.is_positive_definite
