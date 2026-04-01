# OURE (Orbital Uncertainty & Risk Engine)

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-v1.2.0-orange.svg)

OURE is a high-performance, enterprise-grade Space Situational Awareness (SSA) platform designed for orbital risk prediction, collision avoidance optimization, fragmentation modeling, and massive fleet screening.

Built for mission-critical speed and mathematical rigor, OURE processes Space-Track Two-Line Elements (TLEs), NASA CDDIS data, and CCSDS Conjunction Data Messages (CDMs). It propagates uncertainty using vectorized Monte Carlo simulations and evaluates Probability of Collision ($P_c$) using Foster's algorithm on the encounter B-plane.

## Key Features

- **Multi-Fidelity Physics Engine:** Native SGP4 propagation combined with a High Precision Orbit Propagator (HPOP) featuring J2 oblateness, Solar Radiation Pressure (SRP), and atmospheric drag perturbations.
- **NASA-Grade Integration:** Supports parsing NASA CDDIS CPF (Satellite Laser Ranging) files for centimeter-level accuracy and implements the NASA MSFC Jacchia analytical atmospheric model for highly accurate solar flux drag modifications.
- **Collision Avoidance (SLSQP):** Mathematical maneuver optimization to find minimum-fuel 3D Delta-V vectors that mitigate collision risk below safety thresholds.
- **NASA Standard Breakup Model:** Simulation of hypervelocity impacts and debris cloud dispersion.
- **Sensor Fusion:** Extended Kalman Filter (EKF) updates to simulate commercial radar tasking and covariance collapse.
- **KD-Tree Fleet Screening:** Distributed epoch-bucketed $O(N \log N)$ screening of entire satellite constellations against the full NORAD catalog.
- **Enterprise Observability:** Fully instrumented FastAPI REST API and Celery/Redis background workers, seamlessly integrated with **Prometheus and Grafana** for real-time physics engine throughput and risk quantification latency monitoring.
- **Interactive Visualizations:** 3D ECI encounter geometry and 2D B-Plane cross-sections using Plotly, wrapped in a Streamlit Operations Dashboard.

## Installation & Deployment

OURE can be run locally via CLI, launched via a lightweight web interface, or deployed as a full enterprise microservice stack.

### 1. Local CLI & Lightweight Launch

```bash
git clone https://github.com/h-rishi16/oure.git
cd oure

# Install CLI and dependencies natively
bash install.sh

# Run the lightweight Streamlit + FastAPI stack locally
./start_web.sh
```

### 2. Enterprise Stack (Docker Compose)

For production environments, OURE deploys as a fully isolated 6-service stack including the API, Background Workers, Redis Broker, Operations Dashboard, Prometheus metrics, and a Grafana observability suite.

```bash
# Start the full Enterprise Stack
docker compose up --build -d
```

* **Operations Dashboard:** [http://localhost:8501](http://localhost:8501)
* **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Grafana (Observability):** [http://localhost:3000](http://localhost:3000) *(Login: admin / admin)*
* **Prometheus Metrics:** [http://localhost:8000/metrics](http://localhost:8000/metrics)

## CLI Usage

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

## Architecture & Security

OURE enforces a strict, decoupled 5-layer architecture, hardened against Resource Exhaustion (DoS) and Numerical Singularities:
1. **Core:** Immutable data models (`StateVector`, `CovarianceMatrix`) and Prometheus Metrics Managers.
2. **Data:** Caching fetchers (`SpaceTrack`, `NOAA F10.7`), `NASA CDDIS CPF` parsing, and strict CCSDS `CDM Parser`.
3. **Physics:** Certified SGP4, RK45 Numerical integrators, NASA MSFC Atmospheric modeling, and SRP.
4. **Uncertainty:** Memory-hardened Vectorized Monte Carlo ensembles (capped at 100k samples), STM generation, and EKF Sensor updates.
5. **Conjunction/Risk:** TCA Golden-section search, Robust Foster $P_c$ math utilizing Moore-Penrose pseudo-inverses (`np.linalg.pinv`) to prevent singular matrix crashes, and SLSQP maneuver optimization.

## Testing & Quality

OURE maintains strict engineering standards, verified by GitHub Actions CI/CD:
- **Test Coverage:** 88%+ enforced via `pytest-cov` across 70+ test suites.
- **Static Analysis:** Strict `mypy` typing and `ruff` linting.
- **Numerical Stability:** Joseph-form covariance updates, eigenvalue-ordered risk projection with singularity protection.

```bash
make test-all
```

## License

MIT License
