# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-03-14

### Added
- **Interactive Avoidance Wizard:** New `oure avoid` command featuring a step-by-step guide for maneuver optimization.
- **Enterprise-Grade Dashboard:** Multi-page Streamlit dashboard for visual fleet monitoring and task management.
- **NASA Standard Breakup Model:** New `oure shatter` command to simulate hypervelocity collisions and debris cloud dispersion.
- **Distributed Fleet Screening:** New `oure analyze-fleet` command using `ProcessPoolExecutor` for parallel 1-vs-N catalog screening.
- **EKF Sensor Tasking:** Simulation of covariance reduction via radar observations in `oure task-sensor`.
- **HPOP Propagator:** High Precision Orbit Propagator using RK45 numerical integration with J2 and atmospheric drag.
- **CDM Support:** Added a parser for CCSDS Conjunction Data Messages (JSON).
- **Unified UI System:** Standardized branding, themes, and "Pretty Error" handling across the entire CLI suite.
- **Shell Autocomplete:** Added `oure install-completion` for Zsh/Bash/Fish.

### Fixed
- **Foster Series Math:** Resolved critical eigenvalue ordering and normalization errors in the Foster $P_c$ algorithm.
- **Resource Management:** Fixed unclosed SQLite connections and properly managed temporary files in the API layer.
- **Numerical Stability:** Implemented the Joseph form for Kalman Filter updates to maintain covariance positive-definiteness.
- **Circular Dependencies:** Refactored CLI utility functions to resolve import loops.

### Security
- **Strict Ingestion Guard:** Added validation for all user-provided satellite IDs and CDM files.
- **Credential Protection:** Ensured API keys are never logged or stored in the local cache.

## [1.0.0] - 2026-03-11

### Added
- **Core Architecture:** Implemented a strict 5-layer decoupled architecture.
- **Physics Engine:** Added `SGP4Propagator`, `J2PerturbationCorrector`, and `AtmosphericDragCorrector`.
- **Vectorized Operations:** Native NumPy implementation for Kepler solvers and frame transformations.
- **Risk Calculation:** B-Plane projection and Foster's 1992 Algorithm.
- **CLI Interface:** Initial release with `fetch`, `analyze`, `monitor`, `cache`, and `report`.
