# OURE Testing Guide

This document outlines how to run the automated unit testing suite and performance benchmarks for the OURE (Orbital Uncertainty & Risk Engine) project.

## Prerequisites
Ensure your virtual environment is activated and dependencies are installed. You should be in the root `oure/` project directory.
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (including dev)
pip install -e '.[dev]'
```

## Running the Automated Test Suite
OURE uses `pytest` for unit testing across all decoupled layers.

### Run All Tests
To execute the entire test suite (Architecture, Core Models, Physics Propagators, Uncertainty propagation, and Conjunction Assessment):
```bash
# Ensure the our PYTHONPATH includes the local directory
export PYTHONPATH=$(pwd)
pytest tests/
```

### Run Specific Test Modules
If you are developing a specific component, you can target its test file:
```bash
# Test strictly decoupled architecture constraints
pytest tests/test_architecture.py

# Test core frozen dataclass models
pytest tests/test_models.py

# Test the Decorator Chain Physics Engine (SGP4, J2, Atmospheric Drag)
pytest tests/test_physics.py

# Test STM Calculations and Monte Carlo Uncertainty propagation
pytest tests/test_uncertainty.py

# Test KD-Tree spatial screening and Foster's Algorithm B-Plane Integration
pytest tests/test_conjunction.py
```

### Test Flags
- **Verbose output:** `pytest -v tests/`
- **Output Python Print statements:** `pytest -s tests/`
- **Stop on first failure:** `pytest -x tests/`

## Running Performance Benchmarks
A manual benchmarking script `example.py` is included to test O(N log N) scaling capabilities for KD-Tree screening against a mock catalog of 27,000 satellites.

To run the spatial indexing benchmark:
```bash
export PYTHONPATH=$(pwd)
python example.py
```

Expected output should show:
```
Generating mock catalog of 27,000 satellites...
...
Building KD-Tree and querying pairs within 5km radius...
Screening complete! Found [X] potential conjunction pairs.
Screening took: ~0.02 seconds.
Performance metric passed (O(N log N) scaling is fast).
```
