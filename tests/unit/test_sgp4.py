from oure.physics.sgp4_propagator import SGP4Propagator


def test_sgp4_base(sample_tle, dummy_state):
    propagator = SGP4Propagator(sample_tle)

    propagated_state = propagator.propagate(dummy_state, 3600.0)
    assert propagated_state.r.shape == (3,)
    assert propagated_state.v.shape == (3,)
