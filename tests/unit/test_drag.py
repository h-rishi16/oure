import numpy as np

from oure.physics.drag_corrector import AtmosphericDragCorrector
from oure.physics.sgp4_propagator import SGP4Propagator


def test_drag_corrector(sample_tle, dummy_state):
    base_propagator = SGP4Propagator(sample_tle)
    drag_propagator = AtmosphericDragCorrector(
        base_propagator, cd=2.2, mass_kg=500.0, area_m2=10.0, solar_flux=150.0
    )

    drag_state = drag_propagator.propagate(dummy_state, 3600.0)
    assert drag_state.r.shape == (3,)


def test_drag_magnitude(dummy_state):
    from oure.physics.numerical import NumericalPropagator

    # Test drag deceleration magnitude at ~400km altitude
    prop = NumericalPropagator(cd=2.2, area_m2=10.0, mass_kg=500.0, solar_flux=150.0)
    # y = [x, y, z, vx, vy, vz]
    y0 = dummy_state.state_vector_6d
    y_dot = prop._dynamics(0.0, y0)

    a_tot = y_dot[3:]

    # Gravitational accel at 7000km is ~ MU / 7000^2 ~ 3.986e5 / 4.9e7 ~ 0.0081 km/s^2
    # Drag accel is ~ 1e-7 km/s^2

    # To isolate drag, we can just call the drag part
    r_mag = np.linalg.norm(y0[:3])
    altitude = r_mag - 6371.0
    rho = prop._atmo.get_density(altitude)

    v_mag = np.linalg.norm(y0[3:])
    v_mag_ms = v_mag * 1000.0
    a_drag_ms2 = -0.5 * prop.cd * prop.am_ratio * rho * (v_mag_ms**2)
    a_drag_kms2 = a_drag_ms2 / 1000.0

    # Drag deceleration should be small, approx 6e-12 km/s^2 at 630km
    assert 1e-13 < abs(a_drag_kms2) < 1e-10
