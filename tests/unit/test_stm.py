from oure.uncertainty.stm import STMCalculator


def test_stm_calculator(dummy_state):
    calculator = STMCalculator(fidelity=0)  # Two-body
    stm = calculator.compute(dummy_state, 60.0)
    assert stm.shape == (6, 6)

    calc1 = STMCalculator(fidelity=1)  # J2 linearized
    stm1 = calc1.compute(dummy_state, 60.0)
    assert stm1.shape == (6, 6)

    calc2 = STMCalculator(fidelity=2)  # Numerical
    stm2 = calc2.compute(dummy_state, 10.0)
    assert stm2.shape == (6, 6)
