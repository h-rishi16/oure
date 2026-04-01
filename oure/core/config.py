"""
OURE Configuration Management
=============================
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OUREConfig(BaseSettings):
    """
    Global settings for the OURE engine, validated at startup.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Space-Track Credentials (Required - no defaults)
    spacetrack_user: str = Field(validation_alias="SPACETRACK_USER")
    spacetrack_pass: str = Field(validation_alias="SPACETRACK_PASS")

    # Default Physics Parameters
    default_sigma_km: float = Field(
        default=0.5, validation_alias="OURE_DEFAULT_COV_SIGMA_KM"
    )
    solar_flux_override: float | None = Field(
        default=None, validation_alias="OURE_SOLAR_FLUX_OVERRIDE"
    )
    tle_max_age_hours: float = Field(
        default=48.0, validation_alias="OURE_TLE_MAX_AGE_HOURS"
    )

    # Analysis Defaults
    mc_samples: int = Field(default=1000, validation_alias="OURE_MC_SAMPLES")
    screening_dist_km: float = Field(
        default=5.0, validation_alias="OURE_SCREENING_DIST_KM"
    )

    # Logging
    log_level: str = Field(default="INFO", validation_alias="OURE_LOG_LEVEL")
    log_format: str = Field(default="console", validation_alias="OURE_LOG_FORMAT")


settings = OUREConfig()
