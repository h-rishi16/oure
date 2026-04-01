import os
import pytest
from oure.core.config import OUREConfig

def test_oure_config_defaults(monkeypatch):
    # Mock required fields in environment
    monkeypatch.setenv("SPACETRACK_USER", "test_user")
    monkeypatch.setenv("SPACETRACK_PASS", "test_pass")
    
    config = OUREConfig()
    assert config.mc_samples == 1000
    assert config.screening_dist_km == 5.0
    assert config.log_level == "INFO"

def test_oure_config_env_override(monkeypatch):
    monkeypatch.setenv("SPACETRACK_USER", "test_user")
    monkeypatch.setenv("SPACETRACK_PASS", "test_pass")
    monkeypatch.setenv("OURE_MC_SAMPLES", "5000")
    monkeypatch.setenv("OURE_SCREENING_DIST_KM", "10.0")
    
    config = OUREConfig()
    assert config.mc_samples == 5000
    assert config.screening_dist_km == 10.0
