import numpy as np

from oure.physics.drag_corrector import AtmosphericDragCorrector
from oure.physics.j2_corrector import J2PerturbationCorrector
from oure.physics.sgp4_propagator import SGP4Propagator


def test_j2_corrector_vectorized(sample_tle, dummy_state):
    base_prop = SGP4Propagator(sample_tle)
    j2_prop = J2PerturbationCorrector(base_prop)

    states = np.array([dummy_state.state_vector_6d, dummy_state.state_vector_6d])
    target_epoch = dummy_state.epoch

    result = j2_prop.propagate_many_to(states, dummy_state.epoch, target_epoch)
    assert result.shape == (2, 6)


def test_drag_corrector_vectorized(sample_tle, dummy_state):
    base_prop = SGP4Propagator(sample_tle)
    drag_prop = AtmosphericDragCorrector(base_prop)

    states = np.array([dummy_state.state_vector_6d, dummy_state.state_vector_6d])
    target_epoch = dummy_state.epoch

    result = drag_prop.propagate_many_to(states, dummy_state.epoch, target_epoch)
    assert result.shape == (2, 6)


def test_drag_corrector_set_flux(sample_tle):
    base_prop = SGP4Propagator(sample_tle)
    drag_prop = AtmosphericDragCorrector(base_prop)
    drag_prop.set_solar_flux(200.0)
    assert drag_prop._atmo.f10_7 == 200.0


def test_base_propagate_sequence(sample_tle, dummy_state):
    base_prop = SGP4Propagator(sample_tle)
    epochs = [dummy_state.epoch, dummy_state.epoch]
    results = base_prop.propagate_sequence(dummy_state, epochs)
    assert len(results) == 2
