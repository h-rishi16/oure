from datetime import UTC, datetime

import numpy as np
import pytest

from oure.core.models import ConjunctionEvent, CovarianceMatrix, RiskResult, StateVector
from oure.risk.alert import AlertClassifier


@pytest.fixture
def dummy_event():
    state = StateVector(
        r=np.array([7000.0, 0.0, 0.0]),
        v=np.array([0.0, 7.5, 0.0]),
        epoch=datetime.now(UTC),
        sat_id="1",
    )
    cov = CovarianceMatrix(matrix=np.eye(6), epoch=state.epoch, sat_id="1")
    return ConjunctionEvent(
        primary_id="1",
        secondary_id="2",
        tca=state.epoch,
        miss_distance_km=1.0,
        relative_velocity_km_s=10.0,
        primary_state=state,
        secondary_state=state,
        primary_covariance=cov,
        secondary_covariance=cov,
    )


def test_alert_classifier_red(dummy_event):
    classifier = AlertClassifier()
    result = RiskResult(
        conjunction=dummy_event,
        pc=1.5e-3,
        combined_covariance=np.eye(2),
        hard_body_radius_m=20.0,
        b_plane_sigma_x=1.0,
        b_plane_sigma_z=1.0,
    )
    assert classifier.classify(result) == "RED"


def test_alert_classifier_yellow(dummy_event):
    classifier = AlertClassifier()
    result = RiskResult(
        conjunction=dummy_event,
        pc=5.0e-5,
        combined_covariance=np.eye(2),
        hard_body_radius_m=20.0,
        b_plane_sigma_x=1.0,
        b_plane_sigma_z=1.0,
    )
    assert classifier.classify(result) == "YELLOW"


def test_alert_classifier_green(dummy_event):
    classifier = AlertClassifier()
    result = RiskResult(
        conjunction=dummy_event,
        pc=1.0e-6,
        combined_covariance=np.eye(2),
        hard_body_radius_m=20.0,
        b_plane_sigma_x=1.0,
        b_plane_sigma_z=1.0,
    )
    assert classifier.classify(result) == "GREEN"
