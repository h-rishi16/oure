from datetime import UTC, datetime, timedelta

import numpy as np

from oure.conjunction.tca_finder import TCARefinementEngine
from oure.core.models import StateVector


class MockPropagator:
    def propagate_to(self, state: StateVector, target_epoch: datetime) -> StateVector:
        dt = (target_epoch - state.epoch).total_seconds()
        # Primary moves along X
        if state.sat_id == "1":
            r_new = state.r + np.array([dt * 7.5, 0, 0])
        # Secondary moves along Y
        else:
            r_new = state.r + np.array([0, dt * 7.5, 0])
        return StateVector(r=r_new, v=state.v, epoch=target_epoch, sat_id=state.sat_id)


def test_tca_refinement_engine():
    epoch = datetime.now(UTC)
    # They cross the origin at exactly dt=100s
    p_state = StateVector(
        r=np.array([-750.0, 0, 0]), v=np.array([7.5, 0, 0]), epoch=epoch, sat_id="1"
    )
    s_state = StateVector(
        r=np.array([0, -750.0, 0]), v=np.array([0, 7.5, 0]), epoch=epoch, sat_id="2"
    )

    prop = MockPropagator()
    finder = TCARefinementEngine(tolerance_seconds=0.1)

    t_start = epoch
    t_end = epoch + timedelta(seconds=200)

    tca, dist = finder.find_tca(p_state, prop, s_state, prop, t_start, t_end)  # type: ignore

    assert tca is not None
    assert abs((tca - epoch).total_seconds() - 100.0) < 0.2
    assert dist < 1.0


def test_tca_refinement_no_conjunction():
    epoch = datetime.now(UTC)
    # Parallel paths, they never get close
    p_state = StateVector(
        r=np.array([0.0, 0, 0]), v=np.array([7.5, 0, 0]), epoch=epoch, sat_id="1"
    )
    s_state = StateVector(
        r=np.array([0, 20.0, 0]), v=np.array([7.5, 0, 0]), epoch=epoch, sat_id="2"
    )

    prop = MockPropagator()
    finder = TCARefinementEngine(tolerance_seconds=0.1)

    t_start = epoch
    t_end = epoch + timedelta(seconds=200)

    result = finder.find_tca(p_state, prop, s_state, prop, t_start, t_end)  # type: ignore
    assert result is None
