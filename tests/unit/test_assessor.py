import numpy as np

from oure.conjunction.assessor import ConjunctionAssessor
from oure.core.models import CovarianceMatrix, TLERecord
from oure.physics.sgp4_propagator import SGP4Propagator


def test_conjunction_assessor(dummy_state_primary, dummy_state_secondary):
    assessor = ConjunctionAssessor(screening_distance_km=5.0)
    cov1 = CovarianceMatrix(matrix=np.eye(6), epoch=dummy_state_primary.epoch, sat_id="1")
    cov2 = CovarianceMatrix(matrix=np.eye(6), epoch=dummy_state_secondary.epoch, sat_id="2")

    tle = TLERecord(sat_id="1", name="DUMMY", line1="1", line2="2", epoch=dummy_state_primary.epoch, mean_motion_rev_per_day=15.5)
    prop1 = SGP4Propagator(tle)
    prop2 = SGP4Propagator(tle)

    events = assessor.find_conjunctions(
        primary=dummy_state_primary,
        primary_cov=cov1,
        primary_propagator=prop1,
        secondaries=[(dummy_state_secondary, cov2, prop2)],
        look_ahead_hours=1.0
    )

    assert isinstance(events, list)
