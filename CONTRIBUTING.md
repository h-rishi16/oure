# Contributing to OURE

Thank you for your interest in contributing to the Orbital Uncertainty & Risk Engine (OURE). We welcome contributions from aerospace engineers, data scientists, and software developers to help improve orbital risk assessment.

## Development Environment Setup

OURE uses a robust toolchain to ensure code quality and mathematical correctness.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/h-rishi16/OURE.git
    cd OURE
    ```

2.  **Set up the environment:**
    We use `Makefile` targets to simplify environment setup. This will create a `.venv`, install all dependencies, and configure the pre-commit hooks.
    ```bash
    make dev
    ```

3.  **Activate the environment:**
    ```bash
    source .venv/bin/activate
    ```

## Development Workflow

We follow standard open-source development practices.

1.  **Create a branch:** Use the `feature/` or `fix/` prefix.
    ```bash
    git checkout -b feature/your-feature-name
    ```
2.  **Make your changes.**
3.  **Run the test suite:** OURE enforces a strict 88% minimum coverage requirement.
    ```bash
    make test-all
    ```
4.  **Run static analysis:** We use `ruff` for linting and `mypy` for strict type checking.
    ```bash
    make lint
    make type
    ```
5.  **Commit your changes:** The pre-commit hooks will run automatically.
6.  **Push and open a Pull Request.**

## Pull Request Checklist

Before opening a PR, ensure:
*   [ ] You have added tests for any new physics models or features.
*   [ ] `make test-all` passes with 100% success and >88% coverage.
*   [ ] `make lint` and `make type` report zero errors.
*   [ ] Architectural layer boundaries are respected (verified by `test_architecture.py`).

## Architectural Guidelines

OURE uses a strict 5-layer decoupled architecture. If you are adding new features, please respect these boundaries:
*   `core/`: Immutable data models. Cannot import from any other layer.
*   `data/`: Ingestion and caching.
*   `physics/`: Propagators and transformations.
*   `conjunction/`: Screening and TCA algorithms. (May import from `physics/`).
*   `risk/`: B-Plane projection and probability calculations. (May import from `physics/`).
*   `uncertainty/`: Covariance propagation and Monte Carlo. (May import from `physics/`).

Thank you for contributing to safer space operations!
