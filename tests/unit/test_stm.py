from oure.uncertainty.stm import STMCalculator


def test_stm_calculator(dummy_state):
    calculator = STMCalculator(fidelity=0) # Two-body
    stm = calculator.compute(dummy_state, 60.0)
    assert stm.shape == (6, 6)
