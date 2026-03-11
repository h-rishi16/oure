from datetime import timedelta

import numpy as np

from oure.core.models import CovarianceMatrix, TLERecord
from oure.physics.sgp4_propagator import SGP4Propagator
from oure.uncertainty.monte_carlo import MonteCarloUncertaintyPropagator


def test_monte_carlo_generator(dummy_state):
    cov = CovarianceMatrix(matrix=np.eye(6)*1e-6, epoch=dummy_state.epoch, sat_id="12345")

    tle = TLERecord(
        sat_id="12345", name="DUMMY", line1="1 25544U", line2="2 25544", epoch=dummy_state.epoch,
        inclination_deg=51.6, raan_deg=122.9, eccentricity=0.0, arg_perigee_deg=329.8,
        mean_anomaly_deg=116.7, mean_motion_rev_per_day=15.5, bstar=0.0
    )
    base_prop = SGP4Propagator(tle)

    generator = MonteCarloUncertaintyPropagator(propagator=base_prop, n_samples=100)
    result = generator.run(dummy_state, cov, target_epoch=dummy_state.epoch + timedelta(seconds=60))
    assert result.sample_covariance.shape == (6, 6)
    assert len(result.ghost_states) == 100
