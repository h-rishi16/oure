"""Physical and orbital mechanics constants used throughout OURE."""

# ── Gravitational ────────────────────────────────────────────────

MU_KM3_S2: float = 398600.4418
"""Standard gravitational parameter of Earth (km³/s²)."""

MU_M3_S2: float = 3.986004418e14
"""Standard gravitational parameter of Earth (m³/s²)."""

# ── Earth Geometry ───────────────────────────────────────────────

R_EARTH_KM: float = 6378.137
"""WGS84 equatorial radius of Earth (km)."""

R_EARTH_M: float = 6378137.0
"""WGS84 equatorial radius of Earth (m)."""

F_OBLATE: float = 1.0 / 298.257223563
"""WGS84 flattening factor (dimensionless)."""

# ── Zonal Harmonics ──────────────────────────────────────────────

J2: float = 1.08262668e-3
"""Second zonal harmonic --- Earth oblateness (dimensionless)."""

J3: float = -2.53265648e-6
"""Third zonal harmonic (dimensionless)."""

J4: float = -1.61962159e-6
"""Fourth zonal harmonic (dimensionless)."""

# ── Rotation ─────────────────────────────────────────────────────

OMEGA_EARTH_RAD_S: float = 7.2921150e-5
"""Earth sidereal rotation rate (rad/s)."""

# ── Atmosphere ───────────────────────────────────────────────────

SOLAR_FLUX_MEAN_SFU: float = 150.0
"""Long-term mean F10.7 solar flux (Solar Flux Units)."""

JACCHIA_SOLAR_COUPLING: float = 0.003
"""Empirical solar flux density coupling constant (1/SFU)."""

# ── Time ─────────────────────────────────────────────────────────

SECONDS_PER_DAY: float = 86400.0
SECONDS_PER_MINUTE: float = 60.0
TWO_PI: float = 6.283185307179586
