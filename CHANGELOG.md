# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-11

### Added
- **Core Architecture:** Implemented a strict 5-layer decoupled architecture (Core, Data, Physics, Uncertainty, Conjunction/Risk).
- **Physics Engine:** Added `SGP4Propagator`, `J2PerturbationCorrector`, and `AtmosphericDragCorrector` using a decorator pattern.
- **Vectorized Operations:** Replaced Python `for` loops with pure NumPy vectorized math for the Kepler solver, coordinate frame transformations, and state batch propagation.
- **Monte Carlo:** High-performance `MonteCarloUncertaintyPropagator` capable of processing 1000+ ghost trajectories in seconds.
- **Risk Calculation:** B-Plane projection and Probability of Collision ($P_c$) calculation using Foster's 1992 Algorithm (Numerical and Series implementations).
- **Spatial Indexing:** $O(N \log N)$ KD-Tree implementation for rapid coarse-filter conjunction screening.
- **CLI Interface:** A beautiful, responsive command-line interface using `Click` and `Rich` with commands: `fetch`, `analyze`, `monitor`, `cache`, and `report`.
- **PDF Reporting:** Automated PDF manifest generation for high-risk events via the `oure report` command.
- **Resilience:** SQLite-backed `CacheManager` and robust network retry logic using `tenacity`.
- **CI/CD:** Full GitHub Actions workflow, `Makefile`, and `pre-commit` hooks with `ruff` and `mypy`.
