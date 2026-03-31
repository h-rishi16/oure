import os

from oure.core.config import OURESettings


def test_oure_settings_defaults():
    settings = OURESettings()
    assert settings.mc_samples == 1000
    assert settings.screening_dist_km == 5.0
    assert settings.log_level == "INFO"


def test_oure_settings_env_override(monkeypatch):
    os.environ["OURE_MC_SAMPLES"] = "5000"
    os.environ["OURE_SCREENING_DIST_KM"] = "10.0"

    settings = OURESettings()
    assert settings.mc_samples == 5000
    assert settings.screening_dist_km == 10.0
