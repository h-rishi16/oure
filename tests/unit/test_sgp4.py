from oure.physics.sgp4_propagator import SGP4Propagator


def test_sgp4_base(sample_tle, dummy_state):
    propagator = SGP4Propagator(sample_tle)

    from oure.core.models import StateVector

    # Use TLE epoch to prevent massive orbital decay in SGP4 prediction
    state_at_epoch = StateVector(
        r=dummy_state.r, v=dummy_state.v, epoch=sample_tle.epoch, sat_id="12345"
    )

    propagated_state = propagator.propagate(state_at_epoch, 3600.0)
    assert propagated_state.r.shape == (3,)
    assert propagated_state.v.shape == (3,)

    # Assert the propagated position is within ISS bounds (approx 380 - 430 km)
    alt = propagated_state.altitude_km
    assert 380.0 <= alt <= 440.0
