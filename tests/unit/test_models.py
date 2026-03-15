from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import numpy as np
import pytest

from oure.core.models import CovarianceMatrix, StateVector


def test_state_vector_frozen():
    state = StateVector(
        r=np.array([1.0, 2.0, 3.0]),
        v=np.array([0.1, 0.2, 0.3]),
        epoch=datetime.now(UTC),
        sat_id="25544",
    )
    with pytest.raises(FrozenInstanceError):
        state.r = np.array([2.0, 3.0, 4.0])

    assert state.speed_km_s > 0
    assert (
        state.altitude_km > -6378.137
    )  # Cannot be negative altitude basically below center of earth


def test_covariance_matrix_properties():
    cov = CovarianceMatrix(matrix=np.eye(6), epoch=datetime.now(UTC), sat_id="25544")

    assert cov.is_positive_definite
    assert cov.position_block.shape == (3, 3)
    assert cov.velocity_block.shape == (3, 3)
