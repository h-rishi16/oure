from datetime import UTC, datetime

import numpy as np

from oure.core.models import StateVector
from oure.physics.breakup import BreakupModel


def test_breakup_model():
    s1 = StateVector(
        r=np.array([7000.0, 0.0, 0.0]),
        v=np.array([0.0, 7.5, 0.0]),
        epoch=datetime.now(UTC),
        sat_id="1",
    )
    s2 = StateVector(
        r=np.array([7000.0, 0.0, 0.0]),
        v=np.array([0.0, -7.5, 0.0]),
        epoch=s1.epoch,
        sat_id="2",
    )

    fragments = BreakupModel.simulate_collision(
        s1, 500.0, s2, 200.0, s1.epoch, num_fragments=50
    )
    assert len(fragments) == 50
    assert fragments[0].sat_id.startswith("DEBRIS_1")
    # All fragments should originate from the same impact point
    assert np.array_equal(fragments[0].r, s1.r)
