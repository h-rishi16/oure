from oure.physics.drag_corrector import AtmosphericDragCorrector
from oure.physics.sgp4_propagator import SGP4Propagator


def test_drag_corrector(sample_tle, dummy_state):
    base_propagator = SGP4Propagator(sample_tle)
    drag_propagator = AtmosphericDragCorrector(base_propagator, cd=2.2, mass_kg=500.0, area_m2=10.0, solar_flux=150.0)

    drag_state = drag_propagator.propagate(dummy_state, 3600.0)
    assert drag_state.r.shape == (3,)
