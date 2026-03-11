# OURE: Orbital Uncertainty & Risk Engine - Project Specification

## 1. Project Overview
OURE is a specialized Space Situational Awareness (SSA) tool designed to predict orbital conjunctions and quantify collision risks using high-fidelity uncertainty propagation.

## 2. Five-Layer System Architecture
The project is strictly modular, organized into the following layers:

* **L1: Data Ingestion**
    * Factions: TLE (Two-Line Element) parsing, Space-Track API integration.
    * Goal: Automated retrieval and sanitization of orbital data.
* **L2: Propagator Core**
    * Physics: SGP4 (Simplified General Perturbations 4).
    * Perturbations: Accounts for $J_2$ Earth oblateness and atmospheric drag.
* **L3: Uncertainty Module**
    * Method: Monte Carlo simulations (1,000+ "ghost" trajectories).
    * Output: Covariance Matrix propagation ($\sigma$ error ellipsoids).
* **L4: Conjunction Assessment (Risk)**
    * Math: B-Plane (Encounter Plane) projection.
    * Algorithm: Foster's Algorithm for Probability of Collision ($P_c$).
* **L5: CLI Interface**
    * Tech: Python (Click/Typer).
    * Function: Command-line control and automated reporting.



## 3. Technical Requirements & Standards
* **Language:** Python 3.10+ (NumPy, SciPy, SGP4).
* **Optimization:** Use KD-Trees for spatial filtering ($O(\log n)$ lookup) to handle large satellite constellations.
* **Precision:** Support TEME to ECI/ECEF coordinate transformations.

## 4. CLI Command Reference
| Command | Description |
| :--- | :--- |
| `oure sync` | Update local TLE database from Space-Track. |
| `oure propagate <id>` | Calculate future state vector over $t$ days. |
| `oure assess <id1> <id2>` | Project conjunction into the B-Plane and calculate $P_c$. |
| `oure report` | Output a PDF summary of all high-risk events. |

## 5. Deployment Constraints
* **Performance:** All Monte Carlo loops must be vectorized using NumPy.
* **Safety:** Flag TLE data older than 48 hours as "Stale" to avoid accuracy degradation.