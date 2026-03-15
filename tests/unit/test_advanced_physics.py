from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from oure.core.models import StateVector
from oure.physics.maneuver import Maneuver, ManeuverPropagator
from oure.physics.numerical import NumericalPropagator


@pytest.fixture
def initial_state():
    return StateVector(
        r=np.array([7000.0, 0.0, 0.0]),
        v=np.array([0.0, 7.5, 0.0]),
        epoch=datetime.now(UTC),
        sat_id="12345",
    )


def test_numerical_propagator(initial_state):
    prop = NumericalPropagator(solar_flux=150.0)
    # Propagate for 10 minutes
    new_state = prop.propagate(initial_state, 600.0)

    assert new_state.epoch == initial_state.epoch + timedelta(seconds=600)
    assert not np.array_equal(new_state.r, initial_state.r)
    assert new_state.speed_km_s > 0


def test_maneuver_injection(initial_state):
    base_prop = NumericalPropagator()
    burn_epoch = initial_state.epoch + timedelta(seconds=300)
    delta_v = np.array([0.01, 0.0, 0.0])  # 10 m/s burn

    man = Maneuver(burn_epoch=burn_epoch, delta_v_eci=delta_v)
    man_prop = ManeuverPropagator(base_prop, [man])

    # Propagate through the burn
    final_state = man_prop.propagate(initial_state, 600.0)

    # Baseline (no burn)
    baseline_state = base_prop.propagate(initial_state, 600.0)

    # The burn should have changed the final velocity significantly
    assert not np.allclose(final_state.v, baseline_state.v, atol=1e-4)


def test_numerical_propagate_many(initial_state):
    prop = NumericalPropagator()
    states = np.array([initial_state.state_vector_6d, initial_state.state_vector_6d])

    results = prop.propagate_many_to(
        states, initial_state.epoch, initial_state.epoch + timedelta(seconds=60)
    )
    assert results.shape == (2, 6)
