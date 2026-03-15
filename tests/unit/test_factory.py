from oure.physics.drag_corrector import AtmosphericDragCorrector
from oure.physics.factory import PropagatorFactory
from oure.physics.j2_corrector import J2PerturbationCorrector
from oure.physics.sgp4_propagator import SGP4Propagator


def test_factory_build_all_layers(sample_tle):
    prop = PropagatorFactory.build(sample_tle, include_j2=True, include_drag=True)
    assert isinstance(prop, AtmosphericDragCorrector)
    assert isinstance(prop._base, J2PerturbationCorrector)
    assert isinstance(prop._base._base, SGP4Propagator)


def test_factory_build_sgp4_only(sample_tle):
    prop = PropagatorFactory.build(sample_tle, include_j2=False, include_drag=False)
    assert isinstance(prop, SGP4Propagator)
