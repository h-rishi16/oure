from datetime import datetime, timezone
from unittest.mock import MagicMock

import numpy as np

from oure.core.models import StateVector
from oure.physics.srp_corrector import SRPCorrector


def test_srp_corrector_basic():
    mock_base = MagicMock()
    # Mock return a state
    epoch = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)
    state = StateVector(
        r=np.array([7000, 0, 0]), v=np.array([0, 7.5, 0]), epoch=epoch, sat_id="1"
    )
    mock_base.propagate.return_value = state

    corrector = SRPCorrector(mock_base, cr=1.2, area_m2=10.0, mass_kg=500.0)

    # Test propagate
    new_state = corrector.propagate(state, 60.0)
    assert isinstance(new_state, StateVector)
    # Positions should change due to SRP dr
    assert not np.array_equal(new_state.r, state.r)


def test_srp_corrector_vectorized():
    mock_base = MagicMock()
    epoch = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)
    states = np.array([[7000, 0, 0, 0, 7.5, 0]])
    mock_base.propagate_many_to.return_value = states

    corrector = SRPCorrector(mock_base, cr=1.2, area_m2=10.0, mass_kg=500.0)
    new_states = corrector.propagate_many_to(states, epoch, epoch)
    # If dt=0, states should be same (though _apply_srp_vectorized is called after base)
    # Actually propagate_many_to computes dt.

    # dt = 0 case
    assert np.array_equal(new_states, states)

    # dt > 0 case
    future = datetime(2026, 3, 15, 13, 0, tzinfo=timezone.utc)
    new_states_future = corrector.propagate_many_to(states, epoch, future)
    assert not np.array_equal(new_states_future, states)
