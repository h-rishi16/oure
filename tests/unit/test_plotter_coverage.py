from datetime import UTC, datetime

import numpy as np

from oure.core.models import ConjunctionEvent, CovarianceMatrix, StateVector
from oure.risk.plotter import RiskPlotter


def test_risk_plotter_bplane(tmp_path):
    event_data = {
        "primary_id": "1",
        "secondary_id": "2",
        "pc": 1e-4,
        "miss_distance_km": 0.5,
        "hard_body_radius_m": 20.0,
        "sigma_bplane_km": [1.0, 2.0],
    }
    out_path = tmp_path / "plot.html"
    RiskPlotter.plot_bplane_from_json(event_data, out_path)
    assert out_path.exists()


def test_risk_plotter_3d():
    state = StateVector(
        r=np.array([7000, 0, 0]),
        v=np.array([0, 7.5, 0]),
        epoch=datetime.now(UTC),
        sat_id="1",
    )
    cov = CovarianceMatrix(matrix=np.eye(6), epoch=state.epoch, sat_id="1")
    event = ConjunctionEvent(
        primary_id="1",
        secondary_id="2",
        tca=state.epoch,
        miss_distance_km=0.1,
        relative_velocity_km_s=10.0,
        primary_state=state,
        secondary_state=state,
        primary_covariance=cov,
        secondary_covariance=cov,
    )
    fig = RiskPlotter.create_3d_encounter_figure(event)
    assert fig is not None
