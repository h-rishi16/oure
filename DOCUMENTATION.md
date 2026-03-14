# OURE Detailed Documentation

OURE (Orbital Uncertainty & Risk Engine) is a professional-grade Space Situational Awareness (SSA) platform. It provides high-precision orbital prediction, collision risk quantification, and automated maneuver planning.

---

## What Can OURE Do?

OURE is designed to handle the entire lifecycle of conjunction assessment:

1.  **Catalog Ingestion:** Connects to Space-Track.org to fetch the latest TLEs and NOAA for real-time solar flux data.
2.  **Massive Screening:** Uses KD-Tree spatial indexing and vectorized NumPy propagation to screen thousands of satellites for close approaches in seconds.
3.  **Risk Quantification:** Implements **Foster's 1992 Algorithm** to calculate the Probability of Collision ($P_c$) by projecting 3D covariance ellipsoids onto the 2D encounter B-Plane.
4.  **Maneuver Optimization:** Uses the **SLSQP (Sequential Least Squares Programming)** optimizer to find the minimum-fuel burn required to reduce collision risk below safety thresholds.
5.  **Uncertainty Modeling:** Supports both analytical State Transition Matrix (STM) propagation and high-fidelity **Monte Carlo** ensemble simulations.
6.  **Fragmentation Modeling:** Simulates hypervelocity impacts using the **NASA Standard Breakup Model** to predict debris cloud dispersion.
7.  **Sensor Tasking:** Simulates radar measurement updates via an **Extended Kalman Filter (EKF)** to demonstrate how new data "collapses" uncertainty.

---

## Detailed Usage Guide

### 1. The Command Line Interface (CLI)

The CLI is the primary tool for orbital analysts.

#### Conjunction Analysis
To check if two satellites will collide in the next 72 hours:
```
oure analyze --primary 25544 --secondary 43205 --look-ahead 72
```

#### Avoidance Wizard
If a high-risk event is found, run the interactive wizard to plan a maneuver:
```
oure avoid --primary 25544 --secondary 43205
```
This tool will ask you when you want to burn and calculate the optimal 3D Delta-V vector.

#### Fleet Monitoring
To monitor a list of assets continuously:
```
oure monitor --primary 25544 --secondaries-file my_catalog.json --interval 3600
```

---

### 2. The Web Operations Center (SOC)

OURE includes a modern web interface for visual monitoring.

*   **To Launch:** Run `./start_web.sh` and go to `http://localhost:8501`.
*   **Live Status:** View a real-time dashboard of all tracked threats.
*   **CDM Analysis:** Upload official JSON Conjunction Data Messages (CDMs) for independent verification.
*   **3D Visualization:** See the encounter geometry in interactive 3D (ECI frame).

---

### 3. Distributed Task Engine (API)

For enterprise-scale operations, OURE uses a distributed architecture:

*   **FastAPI:** Provides a REST interface for submitting screening jobs.
*   **Celery & Redis:** Heavy physics calculations are moved to background workers so the UI stays responsive.
*   **Docker:** The entire stack can be deployed to the cloud using `docker-compose up`.

---

## Mathematical Foundation

OURE is built on rigorous aerospace engineering principles:

*   **SGP4:** Used for fast, general-purpose TLE propagation.
*   **HPOP (RK45):** A High-Precision Orbit Propagator using Runge-Kutta 4(5) integration, including J2 oblateness and co-rotating atmospheric drag.
*   **B-Plane Projection:** Conjunctions are analyzed in the frame orthogonal to the relative velocity vector, where $P_c$ calculation is most stable.
*   **Joseph Form EKF:** Used for sensor updates to ensure numerical stability and maintain positive-definite covariance matrices.

---

## Data Safety & Privacy

*   **Local Caching:** OURE stores TLEs in a local SQLite database (`~/.oure/cache.db`) to minimize network calls and bypass Space-Track rate limits.
*   **Credential Security:** Credentials are managed via environment variables (`keys.env`) and are never stored in the database or committed to the repository.

---

## Support & Development

For technical details on how to extend OURE, refer to the `ARCHITECTURE.md` (coming soon) or run the full test suite to see the engine in action:
```bash
make test-all
```
