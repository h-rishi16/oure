# OURE (Orbital Uncertainty & Risk Engine)

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Coverage](https://img.shields.io/badge/coverage-81%25-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

OURE is a high-performance, command-line Space Situational Awareness (SSA) tool designed to predict orbital conjunctions and quantify collision risks ($P_c$) between satellites in Low Earth Orbit (LEO).

Built for speed and rigorous mathematical accuracy, OURE processes Two-Line Element (TLE) sets, propagates uncertainty using highly optimized vectorized Monte Carlo simulations, and evaluates the Probability of Collision using Foster's algorithm on the encounter B-plane.

## Features

- **Vectorized Physics Engine:** Blazing fast SGP4 orbit propagation with J2 (Earth oblateness) and Atmospheric Drag (NRL MSISE proxy via NOAA F10.7 flux) perturbations, utilizing pure NumPy arrays.
- **Monte Carlo Uncertainty:** Propagates 1,000+ "ghost" trajectories in seconds to generate highly accurate covariance matrices without relying on linear assumptions.
- **KD-Tree Spatial Indexing:** $O(N \log N)$ screening of large satellite catalogs to quickly filter potential conjunction events.
- **Foster's Algorithm:** B-plane projection and 2D numerical integration/series expansion to calculate accurate probabilities of collision.
- **Rich CLI & PDF Reports:** A beautiful terminal interface built with `Click` and `Rich`, complete with automated PDF report generation via `fpdf2`.
- **Local SQLite Caching:** Built-in rate-limiting protection with local caching of Space-Track and NOAA data.

## Installation

OURE requires Python 3.11 or higher.

1. Clone the repository and navigate to the directory:
   ```bash
   git clone https://github.com/yourusername/oure.git
   cd oure
   ```

2. Create a virtual environment and install the package with developer and visualization extras:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e '.[dev,vis]'
   ```

3. Set up your Space-Track.org credentials. Create a `keys.env` file in the project root:
   ```env
   SPACETRACK_USER=your_email@example.com
   SPACETRACK_PASS=your_password
   ```

## Usage

Load your credentials into your environment, then run the CLI:

```bash
source keys.env
```

### 1. Fetch Data
Download the latest TLEs for the ISS and a Starlink satellite, along with current solar flux:
```bash
oure fetch --sat-id 25544 --sat-id 43205
```

### 2. Analyze Conjunctions
Run the full prediction pipeline to assess risk over the next 72 hours:
```bash
oure analyze --primary 25544 --secondary 43205 --look-ahead 72 --mc-samples 1000 --output results.json
```

### 3. Generate Reports
Export the high-risk alerts to a PDF document:
```bash
oure report --results-file results.json --format pdf --output risk_report.pdf
```

### 4. Continuous Monitoring
Watch a specific catalog for upcoming threats, triggering alerts at defined $P_c$ thresholds:
```bash
oure monitor --primary 25544 --secondaries-file my_catalog.json --alert-threshold 1e-4 --interval 3600
```

## Architecture

OURE enforces a strict, decoupled 5-layer architecture:
1. **Core:** Immutable data models (`StateVector`, `CovarianceMatrix`) and physics constants.
2. **Data:** Caching and fetching interfaces (`SpaceTrackFetcher`, `NOAASolarFluxFetcher`).
3. **Physics:** The propagator decorator chain (`SGP4` -> `J2` -> `Drag`).
4. **Uncertainty:** STM generation and Vectorized Monte Carlo dispersion.
5. **Conjunction/Risk:** KD-Tree screening, TCA golden-section refinement, and B-Plane Foster integration.

## License

MIT License
