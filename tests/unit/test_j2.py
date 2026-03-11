from oure.physics.j2_corrector import J2PerturbationCorrector
from oure.physics.sgp4_propagator import SGP4Propagator


def test_j2_corrector(sample_tle, dummy_state):
    base_propagator = SGP4Propagator(sample_tle)
    j2_propagator = J2PerturbationCorrector(base_propagator)

    j2_state = j2_propagator.propagate(dummy_state, 3600.0)
    assert j2_state.r.shape == (3,)
