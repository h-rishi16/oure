from datetime import timedelta
from unittest.mock import MagicMock

import numpy as np

from oure.core.models import CovarianceMatrix
from oure.uncertainty.monte_carlo import MonteCarloUncertaintyPropagator


def test_monte_carlo_generator(dummy_state):
    cov = CovarianceMatrix(
        matrix=np.eye(6) * 1e-6, epoch=dummy_state.epoch, sat_id="12345"
    )

    mock_prop = MagicMock()
    # Mock the propagate_many_to to return identical perturbed states
    mock_prop.propagate_many_to.side_effect = lambda states, start, end: states

    generator = MonteCarloUncertaintyPropagator(propagator=mock_prop, n_samples=100)
    result = generator.run(
        dummy_state, cov, target_epoch=dummy_state.epoch + timedelta(seconds=60)
    )
    assert result.sample_covariance.shape == (6, 6)
    assert len(result.ghost_states) == 100
