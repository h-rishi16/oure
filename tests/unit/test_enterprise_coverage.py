import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from oure.core.models import StateVector, CovarianceMatrix, ConjunctionEvent
from oure.physics.numerical import NumericalPropagator
from oure.physics.maneuver import Maneuver, ManeuverPropagator
from oure.physics.breakup import BreakupModel
from oure.data.cdm_parser import CDMParser
from oure.risk.optimizer import ManeuverOptimizer
from oure.uncertainty.sensor import SensorTaskingSimulator
from oure.core.logging_config import configure_logging

def test_numerical_propagator_impact():
    prop = NumericalPropagator()
    # State pointing straight down to Earth
    state = StateVector(
        r=np.array([100.0, 0.0, 0.0]), # Inside Earth
        v=np.array([0.0, 0.0, 0.0]),
        epoch=datetime.now(timezone.utc),
        sat_id="impact"
    )
    from oure.core.exceptions import PropagationError
    # Catch any propagation error (could be solver failure or impact check)
    with pytest.raises(PropagationError):
        prop.propagate(state, 10.0)

def test_maneuver_propagator_backward():
    base_prop = NumericalPropagator()
    burn_epoch = datetime.now(timezone.utc)
    man = Maneuver(burn_epoch=burn_epoch, delta_v_eci=np.array([0.1, 0, 0]))
    prop = ManeuverPropagator(base_prop, [man])
    
    state = StateVector(r=np.array([7000, 0, 0]), v=np.array([0, 7.5, 0]), epoch=burn_epoch + timedelta(minutes=10), sat_id="1")
    # Propagating backward should not trigger the burn (simplified logic)
    res = prop.propagate_to(state, burn_epoch - timedelta(minutes=10))
    assert res.epoch < state.epoch

def test_breakup_model_randomness():
    s1 = StateVector(r=np.array([7000, 0, 0]), v=np.array([0, 7.5, 0]), epoch=datetime.now(timezone.utc), sat_id="1")
    s2 = StateVector(r=np.array([7000, 0, 0]), v=np.array([0, -7.5, 0]), epoch=s1.epoch, sat_id="2")
    
    f1 = BreakupModel.simulate_collision(s1, 500, s2, 500, s1.epoch, num_fragments=10, random_seed=42)
    f2 = BreakupModel.simulate_collision(s1, 500, s2, 500, s1.epoch, num_fragments=10, random_seed=42)
    
    assert np.array_equal(f1[0].v, f2[0].v)

def test_logging_config():
    configure_logging(level="DEBUG", format="json")
    configure_logging(level="INFO", format="console")
