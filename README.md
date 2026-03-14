# OURE (Orbital Uncertainty & Risk Engine)

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

OURE is a high-performance, enterprise-grade Space Situational Awareness (SSA) platform designed for orbital risk prediction, collision avoidance optimization, and fragmentation modeling.

Built for mission-critical speed and mathematical rigor, OURE processes Two-Line Element (TLE) sets, propagates uncertainty using vectorized Monte Carlo simulations, and evaluates Probability of Collision ($P_c$) using Foster's algorithm on the encounter B-plane.

## Key Features

- **Multi-Fidelity Physics Engine:** Native SGP4 propagation combined with a High Precision Orbit Propagator (HPOP) featuring J2 oblateness and atmospheric drag perturbations.
- **Collision Avoidance (SLSQP):** Mathematical maneuver optimization to find minimum-fuel 3D Delta-V vectors that mitigate collision risk below safety thresholds.
- **NASA Standard Breakup Model:** Simulation of hypervelocity impacts and debris cloud dispersion.
- **Sensor Fusion:** Extended Kalman Filter (EKF) updates to simulate commercial radar tasking and covariance collapse.
- **KD-Tree Fleet Screening:** Distributed $O(N \log N)$ screening of entire satellite constellations against the full NORAD catalog.
- **Interactive Visualizations:** 3D ECI encounter geometry and 2D B-Plane cross-sections using Plotly.
- **Distributed Architecture:** FastAPI REST API and Celery/Redis background worker support for large-scale operations.

## Installation

OURE requires Python 3.11 or higher.

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/oure.git
   cd oure
   ```

2. Setup virtual environment and install:
   ```bash
   make install
   ```

3. Configure credentials in `keys.env`:
   ```env
   SPACETRACK_USER=your_email@example.com
   SPACETRACK_PASS=your_password
   ```

## Usage

### 1. Analyze a Conjunction
```bash
oure analyze --primary 25544 --secondary 43205 --look-ahead 72
```

### 2. Avoidance Maneuver Wizard
Starts an interactive guide to optimize a fuel-efficient burn:
```bash
oure avoid --primary 25544 --secondary 43205
```

### 3. Fleet Screening
Screen thousands of secondaries against a fleet of primaries in parallel:
```bash
oure analyze-fleet --primaries-file p.json --secondaries-file s.json --workers 8
```

### 4. Space Debris Fragmentation
Simulate a "What-if" collision between two objects:
```bash
oure shatter --primary 25544 --secondary 43205 --fragments 5000
```

### 5. Web Dashboard
Launch the multi-page Streamlit dashboard:
```bash
./start_web.sh
```

## Architecture

OURE enforces a strict, decoupled 5-layer architecture:
1. **Core:** Immutable data models (`StateVector`, `CovarianceMatrix`).
2. **Data:** Caching fetchers (`SpaceTrack`, `NOAA`, `CDM Parser`).
3. **Physics:** Certified SGP4 and RK45 Numerical integrators.
4. **Uncertainty:** STM generation, EKF Sensor updates, and Monte Carlo ensembles.
5. **Conjunction/Risk:** TCA Golden-section search, Foster $P_c$ math, and SLSQP optimization.

## Testing & Quality

OURE maintains high engineering standards:
- **Test Coverage:** 88%+ enforced via `pytest-cov`.
- **Static Analysis:** Strict `mypy` typing and `ruff` linting.
- **Numerical Stability:** Joseph-form covariance updates and eigenvalue-ordered risk projection.

```bash
make test-all
```

## License

MIT License
